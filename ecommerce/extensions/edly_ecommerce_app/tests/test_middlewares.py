"""
Test edly settings middleware.
"""
from django.conf import settings
from django.contrib.sites.models import Site
from django.test import TestCase
from django.test.client import Client
from django.urls import reverse

from ecommerce.extensions.edly_ecommerce_app.middleware import DJANGO_SETTINGS_OVERRIDE_CONFIG_KEY
from ecommerce.tests.factories import SiteFactory, SiteConfigurationFactory


class SiteConfigurationSettingsOverrideTests(TestCase):
    """
    Tests settings override middleware for sites.
    """

    def setUp(self):
        """
        Create environment for settings override middleware tests.
        """
        Site.objects.all().delete()
        self.site = SiteFactory.create(
            id=1,
            domain='testserver.fake',
            name='testserver.fake'
        )
        self.client = Client(SERVER_NAME=self.site.domain)
        self.health_page_url = reverse('health')

    def _assert_response_settings_values(self, response, expected_site_configuration_values):
        """
        Validate configuration settings in HTTP response.
        """
        for config_key, expected_config_value in expected_site_configuration_values.items():
            assert expected_config_value == getattr(response.context['settings'], config_key)

    def test_site_configuration_override(self):
        """
        Verify that the django settings are overridden based on the site configuration.
        """
        expected_site_configuration_values = {
            'LOGIN_REDIRECT_URL': 'https://edly.ecommerce.com/',
            'SOCIAL_AUTH_EDX_OIDC_URL_ROOT': 'http://edly.lms.com/oauth2',
            'SOCIAL_AUTH_EDX_OIDC_ISSUER': 'http://edly.lms.com/oauth2',
            'SOCIAL_AUTH_EDX_OIDC_KEY': 'dummy-key',
            'SOCIAL_AUTH_EDX_OIDC_SECRET': 'dummy-secret',
            'SOCIAL_AUTH_EDX_OIDC_ID_TOKEN_DECRYPTION_KEY': 'dummy-secret',
            'SOCIAL_AUTH_EDX_OIDC_LOGOUT_URL': 'http://edly.lms.com/logout',
        }
        edly_client_theme_branding_settings = {
            DJANGO_SETTINGS_OVERRIDE_CONFIG_KEY: expected_site_configuration_values
        }

        # Create related site configuration with the desired values
        site_configuration = SiteConfigurationFactory.create(
            site=self.site,
            edly_client_theme_branding_settings=edly_client_theme_branding_settings,
        )

        # Now verify that the django conf settings are actually changed in the user response
        response = self.client.get(self.health_page_url)
        assert self.site == response.context['site']
        assert site_configuration == response.context['site'].configuration
        self._assert_response_settings_values(response, expected_site_configuration_values)

    def test_disabled_site_configuration_override(self):
        """
        Verify that django settings are not overridden if no override settings provided.
        """
        expected_site_configuration_values = {
        }

        edly_client_theme_branding_settings = {
            DJANGO_SETTINGS_OVERRIDE_CONFIG_KEY: expected_site_configuration_values
        }

        # Create related site configuration with the desired values
        site_configuration = SiteConfigurationFactory.create(
            site=self.site,
            edly_client_theme_branding_settings=edly_client_theme_branding_settings,
        )
        response = self.client.get(self.health_page_url)
        assert self.site == response.context['site']
        assert site_configuration == response.context['site'].configuration
        expected_login_redirect_url = settings.LOGIN_REDIRECT_URL
        assert expected_login_redirect_url == getattr(response.context['settings'], 'LOGIN_REDIRECT_URL')
