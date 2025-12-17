from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connections
from django.db.utils import ProgrammingError, OperationalError
from core.licencas_loader import carregar_licencas_dict


DEPENDENCY_APPS = [
    "contenttypes",
  
]

def criar_usuarios_if_not_exists(alias: str):
    with connections[alias].cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                usua_nome VARCHAR(100),
                usua_codi INTEGER PRIMARY KEY,
                usua_senh_mobi VARCHAR(128),
                usua_seto INTEGER NULL
            );
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

def get_ssl_options(host: str):
    if host in ("localhost", "127.0.0.1"):
        return {}
    return {"sslmode": "require"}

class Command(BaseCommand):
    help = "Roda migrate de um app específico em todos os bancos de licenças"

    def add_arguments(self, parser):
        parser.add_argument("app_label", type=str)

    def handle(self, *args, **options):
        app_label = options["app_label"]
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

            self.stdout.write(self.style.WARNING(f"[{alias}] preparando banco"))

            # 1️⃣ Ajuste defensivo para bancos antigos
            try:
                with connections[alias].cursor() as cursor:
                    # Verifica se a coluna 'name' existe antes de tentar alterar
                    cursor.execute(
                        """
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'django_content_type'
                        AND column_name = 'name';
                        """
                    )
                    if cursor.fetchone():
                        cursor.execute(
                            """
                            ALTER TABLE django_content_type
                            ALTER COLUMN name DROP NOT NULL;
                            """
                        )
            except ProgrammingError:
                pass

            # 1.5 Criar tabela usuarios se não existir (para evitar erro no perfilweb)
            try:
                criar_usuarios_if_not_exists(alias)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro ao criar usuarios: {e}"))

            # 2️⃣ Dependências primeiro
            for dep in DEPENDENCY_APPS:
                self.stdout.write(f"[{alias}] migrate {dep}")
                try:
                    call_command(
                        "migrate",
                        dep,
                        database=alias,
                        interactive=False,
                        verbosity=0,
                        fake_initial=True,
                    )
                except Exception as e:
                    if "column \"name\" of relation \"django_content_type\" does not exist" in str(e):
                        self.stdout.write(self.style.WARNING(f"[{alias}] Ignorando erro de coluna name em contenttypes: {e}"))
                    else:
                        raise e

            # 3️⃣ App alvo
            self.stdout.write(self.style.SUCCESS(f"[{alias}] migrate {app_label}"))
            try:
                call_command(
                    "migrate",
                    app_label,
                    database=alias,
                    interactive=False,  
                    verbosity=1,
                    fake_initial=True,
                )
            except Exception as e:
                if "column \"name\" of relation \"django_content_type\" does not exist" in str(e):
                     self.stdout.write(self.style.WARNING(f"[{alias}] Ignorando erro de coluna name ao migrar {app_label}: {e}"))
                else:
                    raise e
