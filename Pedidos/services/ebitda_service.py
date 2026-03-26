from django.db.models import (
    Sum, F, DecimalField, ExpressionWrapper, OuterRef, Subquery, Value, CharField, DateField,
)
from django.db.models.functions import Coalesce, TruncMonth, Cast
from decimal import Decimal
from Pedidos.models import PedidoVenda, Itenspedidovenda
from Produtos.models import Tabelaprecos


class EbitdaService:

    def __init__(self, inicio, fim, empresa=None, filial=None, banco=None, produto=None):
        self.inicio  = inicio
        self.fim     = fim
        self.empresa = self._to_int(empresa)
        self.filial  = self._to_int(filial)
        self.banco   = banco or "default"
        # FIX: remover caracteres não-numéricos do início do produto
        # evita que o usuário envie ":1376" e quebre filtros ou JSON
        raw = (produto or "").strip()
        # aceita apenas se tiver ao menos um dígito ou letra depois de remover lixo
        self.produto = raw.lstrip(":/ ") or None

    def _to_int(self, value):
        if value is None or value == "":
            return None
        try:
            return int(value)
        except Exception:
            return None

    # FIX: banco não precisa ser passado novamente — usa self.banco
    def calcular(self):
        banco = self.banco

        pedidos = PedidoVenda.objects.using(banco).filter(
            pedi_data__range=[self.inicio, self.fim]
        )
        if self.empresa:
            pedidos = pedidos.filter(pedi_empr=self.empresa)
        if self.filial:
            pedidos = pedidos.filter(pedi_fili=self.filial)

        pedidos_cast = pedidos.annotate(
            pedi_nume_str=Cast("pedi_nume", output_field=CharField())
        )
        pedidos_ids_str = pedidos_cast.values("pedi_nume_str")

        itens = (
            Itenspedidovenda.objects.using(banco)
            .annotate(iped_pedi_str=Cast("iped_pedi", output_field=CharField()))
            .filter(iped_pedi_str__in=Subquery(pedidos_ids_str))
        )
        if self.empresa:
            itens = itens.filter(iped_empr=self.empresa)
        if self.filial:
            itens = itens.filter(iped_fili=self.filial)
        if self.produto:
            itens = itens.filter(iped_prod__icontains=self.produto)

        preco_custo_qs = Tabelaprecos.objects.using(banco).filter(
            tabe_prod=OuterRef("iped_prod")
        )
        if self.empresa:
            preco_custo_qs = preco_custo_qs.filter(tabe_empr=self.empresa)
        if self.filial:
            preco_custo_qs = preco_custo_qs.filter(tabe_fili=self.filial)

        zero = Value(Decimal("0.00"))

        itens = itens.annotate(
            preco_custo=Coalesce(Subquery(preco_custo_qs.values("tabe_cuge")[:1]), zero)
        ).annotate(
            receita_total=ExpressionWrapper(
                Coalesce(F("iped_quan"), zero) * Coalesce(F("iped_unit"), zero),
                output_field=DecimalField(),
            ),
            custo_total=ExpressionWrapper(
                Coalesce(F("iped_quan"), zero) * Coalesce(F("preco_custo"), zero),
                output_field=DecimalField(),
            ),
        ).annotate(
            lucro=ExpressionWrapper(
                Coalesce(F("receita_total"), zero) - Coalesce(F("custo_total"), zero),
                output_field=DecimalField(),
            )
        )

        # ===== RESUMO =====
        resumo   = itens.aggregate(receita=Sum("receita_total"), custo=Sum("custo_total"))
        receita  = resumo.get("receita") or Decimal("0")
        custo    = resumo.get("custo")   or Decimal("0")
        lucro    = receita - custo
        margem   = (lucro / receita * 100) if receita > 0 else Decimal("0")

        # ===== POR ITEM =====
        # FIX: campo correto é iped_prod, não prod_codi
        itens_group = (
            itens.values("iped_prod")
            .annotate(
                receita=Sum("receita_total"),
                custo=Sum("custo_total"),
            )
            .annotate(
                lucro=ExpressionWrapper(
                    Coalesce(F("receita"), zero) - Coalesce(F("custo"), zero),
                    output_field=DecimalField(),
                )
            )
            .order_by("-lucro")
        )

        itens_list = []
        for row in itens_group:
            receita_item = row.get("receita") or 0
            lucro_item   = row.get("lucro")   or 0
            itens_list.append({
                # FIX: usar iped_prod diretamente — prod_codi não existe neste queryset
                "prod_codi": row.get("iped_prod") or "",
                "receita":   float(receita_item),
                "custo":     float(row.get("custo") or 0),
                "lucro":     float(lucro_item),
                "margem":    float(
                    Decimal(str(lucro_item)) / Decimal(str(receita_item)) * 100
                    if receita_item else 0
                ),
            })

        # ===== POR MÊS =====
        # FIX: TruncMonth em Subquery não funciona no Django ORM.
        # Solução: join via pedidos para obter pedi_data diretamente,
        # anotar a data do pedido como DateField e então truncar.
        pedido_data_sq = (
            pedidos_cast
            .filter(pedi_nume_str=OuterRef("iped_pedi_str"))
            .values("pedi_data")[:1]
        )

        mensal_qs = (
            itens
            .annotate(
                pedido_data=Coalesce(
                    Subquery(pedido_data_sq, output_field=DateField()),
                    Value(self.inicio),  # fallback para não perder linhas
                )
            )
            .annotate(mes=TruncMonth("pedido_data"))
            .values("mes")
            .annotate(
                receita=Sum("receita_total"),
                custo=Sum("custo_total"),
            )
            .order_by("mes")
        )

        mensal_list = []
        for row in mensal_qs:
            mes         = row.get("mes")
            receita_mes = row.get("receita") or 0
            custo_mes   = row.get("custo")   or 0
            ebitda_mes  = Decimal(str(receita_mes)) - Decimal(str(custo_mes))
            mensal_list.append({
                "mes":     mes.strftime("%b/%Y") if mes else "—",
                "receita": float(receita_mes),
                "custo":   float(custo_mes),
                "ebitda":  float(ebitda_mes),
                "margem":  float(
                    Decimal(str(ebitda_mes)) / Decimal(str(receita_mes)) * 100
                    if receita_mes else 0
                ),
            })

        return {
            "resumo": {
                "receita": float(receita),
                "custo":   float(custo),
                "ebitda":  float(lucro),
                "margem":  float(round(margem, 2)),
            },
            "itens":   itens_list,
            "mensal":  mensal_list,
        }