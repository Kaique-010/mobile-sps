from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import OperationalError
from core.licencas_loader import carregar_licencas_dict

def produtosDetalhados(alias: str):
    with connections[alias].cursor() as cursor:
        cursor.execute(
            """
            DROP VIEW IF EXISTS public.produtos_detalhados;
            -- View produtos_detalhados
            CREATE OR REPLACE VIEW public.produtos_detalhados
            AS
            SELECT
            prod.prod_codi AS codigo,
            prod.prod_nome AS nome,
            prod.prod_unme AS unidade,
            prod.prod_grup AS grupo_id,
            grup.grup_desc AS grupo_nome,
            prod.prod_marc AS marca_id,
            marc.marc_nome AS marca_nome,
            tabe.tabe_cuge AS custo,
            tabe.tabe_avis AS preco_vista,
            tabe.tabe_apra AS preco_prazo,
            sald.sapr_sald AS saldo,
            prod.prod_foto AS foto,
            prod.prod_peso_brut AS peso_bruto,
            prod.prod_peso_liqu AS peso_liquido,
            sald.sapr_empr AS empresa,
            sald.sapr_fili AS filial,
            COALESCE(tabe.tabe_cuge, 0) * COALESCE(sald.sapr_sald, 0) AS valor_total_estoque,
            COALESCE(tabe.tabe_avis, 0) * COALESCE(sald.sapr_sald, 0) AS valor_total_venda_vista,
            COALESCE(tabe.tabe_apra, 0) * COALESCE(sald.sapr_sald, 0) AS valor_total_venda_prazo,
            prod.prod_ncm AS ncm
            FROM produtos prod
            LEFT JOIN gruposprodutos grup ON prod.prod_grup = grup.grup_codi
            LEFT JOIN marca marc ON prod.prod_marc = marc.marc_codi
            LEFT JOIN saldosprodutos sald
            ON prod.prod_codi = sald.sapr_prod
            AND prod.prod_empr = sald.sapr_empr

            LEFT JOIN tabelaprecos tabe
            ON prod.prod_codi = tabe.tabe_prod
            AND sald.sapr_empr = tabe.tabe_empr
            AND sald.sapr_fili = tabe.tabe_fili  
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
    help = "Atualiza apenas a view produtos_detalhados em todos os bancos de licenças"

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

            self.stdout.write(self.style.WARNING(f"[{alias}] Atualizando view produtos_detalhados..."))

            try:
                produtosDetalhados(alias)
                self.stdout.write(self.style.SUCCESS(f"[{alias}] View atualizada com sucesso!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro ao atualizar view: {e}"))
