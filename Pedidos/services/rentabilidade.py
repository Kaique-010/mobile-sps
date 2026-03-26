from decimal import Decimal

from django.db.models import (
    Case,
    DecimalField,
    ExpressionWrapper,
    F,
    OuterRef,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce

from Entidades.models import Entidades
from Produtos.models import Tabelaprecos
from ..models import Itenspedidovenda, PedidoVenda


class RentabilidadeService:
    @staticmethod
    def calcular_pedido(banco, pedido_id, empresa=None, filial=None, produto=None):
        banco = banco or "default"

        pedido = (
            PedidoVenda.objects.using(banco)
            .filter(pedi_nume=pedido_id)
            .first()
        )
        if not pedido:
            return None

        empresa_id = int(empresa) if empresa is not None else int(pedido.pedi_empr)
        filial_id = int(filial) if filial is not None else int(pedido.pedi_fili)

        cliente_nome = ""
        try:
            cliente_id_raw = str(getattr(pedido, "pedi_forn", "") or "").strip()
            if cliente_id_raw.isdigit():
                cliente = Entidades.objects.using(banco).filter(
                    enti_empr=empresa_id,
                    enti_clie=int(cliente_id_raw),
                ).first()
                cliente_nome = (getattr(cliente, "enti_nome", "") or "") if cliente else ""
        except Exception:
            cliente_nome = ""

        itens = Itenspedidovenda.objects.using(banco).filter(
            iped_empr=empresa_id,
            iped_fili=filial_id,
            iped_pedi=str(pedido.pedi_nume),
        )
        if produto:
            itens = itens.filter(iped_prod__icontains=str(produto).strip())

        zero = Value(Decimal("0.00"))

        custo_cuge_sq = (
            Tabelaprecos.objects.using(banco)
            .filter(
                tabe_empr=empresa_id,
                tabe_fili=filial_id,
                tabe_prod=OuterRef("iped_prod"),
            )
            .values("tabe_cuge")[:1]
        )

        custo_cust_sq = (
            Tabelaprecos.objects.using(banco)
            .filter(
                tabe_empr=empresa_id,
                tabe_fili=filial_id,
                tabe_prod=OuterRef("iped_prod"),
            )
            .values("tabe_cust")[:1]
        )

        preco_custo = Coalesce(
            Subquery(custo_cuge_sq, output_field=DecimalField()),
            Subquery(custo_cust_sq, output_field=DecimalField()),
            zero,
        )

        custo_unitario = Case(
            When(iped_cust__gt=0, then=F("iped_cust")),
            default=preco_custo,
            output_field=DecimalField(),
        )

        qtd = Coalesce(F("iped_quan"), zero)
        unit = Coalesce(F("iped_unli"), F("iped_unit"), zero)
        receita_expr = Coalesce(
            F("iped_tota"),
            ExpressionWrapper(qtd * unit, output_field=DecimalField()),
            zero,
        )

        itens = itens.annotate(
            receita_total=ExpressionWrapper(receita_expr, output_field=DecimalField()),
            custo_total=ExpressionWrapper(qtd * Coalesce(custo_unitario, zero), output_field=DecimalField()),
        ).annotate(
            lucro=ExpressionWrapper(
                Coalesce(F("receita_total"), zero) - Coalesce(F("custo_total"), zero),
                output_field=DecimalField(),
            )
        )

        resumo = itens.aggregate(
            receita=Sum("receita_total"),
            custo=Sum("custo_total"),
        )

        receita = resumo.get("receita") or Decimal("0")
        custo = resumo.get("custo") or Decimal("0")
        lucro = receita - custo
        margem = (lucro / receita * 100) if receita > 0 else Decimal("0")

        itens_group = (
            itens.values("iped_prod")
            .annotate(
                quantidade=Sum("iped_quan"),
                receita=Sum("receita_total"),
                custo=Sum("custo_total"),
                lucro=Sum("lucro"),
            )
            .order_by("-lucro")
        )

        itens_list = []
        for row in itens_group:
            receita_item = row.get("receita") or Decimal("0")
            custo_item = row.get("custo") or Decimal("0")
            lucro_item = row.get("lucro")
            if lucro_item is None:
                lucro_item = receita_item - custo_item
            margem_item = (lucro_item / receita_item * 100) if receita_item > 0 else Decimal("0")
            itens_list.append(
                {
                    "prod_codi": row.get("iped_prod") or "",
                    "quantidade": float(row.get("quantidade") or 0),
                    "receita": float(receita_item),
                    "custo": float(custo_item),
                    "lucro": float(lucro_item),
                    "margem": float(round(margem_item, 2)),
                }
            )

        return {
            "pedido": {
                "numero": int(pedido.pedi_nume),
                "empresa": int(pedido.pedi_empr),
                "filial": int(pedido.pedi_fili),
                "cliente": str(pedido.pedi_forn),
                "cliente_nome": cliente_nome,
                "data": pedido.pedi_data.isoformat() if getattr(pedido, "pedi_data", None) else None,
            },
            "resumo": {
                "receita": float(receita),
                "custo": float(custo),
                "lucro": float(lucro),
                "margem": float(round(margem, 2)),
            },
            "itens": itens_list,
        }
