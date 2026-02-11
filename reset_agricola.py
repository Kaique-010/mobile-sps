
import os
import sys
import django
from django.db import connections
from django.conf import settings

# Adicionar diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from Licencas.licencas_loader import carregar_licencas_dict

def reset_agricola_migrations():
    print("Iniciando reset das migrações do Agricola...")
    
    # Simular o comportamento do migrate_tenant_app para carregar as conexões
    # Mas carregar_licencas_dict já deve retornar o dicionário usado no settings
    # Porém, as conexões precisam ser configuradas no settings.DATABASES dinamicamente?
    # O settings.py normalmente já carrega isso.
    
    # Verificar se as conexões dos tenants estão disponíveis
    print(f"Conexões disponíveis: {list(connections)}")
    
    # Se só tiver 'default', precisamos carregar as outras manualmente ou confiar no settings
    # O settings.py do projeto parece usar o licencas_loader para popular DATABASES.
    
    for alias in connections:
        if alias == 'default': continue
        
        print(f"Processando {alias}...")
        try:
            with connections[alias].cursor() as cursor:
                # Verificar se a tabela de migrações existe
                cursor.execute("SELECT 1 FROM django_migrations LIMIT 1;")
                
                # Deletar migrações do Agricola
                print(f"  - Limpando django_migrations para Agricola em {alias}")
                cursor.execute("DELETE FROM django_migrations WHERE app = 'Agricola';")
                
                # Drop tables para garantir criação limpa (já que o usuário quer recriar)
                tabelas_agricola = [
                    'agricola_animais',
                    'agricola_eventos_animais',
                    'agricola_fazendas',
                    'agricola_talhoes',
                    'categorias_produtos_agricolas',
                    'agricola_produtos_agro',
                    'agricola_estoque_fazenda',
                    'agricola_movimentacao_estoque',
                    'agricola_historico_movimentacoes',
                    'agricola_aplicacao_insumos'
                ]
                
                for tabela in tabelas_agricola:
                     try:
                        cursor.execute(f"DROP TABLE IF EXISTS {tabela} CASCADE;")
                        print(f"    - Dropou {tabela}")
                     except Exception as e:
                        print(f"    - Falha ao dropar {tabela}: {e}")

            print(f"  - Sucesso em {alias}")
            
        except Exception as e:
            print(f"  - Erro em {alias}: {e}")

if __name__ == "__main__":
    reset_agricola_migrations()
