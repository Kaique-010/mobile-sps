from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connections
from django.db.utils import ProgrammingError, OperationalError
from core.licencas_loader import carregar_licencas_dict
import sys
import os

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
        parser.add_argument("--license", type=str, required=False, help="Slug da licença específica para rodar o migrate")

    def handle(self, *args, **options):
        # Desconecta signals de post_migrate que causam problemas em bancos legados
        # O problema ocorre porque 'django.contrib.auth' tenta criar permissões e acessa 'django_content_type.name'
        # que foi removido no Django mais novo, mas pode existir ou estar corrompido em bancos legados.
        from django.db.models.signals import post_migrate
        from django.contrib.auth.management import create_permissions
        from django.contrib.contenttypes.management import create_contenttypes
        
        # Tenta desconectar handlers padrão conhecidos por causar erro
        try:
            post_migrate.disconnect(create_permissions, dispatch_uid="django.contrib.auth.management.create_permissions")
        except:
            pass
            
        try:
            # Em versões antigas o dispatch_uid pode não ser usado, tenta desconectar pela função direta
            post_migrate.disconnect(create_permissions, sender=None)
        except:
            pass

        try:
            post_migrate.disconnect(create_contenttypes, dispatch_uid="django.contrib.contenttypes.management.create_contenttypes")
        except:
            pass

        try:
            post_migrate.disconnect(create_contenttypes, sender=None)
        except:
            pass

        app_label = options["app_label"]
        target_license = options.get("license")
        licencas = carregar_licencas_dict()

        if target_license:
            licencas = [l for l in licencas if l["slug"] == target_license]
            if not licencas:
                raise CommandError(f"Licença '{target_license}' não encontrada.")

        if not licencas:
            raise CommandError("Nenhuma licença encontrada")

        self.stdout.write(f"Encontradas {len(licencas)} licenças. Iniciando migração de '{app_label}'...")

        try:
            for i, lic in enumerate(licencas, 1):
                alias = lic["slug"]
                self.stdout.write(f"[{i}/{len(licencas)}] Processando {alias}...")

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

                try:
                    criar_usuarios_if_not_exists(alias)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"[{alias}] Erro ao criar usuarios: {e}"))

                # 2️⃣ Dependências primeiro
                for dep in DEPENDENCY_APPS:
                    self.stdout.write(f"[{alias}] migrate {dep}")
                    try:
                        # Mute stdout to avoid verbose output from dependencies
                        with open(os.devnull, 'w') as devnull:
                            call_command(
                                "migrate",
                                dep,
                                database=alias,
                                interactive=False,
                                verbosity=0,
                                fake_initial=True,
                                stdout=devnull
                            )
                    except Exception as e:
                        if "column \"name\" of relation \"django_content_type\" does not exist" in str(e):
                            pass # Silenciosamente ignorar erro conhecido em dependências
                        else:
                            # Log warning but continue
                            self.stdout.write(self.style.WARNING(f"[{alias}] Aviso ao migrar dependência {dep}: {e}"))

                # 3️⃣ App alvo
                self.stdout.write(self.style.SUCCESS(f"[{alias}] migrate {app_label}"))
                def _run_migrate_app():
                    call_command(
                        "migrate",
                        app_label,
                        database=alias,
                        interactive=False,
                        verbosity=1,
                        fake_initial=True,
                    )

                def _apply_cfop_fake_for_legacy_conflict(msg: str) -> bool:
                    from django.db.migrations.recorder import MigrationRecorder

                    recorder = MigrationRecorder(connections[alias])
                    applied_migrations = recorder.applied_migrations()

                    def _record(migration_name: str) -> bool:
                        key = (app_label, migration_name)
                        if key in applied_migrations:
                            return False
                        recorder.record_applied(app_label, migration_name)
                        applied_migrations.add(key)
                        return True

                    to_record: list[str] = []

                    if "relation" in msg and "already exists" in msg:
                        if "produto_fiscal_padrao" in msg or "ncm_fiscal_padrao" in msg:
                            to_record.append("0002_auto_20260113_1534")
                        if "cfop_fiscal_padrao" in msg:
                            to_record.append("0006_cfopfiscalpadrao")
                        if "ncm_fiscal_padrao_ncm_id" in msg:
                            to_record.append("0009_ncmfiscalpadrao_multi")

                    if "column" in msg and "already exists" in msg:
                        if "cfop_fiscal_padrao" in msg or "ncm_fiscal_padrao" in msg or "produto_fiscal_padrao" in msg:
                            to_record.append("0007_fiscalpadrao_contexto")
                        if "column \"cfop\"" in msg and "ncm_fiscal_padrao" in msg:
                            to_record.append("0008_ncmfiscalpadrao_cfop")

                    if not to_record:
                        return False

                    changed = False
                    for migration_name in to_record:
                        if _record(migration_name):
                            changed = True
                            self.stdout.write(self.style.WARNING(f"[{alias}] Marcando {app_label}.{migration_name} como FAKED (registro direto)."))

                    return changed

                if app_label.lower() == "cfop":
                    attempts = 0
                    while True:
                        try:
                            _run_migrate_app()
                            break
                        except Exception as e:
                            msg = str(e)
                            if "column \"name\" of relation \"django_content_type\" does not exist" in msg:
                                self.stdout.write(self.style.WARNING(f"[{alias}] Ignorando erro de coluna name ao migrar {app_label}: {e}"))
                                break

                            applied_fix = _apply_cfop_fake_for_legacy_conflict(msg)
                            if applied_fix and attempts < 3:
                                attempts += 1
                                self.stdout.write(self.style.WARNING(f"[{alias}] Reexecutando migrate {app_label} após ajustes..."))
                                continue

                            self.stdout.write(self.style.ERROR(f"[{alias}] Erro crítico ao migrar {app_label}: {e}"))
                            break
                else:
                    try:
                        _run_migrate_app()
                    except Exception as e:
                        msg = str(e)
                        if "column \"name\" of relation \"django_content_type\" does not exist" in msg:
                            self.stdout.write(self.style.WARNING(f"[{alias}] Ignorando erro de coluna name ao migrar {app_label}: {e}"))
                        else:
                            self.stdout.write(self.style.ERROR(f"[{alias}] Erro crítico ao migrar {app_label}: {e}"))

                if app_label.lower() == "cfop":
                    try:
                        with connections[alias].cursor() as cursor:
                            cursor.execute(
                                """
                                SELECT column_name
                                FROM information_schema.columns
                                WHERE table_name = 'ncm_fiscal_padrao'
                                  AND column_name IN ('uf_origem', 'uf_destino', 'tipo_entidade')
                                """
                            )
                            cols = {r[0] for r in cursor.fetchall()}
                        missing = [c for c in ("uf_origem", "uf_destino", "tipo_entidade") if c not in cols]
                        if missing:
                            self.stdout.write(self.style.ERROR(f"[{alias}] ncm_fiscal_padrao ainda sem colunas: {', '.join(missing)}"))
                        else:
                            self.stdout.write(self.style.SUCCESS(f"[{alias}] ncm_fiscal_padrao com colunas de contexto OK"))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"[{alias}] Não foi possível validar colunas de ncm_fiscal_padrao: {e}"))
        except KeyboardInterrupt:
            self.stdout.write(self.style.ERROR("\n🛑 Operação interrompida pelo usuário."))
            sys.exit(0)
