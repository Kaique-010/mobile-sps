import json
from logging import config
from django.conf import settings


DB_CONFIG_PATH = 'db_configs.json'

def get_db_config(cod):
    try:
        with open(DB_CONFIG_PATH) as f:
            configs = json.load(f)

        if cod not in configs:
            raise ValueError(f"[ERRO] CNPJ {cod} não está configurado em {DB_CONFIG_PATH}")

        return configs[cod]

    except FileNotFoundError:
        raise ValueError(f"[ERRO] Arquivo {DB_CONFIG_PATH} não encontrado.")
    except json.JSONDecodeError:
        raise ValueError("[ERRO] Erro ao ler o arquivo JSON de configuração do banco.")
    except Exception as e:
        raise ValueError(f"[ERRO] Falha ao acessar configurações de banco: {e}")