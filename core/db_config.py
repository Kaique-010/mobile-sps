import json
from logging import config
from django.conf import settings


DB_CONFIG_PATH = 'db_configs.json'

def get_db_config(cod):
    with open(DB_CONFIG_PATH) as f:
        configs = json.load(f)

    if cod not in configs:
        raise ValueError(f"[ERRO] CNPJ {cod} não está configurado em {DB_CONFIG_PATH}")

    return configs[cod]