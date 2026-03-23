from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import OperationalError
from core.licencas_loader import carregar_licencas_dict
from decimal import Decimal
from datetime import date

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

    def add_arguments(self, parser):
        parser.add_argument("--slug", type=str, default="saveweb001")
        parser.add_argument("--teste-baixa", action="store_true")

    def _buscar_produtos_para_teste(self, alias: str):
        with connections[alias].cursor() as cursor:
            cursor.execute(
                """
                SELECT codigo, empresa, filial, saldo, COALESCE(preco_vista, 0) AS preco_vista
                FROM public.produtos_detalhados
                ORDER BY codigo
                LIMIT 3
                """
            )
            rows = cursor.fetchall()
        if len(rows) < 3:
            with connections[alias].cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        prod.prod_codi AS codigo,
                        sald.sapr_empr AS empresa,
                        sald.sapr_fili AS filial,
                        sald.sapr_sald AS saldo,
                        COALESCE(tabe.tabe_avis, 0) AS preco_vista
                    FROM saldosprodutos sald
                    JOIN produtos prod
                      ON prod.prod_codi = sald.sapr_prod
                     AND prod.prod_empr = sald.sapr_empr
                    LEFT JOIN tabelaprecos tabe
                      ON tabe.tabe_prod = sald.sapr_prod
                     AND tabe.tabe_empr = sald.sapr_empr
                     AND tabe.tabe_fili = sald.sapr_fili
                    WHERE COALESCE(sald.sapr_sald, 0) > 0
                    ORDER BY sald.sapr_prod
                    LIMIT 3
                    """
                )
                rows = cursor.fetchall()
        produtos = []
        for r in rows:
            produtos.append(
                {
                    "codigo": str(r[0]),
                    "empresa": int(r[1]) if r[1] is not None else None,
                    "filial": int(r[2]) if r[2] is not None else None,
                    "saldo": Decimal(str(r[3] or 0)),
                    "preco_vista": Decimal(str(r[4] or 0)),
                }
            )
        return produtos

    def _buscar_cliente(self, alias: str, empresa: int):
        with connections[alias].cursor() as cursor:
            cursor.execute(
                """
                SELECT enti_clie
                FROM entidades
                WHERE enti_empr = %s
                  AND enti_situ = '1'
                  AND enti_tipo_enti IN ('CL', 'AM')
                ORDER BY enti_clie
                LIMIT 1
                """,
                [empresa],
            )
            row = cursor.fetchone()
        if row:
            return str(row[0])

        with connections[alias].cursor() as cursor:
            cursor.execute(
                """
                SELECT enti_clie
                FROM entidades
                WHERE enti_empr = %s
                ORDER BY enti_clie
                LIMIT 1
                """,
                [empresa],
            )
            row = cursor.fetchone()
        return str(row[0]) if row else "0"

    def _ler_saldo_produto(self, alias: str, codigo: str, empresa: int, filial: int):
        from Produtos.models import SaldoProduto
        from Produtos.models import Produtos

        saldo = (
            SaldoProduto.objects.using(alias)
            .filter(
                produto_codigo=codigo,
                empresa=str(empresa),
                filial=str(filial),
            )
            .first()
        )
        if not saldo and str(codigo).strip().isdigit():
            prod = Produtos.objects.using(alias).filter(
                prod_empr=str(empresa),
                prod_codi_nume=str(codigo).strip(),
            ).first()
            if prod:
                saldo = (
                    SaldoProduto.objects.using(alias)
                    .filter(
                        produto_codigo=str(prod.prod_codi),
                        empresa=str(empresa),
                        filial=str(filial),
                    )
                    .first()
                )
        return Decimal(str(getattr(saldo, "saldo_estoque", 0) or 0))

    def _executar_teste_baixa_estorno(self, alias: str):
        from Pedidos.services.pedido_service import PedidoVendaService

        produtos = self._buscar_produtos_especificos(alias, codigos=["1", "2", "3"])
        if len(produtos) < 3:
            raise CommandError(f"[{alias}] Não encontrei os 3 produtos (1,2,3) para o teste")

        empresa = produtos[0]["empresa"]
        filial = produtos[0]["filial"]
        if empresa is None or filial is None:
            raise CommandError(f"[{alias}] Não consegui resolver empresa/filial para os produtos (1,2,3)")

        cliente = self._buscar_cliente(alias, empresa)

        saldos_antes = []
        for idx, p in enumerate(produtos, start=1):
            saldo = self._ler_saldo_produto(alias, p["codigo"], empresa, filial)
            saldos_antes.append(saldo)
            self.stdout.write(
                f"[{alias}] Produto {idx}: pedido={p.get('codigo_pedido')} resolvido={p['codigo']} saldo_antes={saldo}"
            )

        itens_data = []
        for p in produtos:
            itens_data.append(
                {
                    "iped_prod": p["codigo"],
                    "iped_quan": Decimal("1.00"),
                    "iped_unit": p["preco_vista"],
                    "iped_desc": Decimal("0.00"),
                }
            )

        pedido_data = {
            "pedi_empr": empresa,
            "pedi_fili": filial,
            "pedi_forn": cliente,
            "pedi_vend": "0",
            "pedi_data": date.today(),
            "pedi_topr": Decimal("0.00"),
            "pedi_tota": Decimal("0.00"),
            "pedi_canc": False,
            "pedi_fina": "0",
            "pedi_stat": "0",
            "pedi_form_rece": "54",
            "pedi_desc": Decimal("0.00"),
            "pedi_liqu": Decimal("0.00"),
            "pedi_tipo_oper": "VENDA",
            "pedi_obse": "TESTE BAIXA/ESTORNO",
        }

        pedido = PedidoVendaService.create_pedido_venda(
            banco=alias,
            pedido_data=pedido_data,
            itens_data=itens_data,
            pedi_tipo_oper="VENDA",
            request=None,
        )

        self.stdout.write(self.style.SUCCESS(f"[{alias}] Pedido criado: {getattr(pedido, 'pedi_nume', None)}"))
        self._imprimir_saidas_pedido(alias, empresa, filial, getattr(pedido, "pedi_nume", None), titulo="SAIDAS_APOS_CRIAR")

        saldos_depois = []
        for idx, p in enumerate(produtos, start=1):
            saldo = self._ler_saldo_produto(alias, p["codigo"], empresa, filial)
            saldos_depois.append(saldo)
            self.stdout.write(
                f"[{alias}] Produto {idx}: pedido={p.get('codigo_pedido')} resolvido={p['codigo']} saldo_depois={saldo}"
            )

        pedido = PedidoVendaService.update_pedido_venda(
            banco=alias,
            pedido=pedido,
            pedido_updates={"pedi_stat": "4", "pedi_canc": True},
            itens_data=itens_data,
            pedi_tipo_oper="VENDA",
            request=None,
        )

        self.stdout.write(self.style.WARNING(f"[{alias}] Pedido atualizado para status 4: {getattr(pedido, 'pedi_nume', None)}"))
        self._imprimir_saidas_pedido(alias, empresa, filial, getattr(pedido, "pedi_nume", None), titulo="SAIDAS_APOS_ESTORNO")

        for idx, p in enumerate(produtos, start=1):
            saldo = self._ler_saldo_produto(alias, p["codigo"], empresa, filial)
            self.stdout.write(
                f"[{alias}] Produto {idx}: pedido={p.get('codigo_pedido')} resolvido={p['codigo']} saldo_estorno={saldo}"
            )
            if saldo != saldos_antes[idx - 1]:
                raise CommandError(
                    f"[{alias}] Estorno incorreto produto={p['codigo']} antes={saldos_antes[idx-1]} depois_estorno={saldo}"
                )

        self.stdout.write(self.style.SUCCESS(f"[{alias}] OK: baixa e estorno voltaram ao saldo original"))

    def _imprimir_saidas_pedido(self, alias: str, empresa: int, filial: int, numero_pedido, titulo: str):
        if not numero_pedido:
            return
        base = f"Saída automática - Pedido {numero_pedido}"
        with connections[alias].cursor() as cursor:
            cursor.execute(
                """
                SELECT said_sequ, said_prod, said_quan, said_data, said_obse
                FROM saidasestoque
                WHERE said_empr = %s
                  AND said_fili = %s
                  AND said_obse LIKE %s
                ORDER BY said_sequ
                """,
                [empresa, filial, f"{base}%"],
            )
            rows = cursor.fetchall()
        self.stdout.write(f"[{alias}] {titulo} total={len(rows)} base={base}")
        for r in rows:
            self.stdout.write(f"[{alias}] {titulo} sequ={r[0]} prod={r[1]} quan={r[2]} data={r[3]} obse={r[4]}")

    def _buscar_produtos_especificos(self, alias: str, codigos: list[str]):
        produtos = []

        with connections[alias].cursor() as cursor:
            cursor.execute(
                """
                SELECT prod_empr
                FROM produtos
                WHERE prod_codi = %s OR prod_codi_nume = %s
                ORDER BY prod_empr
                LIMIT 1
                """,
                [str(codigos[0]).strip(), str(codigos[0]).strip()],
            )
            row = cursor.fetchone()
        if not row:
            return []
        empresa = int(row[0])

        for codigo_pedido in codigos:
            codigo_pedido = str(codigo_pedido).strip()
            if not codigo_pedido:
                continue

            with connections[alias].cursor() as cursor:
                cursor.execute(
                    """
                    SELECT prod_codi
                    FROM produtos
                    WHERE prod_empr = %s
                      AND prod_codi = %s
                    LIMIT 1
                    """,
                    [empresa, codigo_pedido],
                )
                row = cursor.fetchone()
                if row:
                    codigo_resolvido = str(row[0])
                else:
                    cursor.execute(
                        """
                        SELECT prod_codi
                        FROM produtos
                        WHERE prod_empr = %s
                          AND prod_codi_nume = %s
                        ORDER BY prod_codi
                        LIMIT 1
                        """,
                        [empresa, codigo_pedido],
                    )
                    row = cursor.fetchone()
                    if not row:
                        continue
                    codigo_resolvido = str(row[0])

            with connections[alias].cursor() as cursor:
                cursor.execute(
                    """
                    SELECT sapr_fili, sapr_sald
                    FROM saldosprodutos
                    WHERE sapr_empr = %s
                      AND sapr_prod = %s
                    ORDER BY sapr_fili
                    LIMIT 1
                    """,
                    [empresa, codigo_resolvido],
                )
                row = cursor.fetchone()

            filial = int(row[0]) if row and row[0] is not None else 1

            with connections[alias].cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COALESCE(tabe_avis, 0)
                    FROM tabelaprecos
                    WHERE tabe_empr = %s
                      AND tabe_fili = %s
                      AND tabe_prod = %s
                    LIMIT 1
                    """,
                    [empresa, filial, codigo_resolvido],
                )
                row = cursor.fetchone()
            preco = Decimal(str(row[0] or 0)) if row else Decimal("0.00")

            produtos.append(
                {
                    "codigo_pedido": codigo_pedido,
                    "codigo": codigo_resolvido,
                    "empresa": empresa,
                    "filial": filial,
                    "preco_vista": preco,
                }
            )

        return produtos

    def handle(self, *args, **options):
        licencas = carregar_licencas_dict()

        if not licencas:
            raise CommandError("Nenhuma licença encontrada")

        if options.get("teste_baixa"):
            slug = (options.get("slug") or "").strip()
            lic = next((l for l in licencas if str(l.get("slug", "")).strip() == slug), None)
            if not lic:
                raise CommandError(f"Licença não encontrada para slug={slug}")

            alias = f"tenant_{lic['slug']}"
            connections.databases[alias] = montar_db_config(lic)
            try:
                with connections[alias].cursor() as cursor:
                    cursor.execute("SELECT 1")
            except OperationalError:
                raise CommandError(f"[{alias}] Banco de dados não encontrado ou inacessível")

            self.stdout.write(self.style.WARNING(f"[{alias}] Atualizando view produtos_detalhados..."))
            produtosDetalhados(alias)
            self.stdout.write(self.style.SUCCESS(f"[{alias}] View atualizada com sucesso!"))

            self._executar_teste_baixa_estorno(alias)
            return

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
