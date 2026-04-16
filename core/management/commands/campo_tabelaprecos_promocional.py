from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import OperationalError

from core.licencas_loader import carregar_licencas_dict


def _alter_tables(alias: str):
    with connections[alias].cursor() as cursor:
        cursor.execute(
            """
            do $$
            begin
                if to_regclass('public.tabelaprecos_promocional') is null
                   and to_regclass('public.tabelaprecospromocional') is not null then
                    alter table public.tabelaprecospromocional rename to tabelaprecos_promocional;
                end if;

                if to_regclass('public."tabelaprecosPromocionalhist"') is null
                   and to_regclass('public.tabelaprecospromocionalhist') is not null then
                    alter table public.tabelaprecospromocionalhist rename to "tabelaprecosPromocionalhist";
                end if;
            end $$;

            create table if not exists tabelaprecos_promocional (
                tabe_empr integer,
                tabe_fili integer,
                tabe_prod varchar(60),
                tabe_prco numeric(15,2),
                tabe_desp numeric(15,4),
                tabe_cust numeric(15,2),
                tabe_marg numeric(15,4),
                tabe_cuge numeric(15,2),
                tabe_avis numeric(15,2),
                tabe_praz numeric(15,4),
                tabe_apra numeric(15,2),
                tabe_hist text,
                tabe_perc_reaj numeric(15,2)
            );

            alter table tabelaprecos_promocional add column if not exists tabe_empr integer;
            alter table tabelaprecos_promocional add column if not exists tabe_fili integer;
            alter table tabelaprecos_promocional add column if not exists tabe_prod varchar(60);
            alter table tabelaprecos_promocional add column if not exists tabe_prco numeric(15,2);
            alter table tabelaprecos_promocional add column if not exists tabe_desp numeric(15,4);
            alter table tabelaprecos_promocional add column if not exists tabe_cust numeric(15,2);
            alter table tabelaprecos_promocional add column if not exists tabe_marg numeric(15,4);
            alter table tabelaprecos_promocional add column if not exists tabe_cuge numeric(15,2);
            alter table tabelaprecos_promocional add column if not exists tabe_avis numeric(15,2);
            alter table tabelaprecos_promocional add column if not exists tabe_praz numeric(15,4);
            alter table tabelaprecos_promocional add column if not exists tabe_apra numeric(15,2);
            alter table tabelaprecos_promocional add column if not exists tabe_hist text;
            alter table tabelaprecos_promocional add column if not exists tabe_perc_reaj numeric(15,2);

            create unique index if not exists tabelaprecos_promocional_uq
            on tabelaprecos_promocional (tabe_empr, tabe_fili, tabe_prod);

            create index if not exists tabelaprecos_promocional_prod_idx
            on tabelaprecos_promocional (tabe_prod);

            create table if not exists "tabelaprecosPromocionalhist" (
                tabe_id bigserial,
                tabe_empr integer,
                tabe_fili integer,
                tabe_prod varchar(20),
                tabe_data_hora timestamp without time zone,
                tabe_perc_reaj numeric(15,2),
                tabe_avis_ante numeric(15,2),
                tabe_avis_novo numeric(15,2),
                tabe_apra_ante numeric(15,2),
                tabe_apra_novo numeric(15,2),
                tabe_hist text,
                tabe_prco_ante numeric(15,2),
                tabe_prco_novo numeric(15,2),
                tabe_desp_ante numeric(15,2),
                tabe_desp_novo numeric(15,2),
                tabe_cust_ante numeric(15,2),
                tabe_cust_novo numeric(15,2),
                tabe_cuge_ante numeric(15,2),
                tabe_cuge_novo numeric(15,2),
                tabe_marg_ante numeric(15,2),
                tabe_marg_novo numeric(15,2),
                tabe_praz_ante numeric(15,2),
                tabe_praz_novo numeric(15,2)
            );

            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_id bigint;
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_empr integer;
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_fili integer;
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_prod varchar(20);
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_data_hora timestamp without time zone;
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_perc_reaj numeric(15,2);
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_avis_ante numeric(15,2);
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_avis_novo numeric(15,2);
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_apra_ante numeric(15,2);
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_apra_novo numeric(15,2);
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_hist text;
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_prco_ante numeric(15,2);
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_prco_novo numeric(15,2);
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_desp_ante numeric(15,2);
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_desp_novo numeric(15,2);
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_cust_ante numeric(15,2);
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_cust_novo numeric(15,2);
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_cuge_ante numeric(15,2);
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_cuge_novo numeric(15,2);
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_marg_ante numeric(15,2);
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_marg_novo numeric(15,2);
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_praz_ante numeric(15,2);
            alter table "tabelaprecosPromocionalhist" add column if not exists tabe_praz_novo numeric(15,2);

            do $$
            declare
                seq_name text;
                max_id bigint;
            begin
                seq_name := pg_get_serial_sequence('"tabelaprecosPromocionalhist"', 'tabe_id');
                if seq_name is null then
                    seq_name := 'tabelaprecospromocionalhist_tabe_id_seq';
                    execute format('create sequence if not exists %s', seq_name);
                    execute format(
                        'alter table "tabelaprecosPromocionalhist" alter column tabe_id set default nextval(''%s'')',
                        seq_name
                    );
                else
                    execute format(
                        'alter table "tabelaprecosPromocionalhist" alter column tabe_id set default nextval(''%s'')',
                        seq_name
                    );
                end if;

                execute format(
                    'update "tabelaprecosPromocionalhist" set tabe_id = nextval(''%s'') where tabe_id is null',
                    seq_name
                );

                execute 'select coalesce(max(tabe_id), 0) from "tabelaprecosPromocionalhist"' into max_id;
                if max_id < 1 then
                    execute format('select setval(''%s'', 1, false)', seq_name);
                else
                    execute format('select setval(''%s'', %s, true)', seq_name, max_id);
                end if;

                execute 'alter table "tabelaprecosPromocionalhist" alter column tabe_id set not null';
            end $$;

            do $$
            begin
                if not exists (
                    select 1
                    from pg_constraint c
                    join pg_class t on t.oid = c.conrelid
                    where t.relname = 'tabelaprecosPromocionalhist'
                      and c.contype = 'p'
                ) then
                    alter table "tabelaprecosPromocionalhist"
                    add constraint tabelaprecospromocionalhist_pk primary key (tabe_id);
                end if;
            end $$;

            create index if not exists tabelaprecospromocionalhist_prod_idx
            on "tabelaprecosPromocionalhist" (tabe_empr, tabe_fili, tabe_prod, tabe_data_hora);
            """
        )


