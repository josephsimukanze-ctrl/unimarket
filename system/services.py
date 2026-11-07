from django.core.cache import cache

from .models import SiteSetting


CACHE_KEY = "site_settings"
CACHE_TIMEOUT = 60


def get_settings() -> SiteSetting:
    """Return cached SiteSetting object."""
    settings = cache.get(CACHE_KEY)
    if settings is None:
        settings = SiteSetting.get()
        cache.set(CACHE_KEY, settings, CACHE_TIMEOUT)
    return settings


def invalidate_cache():
    cache.delete(CACHE_KEY)
