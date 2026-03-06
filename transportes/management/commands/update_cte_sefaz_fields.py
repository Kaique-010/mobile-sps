from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import OperationalError
from core.licencas_loader import carregar_licencas_dict

def update_cte_columns(alias: str):
    with connections[alias].cursor() as cursor:
        sqls = [
            "ALTER TABLE cte ADD COLUMN IF NOT EXISTS cte_reci varchar(50);",
            "ALTER TABLE cte ADD COLUMN IF NOT EXISTS cte_doc_chav varchar(44);",
        ]
        for sql in sqls:
            cursor.execute(sql)

def montar_db_config(lic):
    config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": lic["db_name"],
        "USER": lic["db_user"],
        "PASSWORD": lic["db_password"],
        "HOST": lic["db_host"],
        "PORT": lic["db_port"],
        "CONN_MAX_AGE": 0,
        "OPTIONS": {
            "connect_timeout": 5,
            "options": "-c statement_timeout=10000" # 10 segundos timeout
        }
    }
    return config

class Command(BaseCommand):
    help = 'Adiciona colunas para controle SEFAZ na tabela Cte (legacy) em todos os tenants'

    def handle(self, *args, **options):
        licencas = carregar_licencas_dict()

        if not licencas:
            self.stdout.write(self.style.WARNING("Nenhuma licença encontrada. Verifique a tabela licencas_web."))
            # Tenta rodar no default como fallback se não houver licenças (útil para dev local sem multitenancy configurado)
            self.stdout.write(self.style.WARNING("Tentando rodar no banco 'default' como fallback..."))
            try:
                update_cte_columns('default')
                self.stdout.write(self.style.SUCCESS("Colunas atualizadas no banco 'default' com sucesso!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao atualizar 'default': {e}"))
            return
        
        # Ordenar para garantir consistência
        licencas.sort(key=lambda x: x['slug'])

        self.stdout.write(f"Encontradas {len(licencas)} licenças para processar.")

        for lic in licencas:
            alias = f"tenant_{lic['slug']}"
            
            # Pular se não tiver host
            if not lic.get('db_host'):
                self.stdout.write(self.style.ERROR(f"[{alias}] Sem host configurado. Pulando..."))
                continue

            connections.databases[alias] = montar_db_config(lic)

            self.stdout.write(f"[{alias}] Conectando a {lic['db_host']}...")

            # Testar conexão
            try:
                with connections[alias].cursor() as cursor:
                    cursor.execute("SELECT 1")
            except OperationalError as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro de conexão (OperationalError): {e}. Pulando..."))
                continue
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro genérico ao conectar: {e}. Pulando..."))
                continue

            self.stdout.write(self.style.WARNING(f"[{alias}] Atualizando colunas na tabela cte..."))

            try:
                update_cte_columns(alias)
                self.stdout.write(self.style.SUCCESS(f"[{alias}] Colunas atualizadas com sucesso!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro ao atualizar colunas: {e}"))
            finally:
                # Fechar conexão explicitamente
                try:
                    connections[alias].close()
                except:
                    pass
