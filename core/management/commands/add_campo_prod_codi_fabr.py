"""Padroniza a view `produtos_detalhados` em todos os tenants (ou em um específico).

Garante:
  1. A coluna `prod_codi_fabr` na tabela `produtos` (criada quando ausente).
  2. A estrutura única da view, incluindo o campo `codigo_do_fabricante`.

`CREATE OR REPLACE VIEW` não permite alterar/renomear colunas de uma view
existente, por isso a view é removida (DROP ... CASCADE) antes de ser recriada.

Uso:
    python manage.py add_campo_prod_codi_fabr
    python manage.py add_campo_prod_codi_fabr --slug gold
    python manage.py add_campo_prod_codi_fabr --tenant gold
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import DatabaseError, OperationalError

from core.licencas_loader import carregar_licencas_dict


# Estrutura única da view produtos_detalhados (idêntica em todos os tenants)
VIEW_PRODUTOS_DETALHADOS_SQL = """
ALTER TABLE produtos ADD COLUMN IF NOT EXISTS prod_codi_fabr varchar(60);

DROP VIEW IF EXISTS public.produtos_detalhados CASCADE;

CREATE OR REPLACE VIEW public.produtos_detalhados AS
SELECT
    prod.prod_codi AS codigo,
    prod.prod_nome AS nome,
    prod.prod_unme AS unidade,
    prod.prod_grup AS grupo_id,
    grup.grup_desc AS grupo_nome,
    prod.prod_marc AS marca_id,
    prod.prod_ncm AS ncm,
    marc.marc_nome AS marca_nome,
    tabe.tabe_cuge AS custo,
    tabe.tabe_avis AS preco_vista,
    tabe.tabe_apra AS preco_prazo,
    sald.sapr_sald AS saldo,
    prod.prod_foto AS foto,
    prod.prod_codi_fabr AS codigo_do_fabricante,
    prod.prod_peso_brut AS peso_bruto,
    prod.prod_peso_liqu AS peso_liquido,
    sald.sapr_empr AS empresa,
    sald.sapr_fili AS filial,
    COALESCE(tabe.tabe_cuge, 0::numeric) * COALESCE(sald.sapr_sald, 0::numeric) AS valor_total_estoque,
    COALESCE(tabe.tabe_avis, 0::numeric) * COALESCE(sald.sapr_sald, 0::numeric) AS valor_total_venda_vista,
    COALESCE(tabe.tabe_apra, 0::numeric) * COALESCE(sald.sapr_sald, 0::numeric) AS valor_total_venda_prazo
FROM produtos prod
    LEFT JOIN gruposprodutos grup ON prod.prod_grup::text = grup.grup_codi::text
    LEFT JOIN marca marc ON prod.prod_marc = marc.marc_codi
    LEFT JOIN tabelaprecos tabe ON prod.prod_codi::text = tabe.tabe_prod::text
        AND prod.prod_empr = tabe.tabe_empr
    LEFT JOIN saldosprodutos sald ON prod.prod_codi::text = sald.sapr_prod::text;
"""


def atualizar_produtos_view(alias: str):
    """Recria a view produtos_detalhados padronizada no banco informado."""
    with connections[alias].cursor() as cursor:
        cursor.execute(VIEW_PRODUTOS_DETALHADOS_SQL)


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
    help = (
        "Padroniza a view produtos_detalhados (e a coluna prod_codi_fabr) "
        "em todos os tenants ou em um específico."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--slug",
            type=str,
            help="Slug do tenant específico.",
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
            raise CommandError("Use apenas um entre --slug e --tenant.")

        slug_alvo = slug or tenant

        licencas = carregar_licencas_dict()

        if not licencas:
            raise CommandError("Nenhuma licença encontrada.")

        if slug_alvo:
            licencas = [lic for lic in licencas if lic.get("slug") == slug_alvo]

            if not licencas:
                raise CommandError(
                    f"Nenhuma licença encontrada para slug={slug_alvo}"
                )

        atualizados = 0
        falhas = 0

        for lic in licencas:
            alias = f"tenant_{lic['slug']}"

            connections.databases[alias] = montar_db_config(lic)

            self.stdout.write(
                self.style.WARNING(f"[{alias}] Atualizando produtos_detalhados...")
            )

            try:
                with connections[alias].cursor() as cursor:
                    cursor.execute("SELECT 1")

                atualizar_produtos_view(alias)

                atualizados += 1

                self.stdout.write(
                    self.style.SUCCESS(f"[{alias}] View atualizada com sucesso!")
                )

            except (OperationalError, DatabaseError) as e:
                falhas += 1

                self.stdout.write(
                    self.style.ERROR(f"[{alias}] Erro ao atualizar view: {e}")
                )

            finally:
                connections[alias].close()

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Finalizado! Atualizados: {atualizados} | Falhas: {falhas}"
            )
        )