def _verificar_tabelas(alias: str):
    with connections[alias].cursor() as cursor:
        cursor.execute(
            """
            select
                to_regclass('public.tabelaprecos_promocional'),
                to_regclass('public."tabelaprecosPromocionalhist"')
            """
        )
        return cursor.fetchone()


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
    help = "Cria/atualiza tabelas de preços promocionais em todos os tenants (ou em tenant específico)."

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

        ok = 0
        falhas = 0
        for lic in licencas:
            alias = f"tenant_{lic['slug']}"
            connections.databases[alias] = montar_db_config(lic)

            try:
                with connections[alias].cursor() as cursor:
                    cursor.execute("SELECT 1")
            except OperationalError:
                self.stdout.write(self.style.ERROR(f"[{alias}] Banco de dados não encontrado ou inacessível. Pulando..."))
                continue

            self.stdout.write(self.style.WARNING(f"[{alias}] Atualizando tabelas de preços promocionais..."))
            try:
                _alter_tables(alias)
                regclass_preco, regclass_hist = _verificar_tabelas(alias)
                if not regclass_preco or not regclass_hist:
                    raise CommandError(
                        f"[{alias}] Verificação falhou: "
                        f"tabelaprecos_promocional={regclass_preco} "
                        f"tabelaprecosPromocionalhist={regclass_hist}"
                    )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[{alias}] OK -> {regclass_preco} | {regclass_hist}"
                    )
                )
                ok += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro ao atualizar tabelas: {e}"))
                falhas += 1

        self.stdout.write(
            self.style.WARNING(
                f"Finalizado: {ok} tenant(s) com sucesso, {falhas} com falha."
            )
        )
