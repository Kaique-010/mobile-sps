from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import OperationalError

from core.licencas_loader import carregar_licencas_dict


def _alter_table(alias: str):
    with connections[alias].cursor() as cursor:
        cursor.execute(
            """
            create table if not exists bombasaldos (
                bomb_id bigserial,
                bomb_empr integer not null,
                bomb_fili integer not null,
                bomb_bomb varchar(10),
                bomb_comb varchar(10),
                bomb_sald numeric(15,4),
                bomb_tipo_movi integer,
                bomb_data date,
                bomb_usua integer
            );

            alter table bombasaldos
            add column if not exists bomb_empr integer;
            alter table bombasaldos
            add column if not exists bomb_fili integer;
            alter table bombasaldos
            add column if not exists bomb_bomb varchar(10);
            alter table bombasaldos
            add column if not exists bomb_comb varchar(10);
            alter table bombasaldos
            add column if not exists bomb_sald numeric(15,4);
            alter table bombasaldos
            add column if not exists bomb_tipo_movi integer;
            alter table bombasaldos
            add column if not exists bomb_data date;
            alter table bombasaldos
            add column if not exists bomb_usua integer;

            do $$
            begin
                if not exists (
                    select 1
                    from information_schema.columns
                    where table_name = 'bombasaldos'
                      and column_name = 'bomb_id'
                ) then
                    alter table bombasaldos add column bomb_id bigserial;
                end if;
            end $$;
            """
        )
        cursor.execute(
            """
            update bombasaldos
            set bomb_id = nextval(pg_get_serial_sequence('bombasaldos', 'bomb_id'))
            where bomb_id is null;
            """
        )
        cursor.execute(
            """
            alter table bombasaldos
            alter column bomb_id set not null;
            """
        )
        cursor.execute(
            """
            create unique index if not exists bombasaldos_bomb_id_uq
            on bombasaldos (bomb_id);
            """
        )
        cursor.execute(
            """
            do $$
            begin
                if not exists (
                    select 1
                    from pg_constraint c
                    join pg_class t on t.oid = c.conrelid
                    where t.relname = 'bombasaldos'
                      and c.contype = 'p'
                ) then
                    alter table bombasaldos add constraint bombasaldos_pk primary key (bomb_id);
                end if;
            end $$;
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
    help = "Cria a coluna bomb_id em bombasaldos (PK lógica) em todos os tenants (ou um específico)."

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

            self.stdout.write(self.style.WARNING(f"[{alias}] Atualizando tabela bombasaldos (bomb_id)..."))
            try:
                _alter_table(alias)
                self.stdout.write(self.style.SUCCESS(f"[{alias}] Campo atualizado com sucesso!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro ao atualizar campo: {e}"))

