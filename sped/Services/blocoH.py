from decimal import Decimal

from django.db.models import Sum

from sped.models import EntradaEstoque, ProdutosDetalhados, SaldoProduto


def _fmt_data(d):
    if not d:
        return ""
    return d.strftime("%d%m%Y")


def _fmt_decimal(v, casas=2):
    if v is None:
        return ""
    try:
        q = Decimal(v).quantize(Decimal("1." + ("0" * int(casas))))
    except Exception:
        q = Decimal("0").quantize(Decimal("1." + ("0" * int(casas))))
    s = format(q, "f")
    return s.replace(".", ",")


class BlocoHService:
    def __init__(self, *, db_alias, empresa_id, filial_id, data_inicio, data_fim):
        self.db_alias = db_alias
        self.empresa_id = int(empresa_id)
        self.filial_id = int(filial_id)
        self.data_inicio = data_inicio
        self.data_fim = data_fim

    def gerar(self):
        linhas = []

        saldos = list(
            SaldoProduto.objects.using(self.db_alias)
            .filter(empresa=str(self.empresa_id), filial=str(self.filial_id), saldo_estoque__gt=0)
            .select_related("produto_codigo")
            .order_by("produto_codigo_id")
        )

        if not saldos:
            linhas.append("|H001|1|")
            linhas.append("|H990|2|")
            return linhas

        codigos = [s.produto_codigo_id for s in saldos]

        custo_map = {}
        for p in (
            ProdutosDetalhados.objects.using(self.db_alias)
            .filter(empresa=str(self.empresa_id), filial=str(self.filial_id), codigo__in=codigos)
            .only("codigo", "custo")
            .iterator()
        ):
            if p.custo is not None:
                custo_map[p.codigo] = Decimal(p.custo)

        faltantes = [c for c in codigos if c not in custo_map]
        if faltantes:
            agg = (
                EntradaEstoque.objects.using(self.db_alias)
                .filter(entr_empr=self.empresa_id, entr_fili=self.filial_id, entr_data__lte=self.data_fim, entr_prod__in=faltantes)
                .values("entr_prod")
                .annotate(q=Sum("entr_quan"), v=Sum("entr_tota"))
            )
            for a in agg:
                q = a.get("q") or Decimal("0")
                v = a.get("v") or Decimal("0")
                if q and Decimal(q) != Decimal("0"):
                    custo_map[a["entr_prod"]] = (Decimal(v) / Decimal(q))

        linhas.append("|H001|0|")

        itens = []
        total_inv = Decimal("0")
        for s in saldos:
            cod_item = s.produto_codigo_id
            prod = s.produto_codigo

            qtd = Decimal(s.saldo_estoque or 0)
            if qtd <= 0:
                continue

            custo = custo_map.get(cod_item)
            if custo is None:
                custo = Decimal("0")

            vl_item = (qtd * custo).quantize(Decimal("1.00"))
            total_inv += vl_item

            itens.append(
                "|H010|{cod_item}|{unid}|{qtd}|{vl_unit}|{vl_item}|0||||".format(
                    cod_item=(cod_item or "").strip(),
                    unid=(getattr(prod, "prod_unme_id", "") or "").strip(),
                    qtd=_fmt_decimal(qtd, 2),
                    vl_unit=_fmt_decimal(custo, 6),
                    vl_item=_fmt_decimal(vl_item, 2),
                )
            )

        linhas.append(
            "|H005|{dt_inv}|{vl_inv}|01|".format(
                dt_inv=_fmt_data(self.data_fim),
                vl_inv=_fmt_decimal(total_inv, 2),
            )
        )
        linhas.extend(itens)

        linhas.append("|H990|{qtd}|".format(qtd=len(linhas) + 1))
        return linhas
