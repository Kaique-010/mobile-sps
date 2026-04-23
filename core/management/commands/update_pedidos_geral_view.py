from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import OperationalError
from core.licencas_loader import carregar_licencas_dict

def campoIntervaloHoras(alias: str):
    with connections[alias].cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'itenspedidovenda'
            ORDER BY ordinal_position
            """
        )
        colunas_itens = {row[0] for row in cursor.fetchall()}

        col_empr = "iped_empr" if "iped_empr" in colunas_itens else "item_empr"
        col_fili = "iped_fili" if "iped_fili" in colunas_itens else "item_fili"
        col_pedi = "iped_pedi" if "iped_pedi" in colunas_itens else "item_pedi"
        col_prod = "iped_prod" if "iped_prod" in colunas_itens else "item_prod"
        col_quan = "iped_quan" if "iped_quan" in colunas_itens else "item_quan"
        col_item = "iped_item" if "iped_item" in colunas_itens else "item_item"

        cursor.execute(
            f"""
        
DROP VIEW IF EXISTS Pedidos_geral;

CREATE OR REPLACE VIEW Pedidos_geral as(
WITH itens_agrupados AS (
SELECT
i.{col_empr} AS item_empr,
i.{col_fili} AS item_fili,
i.{col_pedi} AS item_pedi,
SUM(i.{col_quan}) AS quantidade,
STRING_AGG(p.prod_nome, ', ' ORDER BY i.{col_item}) AS produtos
FROM itenspedidovenda i
LEFT JOIN produtos p
ON i.{col_prod} = p.prod_codi
AND i.{col_empr} = p.prod_empr
GROUP BY i.{col_empr}, i.{col_fili}, i.{col_pedi}
)

SELECT
p.pedi_empr AS Empresa,
p.pedi_fili AS Filial,
p.pedi_nume AS Numero_Pedido,
c.enti_clie AS Codigo_Cliente,
c.enti_nome AS Nome_Cliente,
p.pedi_data AS Data_Pedido,
CASE
WHEN CAST(p.pedi_stat AS INTEGER) = 0 THEN 'Pendente'
WHEN CAST(p.pedi_stat AS INTEGER) = 1 THEN 'Processando'
WHEN CAST(p.pedi_stat AS INTEGER) = 2 THEN 'Enviado'
WHEN CAST(p.pedi_stat AS INTEGER) = 3 THEN 'Concluído'
WHEN CAST(p.pedi_stat AS INTEGER) = 4 THEN 'Cancelado'
ELSE 'Outro'
END AS Status,
COALESCE(i.quantidade, 0) AS Quantidade_Total,
COALESCE(i.produtos, 'Sem itens') AS Itens_do_Pedido,
p.pedi_tota AS Valor_Total,
CASE
WHEN CAST(p.pedi_fina AS INTEGER) = 0 THEN 'À VISTA'
WHEN CAST(p.pedi_fina AS INTEGER) = 1 THEN 'A PRAZO'
WHEN CAST(p.pedi_fina AS INTEGER) = 2 THEN 'SEM FINANCEIRO'
ELSE 'OUTRO'
END AS Tipo_Financeiro,
v.enti_nome AS Nome_Vendedor
FROM pedidosvenda p
LEFT JOIN entidades c
ON p.pedi_forn = c.enti_clie AND p.pedi_empr = c.enti_empr
LEFT JOIN entidades v
ON p.pedi_vend = v.enti_clie AND p.pedi_empr = v.enti_empr
LEFT JOIN itens_agrupados i
ON p.pedi_nume = i.item_pedi AND p.pedi_empr = i.item_empr AND p.pedi_fili = i.item_fili
ORDER BY p.pedi_data DESC, p.pedi_nume DESC)

 
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
    help = "Atualiza apenas o campo status em todos os bancos de licenças"

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

            self.stdout.write(self.style.WARNING(f"[{alias}] Atualizando campo status..."))

            try:
                campoIntervaloHoras(alias)
                self.stdout.write(self.style.SUCCESS(f"[{alias}] Campo atualizado com sucesso!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro ao atualizar campo: {e}"))
