""" View for interacting with the LumsxPay payment processor. """

from __future__ import unicode_literals

import json
import logging
import requests
import datetime

from django.contrib.auth.views import redirect_to_login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponseNotFound
from django.shortcuts import render_to_response
from django.utils.decorators import method_decorator
from django.views.generic import View
from oscar.core.loading import get_class, get_model

from ecommerce.extensions.checkout.mixins import EdxOrderPlacementMixin
from ecommerce.extensions.payment.processors.lumsxpay import Lumsxpay
from ecommerce.extensions.basket.models import BasketChallanVoucher
from ecommerce.core.url_utils import get_lms_dashboard_url

logger = logging.getLogger(__name__)

Basket = get_model('basket', 'Basket')
Product = get_model('catalogue', 'Product')


class LumsxpayExecutionView(LoginRequiredMixin, EdxOrderPlacementMixin, View):
    @property
    def payment_processor(self):
        return Lumsxpay(self.request.site)

    @method_decorator(transaction.non_atomic_requests)
    def dispatch(self, request, *args, **kwargs):
        return super(LumsxpayExecutionView, self).dispatch(request, *args, **kwargs)

    def extract_items_from_basket(self, basket):
        return [
            {
                "title": l.product.title,
                "amount": str(l.line_price_incl_tax),
                "id": l.product.course_id}
            for l in basket.all_lines()
        ]

    def get_existing_basket_challan(self, request):
        basket = request.basket
        product = basket.lines.first().product

        return BasketChallanVoucher.objects.filter(basket=basket, product=product)

    def get_due_date(self, configuration_helpers):
        due_date_span_in_weeks = configuration_helpers.get('PAYMENT_DUE_DATE_SPAN', 52)
        due_date = datetime.datetime.now() + datetime.timedelta(weeks=due_date_span_in_weeks)
        return due_date.strftime("%Y-%m-%d %H:%M:%S%z")

    def fetch_context(self, request, response, configuration_helpers):
        voucher_details = response.json()
        voucher_data = voucher_details.get('data', {})
        url_for_online_payment = voucher_data.get("url_for_online_payment")
        url_for_download_voucher = voucher_data.get("url_for_download_voucher")
        return {
            'configuration_helpers': configuration_helpers,
            'url_for_online_payment': url_for_online_payment,
            'url_for_download_voucher': url_for_download_voucher,
            'items_list': voucher_data.get('items'),
            "name": request.user.username,
            "email": request.user.email,
            "order_id": request.basket.order_number,
            "user": request.user,
            "lms_dashboard_url": get_lms_dashboard_url,
            "is_paid": False,
            "support_email": request.site.siteconfiguration.payment_support_email,
        }

    def request_existing_challan_context(self, request, basket_challan):
        configuration_helpers = request.site.siteconfiguration.edly_client_theme_branding_settings
        url = '{}/{}'.format(configuration_helpers.get('LUMSXPAY_VOUCHER_API_URL'), basket_challan.voucher_number)
        headers = {
            "Authorization": configuration_helpers.get('PAYMENT_AUTHORIZATION_KEY'),
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return self.fetch_context(request, response, configuration_helpers)

        return {}

    def get(self, request):
        basket = request.basket
        configuration_helpers = request.site.siteconfiguration.edly_client_theme_branding_settings
        url = configuration_helpers.get('LUMSXPAY_VOUCHER_API_URL')

        if not url:
            msg = 'LUMSXPAY_VOUCHER_API_URL is not defined in site configurations'
            logger.info(msg)

        existing_basket_challan = self.get_existing_basket_challan(request)
        if existing_basket_challan.exists():
            context = self.request_existing_challan_context(request, existing_basket_challan.first())
            if not context:
                logger.exception('challan status API not working, no context found')
                return HttpResponseNotFound()

            return render_to_response('payment/lumsxpay.html', context)

        items = self.extract_items_from_basket(basket)
        payload = {
            "name": request.user.username,
            "email": request.user.email,
            "order_id": basket.order_number,
            "items": items,
            "due_date": self.get_due_date(configuration_helpers)
        }

        headers = {
            "Authorization": configuration_helpers.get('PAYMENT_AUTHORIZATION_KEY'),
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers)
        except:
            logger.exception('Challan generation API not working and cannot be reached.')
            return HttpResponseNotFound()

        if response.status_code == 200:
            voucher_details = response.json()
            context = self.fetch_context(request, response, configuration_helpers)

            voucher_number = voucher_details['data']['voucher_id']
            due_date = voucher_details['data']['due_date']

            _, created = BasketChallanVoucher.objects.get_or_create(
                basket=basket,
                voucher_number=voucher_number,
                due_date=due_date,
                is_paid=False,
                product=basket.lines.first().product
            )

            if created:
                logger.info('challan-basket created with voucher number %s and due date %s', voucher_number, due_date)
            else:
                logger.exception('could not create the challan voucher entry in DB')
                return HttpResponseNotFound()

            return render_to_response('payment/lumsxpay.html', context)

        logger.exception(
            'Challan creation API status return %s status code and challan creation failed with response %s',
            response.status_code, response.json()
        )

        return HttpResponseNotFound()
