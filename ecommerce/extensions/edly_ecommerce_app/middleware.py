from logging import getLogger
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site

from ecommerce.core.models import SiteConfiguration

logger = getLogger(__name__)


class SettingsOverrideMiddleware(object):
    """
    Django middleware to override django settings from site configuration.
    """

    def process_request(self, request):
        """
        Override django settings from django site configuration.
        """
        current_site = get_current_site(request)
        try:
            current_site_configuration = current_site.siteconfiguration
        except SiteConfiguration.DoesNotExist:
            logger.warning('Site (%s) has no related site configuration.', current_site)
            return None

        if current_site_configuration:
            django_settings_override_values = current_site_configuration.get_edly_configuration_value('DJANGO_SETTINGS_OVERRIDE', None)
            if django_settings_override_values:
                for config_key, config_value in django_settings_override_values.items():
                    setattr(settings, config_key, config_value)
            else:
                logger.warning('Site configuration for site (%s) has no django settings overrides.', current_site)
