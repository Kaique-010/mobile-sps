from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import OperationalError
from core.licencas_loader import carregar_licencas_dict
from Notas_Fiscais.models import Nota, NotaItem, NotaItemImposto, Transporte, NotaEvento
from CFOP.models import CFOP, MapaCFOP, TabelaICMS, NCM_CFOP_DIF, NcmFiscalPadrao
from Produtos.models import Ncm, NcmAliquota


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


def listar_colunas_existentes(alias: str, table_name: str) -> set:
    with connections[alias].cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
              AND table_schema = 'public'
            """,
            [table_name],
        )
        rows = cursor.fetchall()
    return {r[0] for r in rows}


def sync_model_fields(alias: str, model):
    table = model._meta.db_table
    existentes = listar_colunas_existentes(alias, table)

    concrete_fields = [
        f
        for f in model._meta.get_fields()
        if hasattr(f, "column") and f.column and not f.many_to_many and not f.auto_created
    ]

    conn = connections[alias]
    with conn.schema_editor() as editor:
        for field in concrete_fields:
            column = field.column
            if column in existentes:
                continue
            editor.add_field(model, field)


def sync_tenant(alias: str):
    modelos_nf = [Nota, NotaItem, NotaItemImposto, Transporte, NotaEvento]
    modelos_cfop = [CFOP, MapaCFOP, TabelaICMS, NCM_CFOP_DIF, NcmFiscalPadrao]
    modelos_ncm = [Ncm, NcmAliquota]

    for m in modelos_nf + modelos_cfop + modelos_ncm:
        sync_model_fields(alias, m)


class Command(BaseCommand):
    help = "Cria campos faltantes dos models de NF, CFOP e NCM em um ou todos os tenants"

    def add_arguments(self, parser):
        parser.add_argument(
            "--slug",
            type=str,
            help="Slug do tenant específico. Se omitido, roda em todos os tenants.",
        )

    def handle(self, *args, **options):
        slug_alvo = options.get("slug")
        licencas = carregar_licencas_dict()

        if not licencas:
            raise CommandError("Nenhuma licença encontrada")

        if slug_alvo:
            licencas = [l for l in licencas if l.get("slug") == slug_alvo]
            if not licencas:
                raise CommandError(f"Nenhuma licença encontrada para slug={slug_alvo}")

        for lic in licencas:
            slug = lic["slug"]
            alias = f"tenant_{slug}"
            connections.databases[alias] = montar_db_config(lic)

            try:
                with connections[alias].cursor() as cursor:
                    cursor.execute("SELECT 1")
            except OperationalError:
                self.stdout.write(self.style.ERROR(f"[{alias}] Banco de dados não encontrado ou inacessível. Pulando..."))
                continue

            alvo_txt = f" (slug={slug_alvo})" if slug_alvo else ""
            self.stdout.write(self.style.WARNING(f"[{alias}] Sincronizando campos de NF, CFOP e NCM{alvo_txt}"))

            try:
                sync_tenant(alias)
                self.stdout.write(self.style.SUCCESS(f"[{alias}] Campos sincronizados com sucesso"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro ao sincronizar campos: {e}"))

