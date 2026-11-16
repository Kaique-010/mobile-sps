
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction
from django.db.utils import OperationalError
from core.licencas_loader import carregar_licencas_dict


def produtosDetalhados(alias):
    """
    Atualiza os índices e recria a VIEW produtos_detalhados
    para uma base específica de licença.
    """

    print(f"[{alias}] Preparando otimizações de produtos...")

    with transaction.atomic(using=alias):
        with connections[alias].cursor() as cursor:

            # --------------------------------------------------
            # 1. EXTENSÃO PARA BUSCAS TEXTUAIS
            # --------------------------------------------------

            cursor.execute("""
                CREATE EXTENSION IF NOT EXISTS pg_trgm;
            """)

            # --------------------------------------------------
            # 2. ÍNDICE DO HISTÓRICO DE PREÇOS
            # Busca o preço mais recente por empresa, filial
            # e produto.
            # --------------------------------------------------

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS
                    idx_tabelaprecoshist_ultimo_preco
                ON tabelaprecoshist (
                    tabe_empr,
                    tabe_fili,
                    tabe_prod,
                    tabe_data_hora DESC,
                    tabe_id DESC
                );
            """)

            # --------------------------------------------------
            # 3. ÍNDICE DOS SALDOS
            # --------------------------------------------------

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS
                    idx_saldosprodutos_empresa_filial_produto
                ON saldosprodutos (
                    sapr_empr,
                    sapr_prod,
                    sapr_fili
                );
            """)

            # --------------------------------------------------
            # 4. ÍNDICES PARA PESQUISA DE PRODUTOS
            # --------------------------------------------------

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS
                    idx_produtos_codigo_trgm
                ON produtos
                USING gin (
                    UPPER(prod_codi::text) gin_trgm_ops
                );
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS
                    idx_produtos_nome_trgm
                ON produtos
                USING gin (
                    UPPER(prod_nome) gin_trgm_ops
                );
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS
                    idx_marca_nome_trgm
                ON marca
                USING gin (
                    UPPER(marc_nome) gin_trgm_ops
                );
            """)

            print(f"[{alias}] Índices verificados.")

            # --------------------------------------------------
            # 5. REMOVE A VIEW ANTIGA
            # --------------------------------------------------

            cursor.execute("""
                DROP VIEW IF EXISTS public.produtos_detalhados;
            """)

            # --------------------------------------------------
            # 6. RECRIA A VIEW
            # --------------------------------------------------

            cursor.execute("""
                CREATE VIEW public.produtos_detalhados AS

                SELECT
                    prod.prod_codi AS codigo,
                    prod.prod_nome AS nome,
                    prod.prod_unme AS unidade,

                    prod.prod_grup AS grupo_id,
                    grup.grup_desc AS grupo_nome,

                    prod.prod_marc AS marca_id,
                    marc.marc_nome AS marca_nome,

                    hist.tabe_cuge_novo AS custo,
                    hist.tabe_avis_novo AS preco_vista,
                    hist.tabe_apra_novo AS preco_prazo,

                    sald.sapr_sald AS saldo,
                    prod.prod_foto AS foto,
                    prod.prod_peso_brut AS peso_bruto,
                    prod.prod_peso_liqu AS peso_liquido,

                    sald.sapr_empr AS empresa,
                    sald.sapr_fili AS filial,

                    COALESCE(hist.tabe_cuge_novo, 0)
                        * COALESCE(sald.sapr_sald, 0)
                        AS valor_total_estoque,

                    COALESCE(hist.tabe_avis_novo, 0)
                        * COALESCE(sald.sapr_sald, 0)
                        AS valor_total_venda_vista,

                    COALESCE(hist.tabe_apra_novo, 0)
                        * COALESCE(sald.sapr_sald, 0)
                        AS valor_total_venda_prazo,

                    prod.prod_ncm AS ncm

                FROM produtos prod

                LEFT JOIN gruposprodutos grup
                    ON prod.prod_grup = grup.grup_codi

                LEFT JOIN marca marc
                    ON prod.prod_marc = marc.marc_codi

                LEFT JOIN saldosprodutos sald
                    ON prod.prod_codi = sald.sapr_prod
                    AND prod.prod_empr = sald.sapr_empr

                LEFT JOIN LATERAL (

                    SELECT
                        h.tabe_cuge_novo,
                        h.tabe_avis_novo,
                        h.tabe_apra_novo

                    FROM tabelaprecoshist h

                    WHERE
                        h.tabe_prod = prod.prod_codi
                        AND h.tabe_empr = sald.sapr_empr
                        AND h.tabe_fili = sald.sapr_fili

                    ORDER BY
                        h.tabe_data_hora DESC,
                        h.tabe_id DESC

                    LIMIT 1

                ) hist ON TRUE;
            """)

    print(f"[{alias}] VIEW produtos_detalhados atualizada com sucesso.")



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
    help = "Atualiza apenas a view produtos_detalhados em todos os bancos de licenças"

    def add_arguments(self, parser):
        parser.add_argument("--slug", type=str, default="saveweb001")
        parser.add_argument("--teste-baixa", action="store_true")

    def handle(self, *args, **options):
        licencas = carregar_licencas_dict()

        if not licencas:
            raise CommandError("Nenhuma licença encontrada")

        if options.get("teste_baixa"):
            slug = (options.get("slug") or "").strip()

            lic = next(
                (
                    l for l in licencas
                    if str(l.get("slug", "")).strip() == slug
                ),
                None,
            )

            if not lic:
                raise CommandError(
                    f"Licença não encontrada para slug={slug}"
                )

            self._atualizar_view(lic)
            return

        for lic in licencas:
            self._atualizar_view(lic)

    def _atualizar_view(self, lic):
        alias = f"tenant_{lic['slug']}"

        connections.databases[alias] = montar_db_config(lic)

        try:
            with connections[alias].cursor() as cursor:
                cursor.execute("SELECT 1")

        except OperationalError:
            self.stdout.write(
                self.style.ERROR(
                    f"[{alias}] Banco inacessível. Pulando..."
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f"[{alias}] Atualizando produtos_detalhados..."
            )
        )

        try:
            produtosDetalhados(alias)

            self.stdout.write(
                self.style.SUCCESS(
                    f"[{alias}] VIEW atualizada com sucesso!"
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"[{alias}] Erro ao atualizar VIEW: {e}"
                )
            )
