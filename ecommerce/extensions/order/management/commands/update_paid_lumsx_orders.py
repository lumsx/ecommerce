from __future__ import unicode_literals

import logging

import requests
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from oscar.core.loading import get_class, get_model
from django.test.client import RequestFactory
from threadlocals.threadlocals import set_thread_variable

from ecommerce.extensions.partner.strategy import DefaultStrategy
from ecommerce.extensions.checkout.mixins import EdxOrderPlacementMixin

logger = logging.getLogger(__name__)
Order = get_model('order', 'Order')
Basket = get_model('basket', 'Basket')
BasketChallanVoucher = get_model('basket', 'BasketChallanVoucher')
Product = get_model('catalogue', 'Product')
StockRecord = get_model('partner', 'StockRecord')
Default = get_class('partner.strategy', 'Default')
Free = get_class('shipping.methods', 'Free')
OrderTotalCalculator = get_class('checkout.calculators', 'OrderTotalCalculator')
OrderNumberGenerator = get_class('order.utils', 'OrderNumberGenerator')
OrderCreator = get_class('order.utils', 'OrderCreator')
SiteConfiguration = get_model('core', 'SiteConfiguration')
NoShippingRequired = get_class('shipping.methods', 'NoShippingRequired')


class Command(BaseCommand):
    help = 'Update paid orders'
    VOUCHERS_PER_REQUEST = 99

    def add_arguments(self, parser):
        parser.add_argument('--site-id',
                            action='store',
                            dest='site_id',
                            type=int,
                            help='ID of the Site to update.')

    def equal_divided_chunks(self, lst, length):
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), length):
            yield lst[i:i + length]

    def handle(self, *args, **options):
        site_id = options.get('site_id')
        try:
            site = Site.objects.get(id=site_id)
        except Site.DoesNotExist:
            logger.exception('Site id %s does not exist', site_id)
            raise Exception

        try:
            site_configurations = SiteConfiguration.objects.get(site=site)
            configuration_helpers = site_configurations.edly_client_theme_branding_settings
            voucher_api_url = configuration_helpers.get('LUMSXPAY_VOUCHER_API_URL')
            if not voucher_api_url:
                logger.exception('Cron Job of Update Payment Statuses is canceled due to no '
                                 'LUMSXPAY_VOUCHER_API_URL in client theme branding')
                raise Exception
        except:
            logger.exception('Site Configurations with side id %s does not exist', site_id)
            raise Exception

        try:
            unpaid_challan_baskets = BasketChallanVoucher.objects.filter(
                is_paid=False)
        except:
            logger.exception('could not fetch the unpaid challan baskets from Database')
            raise Exception

        headers = {
            "Authorization": configuration_helpers.get('PAYMENT_AUTHORIZATION_KEY'),
            "Content-Type": "application/json"
        }

        paid_vouchers = []
        unpaid_vouchers = unpaid_challan_baskets.values_list('voucher_number', flat=True)
        if unpaid_challan_baskets:
            for unpaid_vouchers_lst in list(self.equal_divided_chunks(list(unpaid_vouchers), self.VOUCHERS_PER_REQUEST)):
                unpaid_vouchers_str = ','.join(unpaid_vouchers_lst)
                url = '{}/{}'.format(voucher_api_url, unpaid_vouchers_str)

                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    voucher_details = response.json()

                    voucher_data = voucher_details['data']
                    if not isinstance(voucher_details['data'], list):
                        voucher_data = [voucher_details['data']]

                    for voucher in voucher_data:
                        if voucher['paid_status'].lower() == 'paid':
                            paid_vouchers.append(voucher['voucher_id'])
                else:
                    logger.info('VOUCHER API doesnot return 200 OK')
                    return
        else:
            logger.info('No unpaid voucher found for update payment status')
            return

        if not paid_vouchers:
            logger.info('No voucher paid so exiting the job')
            return

        unpaid_basket_ids = unpaid_challan_baskets.filter(
            voucher_number__in=paid_vouchers
        ).values_list('basket_id', flat=True)

        paid_baskets = Basket.objects.filter(id__in=unpaid_basket_ids, status=Basket.OPEN)

        if not paid_baskets:
            logger.info('ERROR: Basket corresponding to voucher does not exist')
            raise Exception

        for basket in paid_baskets:
            shipping_method = NoShippingRequired()
            shipping_charge = shipping_method.calculate(basket)
            basket.strategy = DefaultStrategy()
            order_total = OrderTotalCalculator().calculate(basket, shipping_charge)
            user = basket.owner
            billing_address = None
            request = RequestFactory()
            request.site = site
            request.user = user
            request.site.siteconfiguration = site_configurations
            set_thread_variable('request', request)
            order = EdxOrderPlacementMixin().handle_order_placement(
                order_number=basket.order_number, user=user,
                basket=basket, shipping_address=None,
                shipping_method=shipping_method,
                shipping_charge=shipping_charge,
                billing_address=billing_address,
                order_total=order_total, request=request
            )

            EdxOrderPlacementMixin().handle_post_order(order)
            challan_voucher_basket = BasketChallanVoucher.objects.filter(basket_id=basket.id)

            if len(challan_voucher_basket) > 1:
                logger.info('more than one basket exist with same id in challan table.')
            elif challan_voucher_basket:
                challan_voucher_basket.update(is_paid=True)

        logger.info('Successfully finished the cron job for updating the order payment')
        return
