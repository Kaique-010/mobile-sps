from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import OperationalError
from core.licencas_loader import carregar_licencas_dict

def campoIntervaloHoras(alias: str):
    with connections[alias].cursor() as cursor:
        cursor.execute(
            """
        alter table pedidosvenda
        add column if not exists pedi_stat VARCHAR(10) NOT NULL DEFAULT 'A';
 
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
        "CONN_MAX_AGE": 60,
    }
    return config

class Command(BaseCommand):
    help = "Atualiza apenas o campo pedi_stat em todos os bancos de licenças"

    def handle(self, *args, **options):
        licencas = carregar_licencas_dict()

        if not licencas:
            raise CommandError("Nenhuma licença encontrada")

        for lic in licencas:
            alias = f"tenant_{lic['slug']}"
            connections.databases[alias] = montar_db_config(lic)

            # Testar conexão antes de prosseguir
            try:
                with connections[alias].cursor() as cursor:
                    cursor.execute("SELECT 1")
            except OperationalError:
                self.stdout.write(self.style.ERROR(f"[{alias}] Banco de dados não encontrado ou inacessível. Pulando..."))
                continue

            self.stdout.write(self.style.WARNING(f"[{alias}] Atualizando campo pedi_stat..."))

            try:
                campoIntervaloHoras(alias)
                self.stdout.write(self.style.SUCCESS(f"[{alias}] Campo atualizado com sucesso!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro ao atualizar campo: {e}"))
