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
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception as e:
        logger.error(f"[LICENCAS_CONTEXT] Erro fatal ao ler JSON de fallback: {e}")
        return []

def get_licencas_login_clientes():
    """
    Retorna lista de licenças filtrada para login de clientes.
    Usa lista manual de slugs ou db_names permitidos.
    """
    # Lista de slugs ou nomes de banco permitidos
    # 'eletro' corresponde ao banco savexml144
    PERMITIDOS = ['eletro', 'savexml144', 'savexml839']
    
    todas = get_licencas_map()
    
    # Filtra verificando se o slug OU o db_name está na lista de permitidos
    filtradas = [
        l for l in todas 
        if l.get('slug') in PERMITIDOS or l.get('db_name') in PERMITIDOS
    ]
    
    if not filtradas:
        logger.warning(f"[LOGIN] Nenhum alvo permitido {PERMITIDOS} foi encontrado nas licenças carregadas.")
        return []
        
    return filtradas

LICENCAS_MAP = []
