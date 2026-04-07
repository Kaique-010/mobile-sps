import logging
import time

from django.core.cache import cache

logger = logging.getLogger(__name__)

DEFAULT_NAMESPACE = "mobile_sps"


def build_cache_key(module, *parts):
    normalized = [str(part).strip().replace(" ", "_") for part in parts if part is not None and str(part).strip() != ""]
    return ":".join([DEFAULT_NAMESPACE, str(module)] + normalized)


def cache_get_or_set(key, timeout, factory, logger_instance=None, lock_timeout=30):
    logger_ref = logger_instance or logger
    data = cache.get(key)
    hit = data is not None
    logger_ref.info("CACHE %s chave=%s", "HIT" if hit else "MISS", key)
    if hit:
        return data, True

    lock_key = f"lock:{key}"
    lock_acquired = cache.add(lock_key, "1", lock_timeout)
    if lock_acquired:
        try:
            data = factory()
            cache.set(key, data, timeout)
            return data, False
        finally:
            cache.delete(lock_key)

    for _ in range(10):
        time.sleep(0.1)
        data = cache.get(key)
        if data is not None:
            logger_ref.info("CACHE HIT chave=%s (aguardou lock)", key)
            return data, True

    data = factory()
    cache.set(key, data, timeout)
    return data, False


def safe_delete_pattern(pattern, logger_instance=None):
    logger_ref = logger_instance or logger
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern(pattern)
        logger_ref.info("CACHE INVALIDATE pattern=%s", pattern)
        return
    logger_ref.warning("CACHE INVALIDATE ignorado (backend sem delete_pattern) pattern=%s", pattern)
