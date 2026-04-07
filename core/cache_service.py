import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

DEFAULT_NAMESPACE = "mobile_sps"
_CACHE_MISS = object()


def build_cache_key(module, *parts):
    normalized = [str(part).strip().replace(" ", "_") for part in parts if part is not None and str(part).strip() != ""]
    return ":".join([DEFAULT_NAMESPACE, str(module)] + normalized)


def cache_get_or_set(key, timeout, factory, logger_instance=None, lock_timeout=30, use_lock=False):
    logger_ref = logger_instance or logger
    data = cache.get(key, _CACHE_MISS)
    hit = data is not _CACHE_MISS
    logger_ref.info("CACHE %s chave=%s", "HIT" if hit else "MISS", key)
    if hit:
        return data, True

    if use_lock:
        lock_key = f"lock:{key}"
        lock_acquired = cache.add(lock_key, "1", lock_timeout)
        if lock_acquired:
            try:
                data = factory()
                cache.set(key, data, timeout)
                return data, False
            finally:
                cache.delete(lock_key)

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
