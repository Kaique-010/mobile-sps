import json
import time
import threading
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from django.conf import settings
from django.core.cache import cache

_local_cache = {}

def _cache_get(key):
    val = cache.get(key)
    if val is not None:
        return val
    item = _local_cache.get(key)
    if not item:
        return None
    expires, data = item
    if expires and expires < time.time():
        _local_cache.pop(key, None)
        return None
    return data

def _cache_set(key, data, ttl=3600):
    try:
        cache.set(key, data, ttl)
    except Exception:
        _local_cache[key] = (time.time() + ttl, data)

def suggest_tax(cfop_code, state, entity_type):
    base_url = getattr(settings, 'CFOP_SUGGESTION_API_URL', None)
    key = f"cfop_suggest:{cfop_code}:{state}:{entity_type}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    if not base_url:
        data = {
            'icms_cst': '00',
            'ipi_cst': '50',
            'pis_cst': '01',
            'cofins_cst': '01',
            'aliquotas': {'icms': 18.0, 'ipi': 0.0, 'pis': 1.65, 'cofins': 7.6},
        }
        _cache_set(key, data, 3600)
        return data
    try:
        url = f"{base_url.rstrip('/')}/sugestoes?cfop={cfop_code}&uf={state}&tipo={entity_type}"
        req = Request(url, headers={'Accept': 'application/json'})
        with urlopen(req, timeout=8) as resp:
            body = resp.read().decode('utf-8')
            data = json.loads(body)
            _cache_set(key, data, 3600)
            return data
    except (URLError, HTTPError, json.JSONDecodeError):
        data = {
            'icms_cst': '00',
            'ipi_cst': '50',
            'pis_cst': '01',
            'cofins_cst': '01',
            'aliquotas': {'icms': 18.0, 'ipi': 0.0, 'pis': 1.65, 'cofins': 7.6},
        }
        _cache_set(key, data, 600)
        return data

def refresh_all_periodic():
    # Evitar criar threads zumbis que impedem o shutdown
    # Se for necessário lógica periódica, use Celery ou cron.
    pass