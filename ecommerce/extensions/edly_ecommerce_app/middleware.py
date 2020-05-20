"""
Edly settings middleware.
"""
from logging import getLogger

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site

from ecommerce.core.models import SiteConfiguration

logger = getLogger(__name__)  # pylint: disable=invalid-name
DJANGO_SETTINGS_OVERRIDE_CONFIG_KEY = 'DJANGO_SETTINGS_OVERRIDE'


class SettingsOverrideMiddleware(object):
    """
    Django middleware hook for django settings override based on request.
    """

    def process_request(self, request):
        """
        Override django settings based on request.
        """
        current_site = get_current_site(request)

        try:
            current_site_configuration = current_site.configuration
        except SiteConfiguration.DoesNotExist:
            logger.warning('Site (%s) has no related site configuration.', current_site)

        if current_site_configuration:
            django_settings_override = current_site_configuration.get_edly_configuration_value(
                DJANGO_SETTINGS_OVERRIDE_CONFIG_KEY
            )
            if django_settings_override:
                for config_key, config_value in django_settings_override.items():
                    setattr(settings, config_key, config_value)
            else:
                logger.info('Site (%s) has no django settings override.', current_site)
