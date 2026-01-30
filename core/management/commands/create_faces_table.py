from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import OperationalError
from core.licencas_loader import carregar_licencas_dict

def create_table_entidades_faces(alias: str):
    with connections[alias].cursor() as cursor:
        # Criar tabela sem FK constraint rígida, pois 'entidades' pode não ter constraint UNIQUE/PK no banco legado
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entidades_faces (
                id SERIAL PRIMARY KEY,
                face_enti_id BIGINT NOT NULL,
                face_embe float8[],
                face_data TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        # Criar índice manualmente para performance (já que não temos a FK)
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_entidades_faces_face_enti_id 
            ON entidades_faces (face_enti_id);
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
    help = "Cria a tabela entidades_faces em todos os bancos de licenças"

    def handle(self, *args, **options):
        licencas = carregar_licencas_dict()

        if not licencas:
            raise CommandError("Nenhuma licença encontrada")

        self.stdout.write(f"Encontradas {len(licencas)} licenças. Iniciando criação da tabela entidades_faces...")

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
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro de conexão: {e}"))
                continue

            self.stdout.write(self.style.WARNING(f"[{alias}] Criando/Verificando tabela entidades_faces..."))

            try:
                create_table_entidades_faces(alias)
                self.stdout.write(self.style.SUCCESS(f"[{alias}] Tabela verificada com sucesso!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro ao criar tabela: {e}"))
