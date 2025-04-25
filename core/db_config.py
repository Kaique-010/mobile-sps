from decouple import config, UndefinedValueError
import logging

# Configuração de logging
logger = logging.getLogger(__name__)

def get_dynamic_db_config(docu: str) -> dict:
    """
    Retorna a configuração do banco com base no CNPJ (docu) recebido.
    Se não encontrar, retorna o banco padrão.
    """
    try:
        # Tenta buscar as configurações do banco do CNPJ (docu)
        db_config = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config(f'DB_DOCU_{docu}_NAME'),
            'USER': config(f'DB_DOCU_{docu}_USER'),
            'PASSWORD': config(f'DB_DOCU_{docu}_PASSWORD'),
            'HOST': config(f'DB_DOCU_{docu}_HOST'),
            'PORT': config(f'DB_DOCU_{docu}_PORT'),
        }

        # Loga as informações do banco de dados
        logger.info(f"Conectando ao banco de dados para o CNPJ: {docu}")
        logger.info(f"Usando banco de dados: {db_config['NAME']} no host {db_config['HOST']} na porta {db_config['PORT']}")
        
        return db_config
        
    except UndefinedValueError:
        # Caso não encontre, retorna a configuração do banco padrão
        logger.warning(f"Banco de dados para o CNPJ {docu} não encontrado. Usando banco padrão.")
        
        db_config = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DEFAULT_DB_NAME'),
            'USER': config('DEFAULT_DB_USER'),
            'PASSWORD': config('DEFAULT_DB_PASSWORD'),
            'HOST': config('DEFAULT_DB_HOST'),
            'PORT': config('DEFAULT_DB_PORT'),
        }

        # Loga a configuração do banco padrão
        logger.info(f"Usando banco padrão: {db_config['NAME']} no host {db_config['HOST']} na porta {db_config['PORT']}")
        
        return db_config
