# core/licenca_context.py

import threading
_thread_locals = threading.local()

def set_current_request(request):
    _thread_locals.request = request

def get_current_request():
    return getattr(_thread_locals, 'request', None)

import json
from pathlib import Path

# Carrega apenas os dados. Nada de settings, nada de imports cruzados.
json_path = Path(__file__).resolve().parent / 'licencas.json'
LICENCAS_MAP = json.load(open(json_path))