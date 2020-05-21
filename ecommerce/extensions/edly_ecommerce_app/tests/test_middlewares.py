# -*- coding: utf-8 -*-
"""
Unit tests for middlewares.
"""
from testfixtures import LogCapture
from django.conf import settings
from django.urls import reverse

from ecommerce.core.models import SiteConfiguration
from ecommerce.extensions.edly_ecommerce_app.middleware import logger
from ecommerce.tests.factories import SiteConfigurationFactory
from ecommerce.tests.testcases import TestCase

class SettingsOverrideMiddlewareTests(TestCase):
    """
    Tests settings override middleware for sites.
    """
    def setUp(self):
        """
        Create environment for settings override middleware tests.
        """
        super(SettingsOverrideMiddlewareTests, self).setUp()
        self.dashboard_url = reverse('dashboard:index')
        self.user = self.create_user()
        self.client.login(username=self.user.username, password='test')
        self.default_settings = {
            key: getattr(settings, key, None) for key in [
                'ALLOWED_HOSTS',
                'CSRF_TRUSTED_ORIGINS',
                'EDLY_WORDPRESS_URL',
                'OSCAR_FROM_EMAIL',
                'PLATFORM_NAME',
            ]
        }

    def _assert_settings_values(self, expected_settings_values):
        """
        Checks if current settings values match expected settings values.
        """
        for config_key, expected_config_value in expected_settings_values.items():
            assert expected_config_value == getattr(settings, config_key, None)

    def test_settings_override_middleware_logs_warning_for_empty_override(self):
        """
        Tests "SettingsOverrideMiddleware" logs warning if site configuration has no django settings override values.
        """
        with LogCapture(logger.name) as logs:
            self.client.get(self.dashboard_url)
            logs.check(
                (
                    logger.name,
                    'WARNING',
                    'Site configuration for site ({site}) has no django settings overrides.'.format(site=self.request.site)
                )
            )
            self._assert_settings_values(self.default_settings)

    def test_settings_override_middleware_overrides_settings_correctly(self):
        """
        Tests "SettingsOverrideMiddleware" correctly overrides django settings.
        """
        django_override_settings = {
            'ALLOWED_HOSTS': [],
            'EDLY_WORDPRESS_URL': 'http://red.wordpress.edx.devstack.lms',
            'CSRF_TRUSTED_ORIGINS': [],
            'OSCAR_FROM_EMAIL': 'test@example.com',
            'PLATFORM_NAME': 'Test Platform',
        }
        SiteConfiguration.objects.all().delete()
        SiteConfigurationFactory(
            site=self.site,
            edly_client_theme_branding_settings={
                'DJANGO_SETTINGS_OVERRIDE': django_override_settings
            }
        )
        self._assert_settings_values(self.default_settings)
        self.client.get(self.dashboard_url)
        self._assert_settings_values(django_override_settings)
