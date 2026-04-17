from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import OperationalError

from core.licencas_loader import carregar_licencas_dict


def _alter_table(alias: str):
    with connections[alias].cursor() as cursor:
        cursor.execute(
            """
            alter table tabelaprecos
            add column if not exists tabe_id bigserial;

            update tabelaprecos
            set tabe_id = nextval(pg_get_serial_sequence('tabelaprecos', 'tabe_id'))
            where tabe_id is null;

            alter table tabelaprecos
            alter column tabe_id set not null;

            create unique index if not exists tabelaprecos_tabe_id_uq
            on tabelaprecos (tabe_id);

            alter table tabelaprecos
            alter column tabe_id set default nextval(pg_get_serial_sequence('tabelaprecos', 'tabe_id'));

            alter table tabelaprecos_promocional
            add column if not exists tabe_id bigserial;

            update tabelaprecos_promocional
            set tabe_id = nextval(pg_get_serial_sequence('tabelaprecos_promocional', 'tabe_id'))
            where tabe_id is null;

            alter table tabelaprecos_promocional
            alter column tabe_id set not null;

            create unique index if not exists tabelaprecos_promocional_tabe_id_uq
            on tabelaprecos_promocional (tabe_id);

            alter table tabelaprecos_promocional
            alter column tabe_id set default nextval(pg_get_serial_sequence('tabelaprecos_promocional', 'tabe_id'));
            """
        )


def montar_db_config(lic):
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": lic["db_name"],
        "USER": lic["db_user"],
        "PASSWORD": lic["db_password"],
        "HOST": lic["db_host"],
        "PORT": lic["db_port"],
        "CONN_MAX_AGE": 60,
    }


class Command(BaseCommand):
    help = "Cria a coluna tabe_id (chave técnica) em tabelaprecos e tabelaprecos_promocional em todos os tenants (ou um específico)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--slug",
            type=str,
            help="Slug do tenant específico. Se omitido, roda em todos os tenants.",
        )
        parser.add_argument(
            "--tenant",
            type=str,
            help="Alias de --slug (compatibilidade).",
        )

    def handle(self, *args, **options):
        slug = options.get("slug")
        tenant = options.get("tenant")
        if slug and tenant and slug != tenant:
            raise CommandError("Use apenas um entre --slug e --tenant (ou informe o mesmo valor em ambos).")

        slug_alvo = slug or tenant
        licencas = carregar_licencas_dict()
        if not licencas:
            raise CommandError("Nenhuma licença encontrada")

        if slug_alvo:
            licencas = [l for l in licencas if l.get("slug") == slug_alvo]
            if not licencas:
                raise CommandError(f"Nenhuma licença encontrada para slug={slug_alvo}")

        for lic in licencas:
            alias = f"tenant_{lic['slug']}"
            connections.databases[alias] = montar_db_config(lic)

            try:
                with connections[alias].cursor() as cursor:
                    cursor.execute("SELECT 1")
            except OperationalError:
                self.stdout.write(self.style.ERROR(f"[{alias}] Banco de dados não encontrado ou inacessível. Pulando..."))
                continue

            self.stdout.write(self.style.WARNING(f"[{alias}] Criando tabe_id em tabelaprecos e tabelaprecos_promocional..."))
            try:
                _alter_table(alias)
                self.stdout.write(self.style.SUCCESS(f"[{alias}] Campo tabe_id criado/ajustado com sucesso!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro ao criar/ajustar campo tabe_id: {e}"))
