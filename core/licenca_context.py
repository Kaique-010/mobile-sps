# core/licenca_context.py

import threading
_thread_locals = threading.local()

def set_current_request(request):
    _thread_locals.request = request

def get_current_request():
    return getattr(_thread_locals, 'request', None)

import json
import logging
from pathlib import Path

json_path = Path(__file__).resolve().parent / 'licencas.json'
logger = logging.getLogger(__name__)

def get_licencas_map():
    try:
        from core.licencas_loader import carregar_licencas_dict
        data = carregar_licencas_dict()
        if data:
            
            return data
    except Exception:
        logger.warning("[LICENCAS_CONTEXT] erro ao carregar da tabela, usando fallback JSON")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
        return data

LICENCAS_MAP = []
