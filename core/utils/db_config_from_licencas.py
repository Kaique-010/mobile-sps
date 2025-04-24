from django.db import connection
from decouple import config

def get_db_config_from_licencas(cnpj):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT lice_nome, lice_id
            FROM licencas
            WHERE lice_docu = %s AND lice_bloq = false
        """, [cnpj])
        row = cursor.fetchone()
        if row:
            lice_nome, lice_id = row
            db_name = f'saa_{lice_id}_{lice_nome}'.lower().replace(' ', '_')

            return {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': db_name,
                'USER': config('DB_USER'),
                'PASSWORD': config('DB_PASSWORD'),
                'HOST': config('DB_HOST'),
                'PORT': config('DB_PORT'),
            }
    return None
