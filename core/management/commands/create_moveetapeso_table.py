from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import OperationalError
from core.licencas_loader import carregar_licencas_dict


def montar_db_config(lic):
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": lic["db_name"],
        "USER": lic["db_user"],
        "PASSWORD": lic["db_password"],
        "HOST": lic["db_host"],
        "PORT": lic["db_port"],
        "CONN_MAX_AGE": 0,
        "OPTIONS": {
            "connect_timeout": 5,
            "options": "-c statement_timeout=10000",
        },
    }


def create_table_moveetapeso(alias: str):
    with connections[alias].cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS moveetapeso (
                id SERIAL PRIMARY KEY,
                moet_peso_codi numeric(15,4),
                moet_peso_moet numeric(15,4),
                moet_peso_prod integer,
                moet_peso_oppr integer,
                moet_peso_sald numeric(15,4)
            );
            CREATE INDEX IF NOT EXISTS idx_moveetapeso_oppr ON moveetapeso (moet_peso_oppr);
            """
        )


class Command(BaseCommand):
    help = "Cria a tabela moveetapeso em todos os bancos das licenças (slugs)"

    def handle(self, *args, **options):
        licencas = carregar_licencas_dict()
        if not licencas:
            raise CommandError("Nenhuma licença encontrada")

        licencas.sort(key=lambda x: x["slug"])

        for lic in licencas:
            alias = f"tenant_{lic['slug']}"
            if not lic.get("db_host"):
                self.stdout.write(self.style.ERROR(f"[{alias}] Sem host configurado. Pulando..."))
                continue

            connections.databases[alias] = montar_db_config(lic)

            try:
                with connections[alias].cursor() as cursor:
                    cursor.execute("SELECT 1")
            except OperationalError as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro de conexão: {e}. Pulando..."))
                continue
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro genérico ao conectar: {e}. Pulando..."))
                continue

            self.stdout.write(self.style.WARNING(f"[{alias}] Criando tabela moveetapeso (se não existir)..."))
            try:
                create_table_moveetapeso(alias)
                self.stdout.write(self.style.SUCCESS(f"[{alias}] OK"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro ao criar tabela: {e}"))
            finally:
                try:
                    connections[alias].close()
                except:
                    pass
