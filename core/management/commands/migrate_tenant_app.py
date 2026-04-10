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


def montar_db_config(lic, *, sslmode_override: str | None = None):
    host = lic["db_host"]
    sslmode = sslmode_override or (lic.get("db_sslmode") if isinstance(lic, dict) else None) or os.getenv("DB_SSLMODE", "prefer")
    config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": lic["db_name"],
        "USER": lic["db_user"],
        "PASSWORD": lic["db_password"],
        "HOST": host,
        "PORT": lic["db_port"],
        "CONN_MAX_AGE": 60,
        "OPTIONS": get_ssl_options(host, sslmode),
    }
    return config

def get_ssl_options(host: str, sslmode: str):
    if host in ("localhost", "127.0.0.1"):
        return {}
    return {"sslmode": sslmode}

class Command(BaseCommand):
    help = "Roda migrate de um app específico em todos os bancos de licenças"

    def add_arguments(self, parser):
        parser.add_argument("app_label", type=str)
        parser.add_argument("--license", type=str, required=False, help="Slug da licença específica para rodar o migrate")
        parser.add_argument("--strict", action="store_true", help="Falha o comando (exit code != 0) se qualquer licença falhar")
        parser.add_argument("--run-syncdb", action="store_true", help="Cria tabelas de apps sem migrations (migrate --run-syncdb)")
        parser.add_argument("--no-fake-initial", action="store_true", help="Não usa fake_initial (força executar migrations iniciais)")

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
        strict = bool(options.get("strict"))
        run_syncdb = bool(options.get("run_syncdb"))
        fake_initial = not bool(options.get("no_fake_initial"))
        licencas = carregar_licencas_dict()

        if target_license:
            licencas = [l for l in licencas if l["slug"] == target_license]
            if not licencas:
                raise CommandError(f"Licença '{target_license}' não encontrada.")

        if not licencas:
            raise CommandError("Nenhuma licença encontrada")

        self.stdout.write(f"Encontradas {len(licencas)} licenças. Iniciando migração de '{app_label}'...")

        ok_count = 0
        skipped_count = 0
        failed_count = 0
        ok_aliases: list[str] = []
        skipped: dict[str, str] = {}
        failed: dict[str, str] = {}

        try:
            for i, lic in enumerate(licencas, 1):
                alias = lic["slug"]
                self.stdout.write(f"[{i}/{len(licencas)}] Processando {alias}...")

                def _close_conn():
                    try:
                        connections[alias].close()
                    except Exception:
                        pass

                def _configure_db(*, sslmode_override: str | None = None):
                    connections.databases[alias] = montar_db_config(lic, sslmode_override=sslmode_override)
                    _close_conn()

                def _test_conn() -> None:
                    with connections[alias].cursor() as cursor:
                        cursor.execute("SELECT 1")

                def _expected_tables_for_app() -> list[str]:
                    from django.apps import apps as django_apps

                    app_config = django_apps.get_app_config(app_label)
                    tables: list[str] = []
                    for model in app_config.get_models():
                        opts = model._meta
                        if not getattr(opts, "managed", True):
                            continue
                        if getattr(opts, "proxy", False):
                            continue
                        if getattr(opts, "swapped", False):
                            continue
                        tables.append(opts.db_table)
                    return sorted(set(tables))

                def _missing_tables(table_names: list[str]) -> list[str]:
                    if not table_names:
                        return []
                    placeholders = ", ".join(["%s"] * len(table_names))
                    with connections[alias].cursor() as cursor:
                        cursor.execute(
                            f"""
                            SELECT table_name
                            FROM information_schema.tables
                            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                              AND table_name IN ({placeholders})
                            """,
                            table_names,
                        )
                        existing = {r[0] for r in cursor.fetchall()}
                    return [t for t in table_names if t not in existing]

                def _ensure_app_tables_created() -> bool:
                    from django.db.migrations.recorder import MigrationRecorder

                    expected = _expected_tables_for_app()
                    missing = _missing_tables(expected)
                    if not missing:
                        return True

                    self.stdout.write(self.style.ERROR(f"[{alias}] Tabelas do app '{app_label}' ausentes: {', '.join(missing)}"))
                    self.stdout.write(self.style.WARNING(f"[{alias}] Tentando reaplicar migrations de '{app_label}' (limpando django_migrations do app)..."))

                    recorder = MigrationRecorder(connections[alias])
                    recorder.migration_qs.filter(app=app_label).delete()

                    call_command(
                        "migrate",
                        app_label,
                        database=alias,
                        interactive=False,
                        verbosity=1,
                        fake_initial=False,
                        run_syncdb=run_syncdb,
                    )

                    missing_after = _missing_tables(expected)
                    if missing_after and not run_syncdb:
                        self.stdout.write(self.style.WARNING(f"[{alias}] Tentando novamente com --run-syncdb para forçar criação de tabelas..."))
                        call_command(
                            "migrate",
                            app_label,
                            database=alias,
                            interactive=False,
                            verbosity=1,
                            fake_initial=False,
                            run_syncdb=True,
                        )
                        missing_after = _missing_tables(expected)
                    if missing_after:
                        self.stdout.write(self.style.ERROR(f"[{alias}] Ainda faltando após reaplicar: {', '.join(missing_after)}"))
                        return False

                    self.stdout.write(self.style.SUCCESS(f"[{alias}] Tabelas de '{app_label}' criadas após reaplicar migrations."))
                    return True

                def _repair_legacy_contenttype() -> None:
                    with connections[alias].cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT 1
                            FROM information_schema.tables
                            WHERE table_name = 'django_content_type'
                            """
                        )
                        if not cursor.fetchone():
                            return

                        cursor.execute(
                            """
                            SELECT column_name, is_nullable
                            FROM information_schema.columns
                            WHERE table_name = 'django_content_type'
                              AND column_name = 'name'
                            """
                        )
                        row = cursor.fetchone()
                        if not row:
                            cursor.execute(
                                """
                                ALTER TABLE django_content_type
                                ADD COLUMN name VARCHAR(255) NULL;
                                """
                            )
                            return

                        _, is_nullable = row
                        if is_nullable == "NO":
                            cursor.execute(
                                """
                                ALTER TABLE django_content_type
                                ALTER COLUMN name DROP NOT NULL;
                                """
                            )

                _configure_db()
                try:
                    _test_conn()
                except OperationalError as e:
                    msg = str(e)
                    retry_sslmode = None
                    lower = msg.lower()
                    if "ssl" in lower:
                        retry_sslmode = "disable"
                    if retry_sslmode:
                        try:
                            self.stdout.write(self.style.WARNING(f"[{alias}] Falha de conexão com SSL. Tentando sslmode={retry_sslmode}..."))
                            _configure_db(sslmode_override=retry_sslmode)
                            _test_conn()
                        except Exception as e2:
                            skipped_count += 1
                            skipped[alias] = str(e2)
                            self.stdout.write(self.style.ERROR(f"[{alias}] Banco de dados não encontrado ou inacessível. Pulando... ({e2})"))
                            continue
                    else:
                        skipped_count += 1
                        skipped[alias] = msg
                        self.stdout.write(self.style.ERROR(f"[{alias}] Banco de dados não encontrado ou inacessível. Pulando... ({e})"))
                        continue
                except Exception as e:
                    failed_count += 1
                    failed[alias] = str(e)
                    self.stdout.write(self.style.ERROR(f"[{alias}] Erro de conexão: {e}"))
                    continue

                license_failed = False
                self.stdout.write(self.style.WARNING(f"[{alias}] preparando banco"))

                # 1️⃣ Ajuste defensivo para bancos antigos
                try:
                    _repair_legacy_contenttype()
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
                                fake_initial=fake_initial,
                                run_syncdb=run_syncdb,
                                stdout=devnull,
                                stderr=devnull,
                            )
                    except Exception as e:
                        msg = str(e)
                        if "column \"name\" of relation \"django_content_type\" does not exist" in msg:
                            try:
                                _repair_legacy_contenttype()
                                with open(os.devnull, 'w') as devnull:
                                    call_command(
                                        "migrate",
                                        dep,
                                        database=alias,
                                        interactive=False,
                                        verbosity=0,
                                        fake_initial=fake_initial,
                                        run_syncdb=run_syncdb,
                                        stdout=devnull,
                                        stderr=devnull,
                                    )
                                continue
                            except Exception as e2:
                                license_failed = True
                                failed[alias] = str(e2)
                                self.stdout.write(self.style.ERROR(f"[{alias}] Erro ao migrar dependência {dep}: {e2}"))
                                break

                        license_failed = True
                        failed[alias] = msg
                        self.stdout.write(self.style.ERROR(f"[{alias}] Erro ao migrar dependência {dep}: {e}"))
                        break

                if license_failed:
                    failed_count += 1
                    _close_conn()
                    continue

                # 3️⃣ App alvo
                self.stdout.write(self.style.SUCCESS(f"[{alias}] migrate {app_label}"))
                def _run_migrate_app():
                    call_command(
                        "migrate",
                        app_label,
                        database=alias,
                        interactive=False,
                        verbosity=1,
                        fake_initial=fake_initial,
                        run_syncdb=run_syncdb,
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
                            if not _ensure_app_tables_created():
                                license_failed = True
                                failed[alias] = f"Tabelas do app '{app_label}' não foram criadas"
                            break
                        except Exception as e:
                            msg = str(e)
                            if "column \"name\" of relation \"django_content_type\" does not exist" in msg:
                                try:
                                    _repair_legacy_contenttype()
                                    attempts += 1
                                    if attempts <= 3:
                                        self.stdout.write(self.style.WARNING(f"[{alias}] Reparando django_content_type.name e reexecutando migrate {app_label}..."))
                                        continue
                                except Exception as e2:
                                    msg = str(e2)

                            applied_fix = _apply_cfop_fake_for_legacy_conflict(msg)
                            if applied_fix and attempts < 3:
                                attempts += 1
                                self.stdout.write(self.style.WARNING(f"[{alias}] Reexecutando migrate {app_label} após ajustes..."))
                                continue

                            self.stdout.write(self.style.ERROR(f"[{alias}] Erro crítico ao migrar {app_label}: {e}"))
                            license_failed = True
                            failed[alias] = str(e)
                            break
                else:
                    try:
                        _run_migrate_app()
                        if not _ensure_app_tables_created():
                            license_failed = True
                            failed[alias] = f"Tabelas do app '{app_label}' não foram criadas"
                    except Exception as e:
                        msg = str(e)
                        if "column \"name\" of relation \"django_content_type\" does not exist" in msg:
                            try:
                                _repair_legacy_contenttype()
                                self.stdout.write(self.style.WARNING(f"[{alias}] Reparando django_content_type.name e reexecutando migrate {app_label}..."))
                                _run_migrate_app()
                                if not _ensure_app_tables_created():
                                    license_failed = True
                                    failed[alias] = f"Tabelas do app '{app_label}' não foram criadas"
                            except Exception as e2:
                                self.stdout.write(self.style.ERROR(f"[{alias}] Erro crítico ao migrar {app_label}: {e2}"))
                                license_failed = True
                                failed[alias] = str(e2)
                        else:
                            self.stdout.write(self.style.ERROR(f"[{alias}] Erro crítico ao migrar {app_label}: {e}"))
                            license_failed = True
                            failed[alias] = str(e)

                if app_label.lower() == "cfop" and not license_failed:
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
                            license_failed = True
                            failed[alias] = f"ncm_fiscal_padrao sem colunas: {', '.join(missing)}"
                        else:
                            self.stdout.write(self.style.SUCCESS(f"[{alias}] ncm_fiscal_padrao com colunas de contexto OK"))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"[{alias}] Não foi possível validar colunas de ncm_fiscal_padrao: {e}"))

                if license_failed:
                    failed_count += 1
                else:
                    ok_count += 1
                    ok_aliases.append(alias)
                try:
                    connections[alias].close()
                except Exception:
                    pass
        except KeyboardInterrupt:
            self.stdout.write(self.style.ERROR("\n🛑 Operação interrompida pelo usuário."))
            sys.exit(0)

        self.stdout.write(self.style.SUCCESS(f"Finalizado: ok={ok_count} | pulados={skipped_count} | falhas={failed_count}"))
        if skipped:
            skipped_preview = ", ".join(list(skipped.keys())[:20])
            self.stdout.write(self.style.WARNING(f"Pulados ({len(skipped)}): {skipped_preview}"))
        if failed:
            failed_preview = ", ".join(list(failed.keys())[:20])
            self.stdout.write(self.style.ERROR(f"Falhas ({len(failed)}): {failed_preview}"))
        if strict:
            if ok_count == 0 and skipped_count > 0:
                raise CommandError("Nenhuma licença foi migrada (todas foram puladas por falha de conexão).")
            if failed_count > 0:
                raise CommandError(f"{failed_count} licença(s) falharam ao migrar '{app_label}'. Veja o log acima para detalhes.")
