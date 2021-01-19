""" Paystack payment processor. """
from __future__ import absolute_import, unicode_literals

import logging

import waffle
from django.conf import settings

logger = logging.getLogger(__name__)


class Lumsxpay():
    """
    Just a bare structure of processor to register its name, no legacy methods added or will be used as LUMSX
    payment method is thirdparty and cannot be integerated
    """
    NAME = 'lumsxpay'

    def __init__(self, site):
        self.site = site

    @property
    def payment_processor(self):
        return Lumsxpay(self.request.site)

    @classmethod
    def is_enabled(cls):
        """
        Returns True if this payment processor is enabled, and False otherwise.
        """
        return waffle.switch_is_active(settings.PAYMENT_PROCESSOR_SWITCH_PREFIX + cls.NAME)
