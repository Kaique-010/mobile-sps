from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import OperationalError
from core.licencas_loader import carregar_licencas_dict
import socket

def update_entidades_columns(alias: str):
    with connections[alias].cursor() as cursor:
        cursor.execute(
            """
            ALTER TABLE entidades
            ADD COLUMN IF NOT EXISTS enti_mobi_usua varchar(100),
            ADD COLUMN IF NOT EXISTS enti_mobi_senh varchar(100),
            ADD COLUMN IF NOT EXISTS enti_mobi_prec boolean DEFAULT true,
            ADD COLUMN IF NOT EXISTS enti_mobi_foto boolean DEFAULT true,
            ADD COLUMN IF NOT EXISTS enti_usua_mobi varchar(100),
            ADD COLUMN IF NOT EXISTS enti_senh_mobi varchar(100),
            ADD COLUMN IF NOT EXISTS enti_usua_prec boolean DEFAULT true,
            ADD COLUMN IF NOT EXISTS enti_usua_foto boolean DEFAULT true;
            """
        )


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
    help = "Adiciona colunas de login mobile na tabela entidades em todos os bancos de licenças"

    def handle(self, *args, **options):
        licencas = carregar_licencas_dict()

        if not licencas:
            raise CommandError("Nenhuma licença encontrada")
        
        # Ordenar para garantir consistência
        licencas.sort(key=lambda x: x['slug'])

        for lic in licencas:
            alias = f"tenant_{lic['slug']}"
            
            # Pular se não tiver host
            if not lic.get('db_host'):
                self.stdout.write(self.style.ERROR(f"[{alias}] Sem host configurado. Pulando..."))
                continue

            connections.databases[alias] = montar_db_config(lic)

            self.stdout.write(f"[{alias}] Conectando a {lic['db_host']}...")

            # Testar conexão antes de prosseguir com timeout explícito
            try:
                with connections[alias].cursor() as cursor:
                    cursor.execute("SELECT 1")
            except OperationalError as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro de conexão (OperationalError): {e}. Pulando..."))
                continue
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro genérico ao conectar: {e}. Pulando..."))
                continue

            self.stdout.write(self.style.WARNING(f"[{alias}] Atualizando colunas na tabela entidades..."))

            try:
                update_entidades_columns(alias)
                self.stdout.write(self.style.SUCCESS(f"[{alias}] Colunas atualizadas com sucesso!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro ao atualizar colunas (possível timeout ou lock): {e}"))
            finally:
                # Fechar conexão explicitamente para liberar recursos
                try:
                    connections[alias].close()
                except:
                    pass
