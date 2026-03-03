
import os
import sys
import django
from django.conf import settings

# Configuração do ambiente Django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from OrdemdeServico.Views.ordem_viewset import OrdemViewSet
from django.test import RequestFactory
from rest_framework.request import Request
from core.utils import get_db_from_slug
from django.db import connections
from OrdemdeServico.models import Ordemservico

def debug_sql():
    # Registra o banco 'eletro'
    try:
        get_db_from_slug('eletro')
    except Exception as e:
        print(f"Erro ao registrar banco: {e}")
        return

    print("\n=== PROCURANDO ORDENS CORROMPIDAS NO VIEWSET ===")
    try:
        from django.db import connections
        with connections['eletro'].cursor() as cursor:
            # Query replica os filtros do OrdemViewSet
            cursor.execute("""
                SELECT orde_nume, orde_seto, orde_stat_orde,
                       orde_data_aber::text, orde_data_fech::text,
                       orde_ulti_alte::text
                FROM ordemservico 
                WHERE (
                       (EXTRACT(YEAR FROM orde_data_aber) < 1900 OR EXTRACT(YEAR FROM orde_data_aber) > 2100)
                    OR (orde_data_fech IS NOT NULL AND (EXTRACT(YEAR FROM orde_data_fech) < 1900 OR EXTRACT(YEAR FROM orde_data_fech) > 2100))
                    OR (orde_ulti_alte IS NOT NULL AND (EXTRACT(YEAR FROM orde_ulti_alte) < 1900 OR EXTRACT(YEAR FROM orde_ulti_alte) > 2100))
                  )
                LIMIT 10
            """)
            rows = cursor.fetchall()
            if rows:
                print(f"Encontradas {len(rows)} ordens com datas principais corrompidas (sem filtros de viewset):")
                for row in rows:
                    print(f"Ordem: {row[0]}, Setor: {row[1]}, Status: {row[2]}")
                    print(f"  DataAber: {row[3]}")
                    print(f"  DataFech: {row[4]}")
                    print(f"  UltiAlte: {row[5]}")
                    print("-" * 30)
            else:
                print("Nenhuma ordem com datas principais corrompidas encontrada no banco todo.")
    except Exception as e:
        print(f"Erro ao buscar ordens corrompidas: {e}")

if __name__ == "__main__":
    debug_sql()
