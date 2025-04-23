import json
from django.db import connections
from django.conf import settings

DB_CONFIG_PATH = 'db_configs.json'

def get_db_config(cod):
    with open(DB_CONFIG_PATH) as f:
        configs = json.load(f)
    return configs[cod]

def connect_and_test(cod):
    config = get_db_config(cod)

    alias = f"db_{cod}"

    # Definir as configurações do banco de dados
    settings.DATABASES[alias] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config["NAME"],
        'USER': config["USER"],
        'PASSWORD': config["PASSWORD"],
        'HOST': config["HOST"],
        'PORT': config["PORT"],
        'CONN_MAX_AGE': 0,  # Não deixa a conexão vazar
        'OPTIONS': {},      # Pode deixar vazio
        'ATOMIC_REQUESTS': False,  # Se for True, lida com transações automaticamente
        'AUTOCOMMIT': True,        # Deixa o autocommit funcionando
        'TEST': {
            'NAME': None,
            'CHARSET': None,
            'COLLATION': None,
            'MIRROR': None,
        },
        'DISABLE_SERVER_SIDE_CURSORS': False,  # Default para não desabilitar
        'CONN_HEALTH_CHECKS': False,  # Evita erro, desativa a verificação de saúde da conexão
    }

    # Adicionando o comando SQL para garantir que o fuso horário seja UTC
    with connections[alias].cursor() as cursor:
        cursor.execute("SET TIMEZONE TO 'UTC';")
        cursor.execute("SELECT NOW();")
        result = cursor.fetchone()
        print("Conectado!", result)
