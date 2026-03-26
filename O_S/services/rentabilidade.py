from decimal import Decimal
from django.db.models import DecimalField, ExpressionWrapper, F, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from Entidades.models import Entidades
from Produtos.models import Tabelaprecos
from ..models import Os, PecasOs, ServicosOs

class RentabilidadeOsService:
    @staticmethod
    def calcular_os(banco, os_id, empresa=None, filial=None):
        banco = banco or "default"

        os_obj = Os.objects.using(banco).filter(os_os=os_id).first()
        if not os_obj:
            return None

        empresa_id = int(empresa) if empresa is not None else int(os_obj.os_empr)
        filial_id = int(filial) if filial is not None else int(os_obj.os_fili)

        cliente_nome = ""
        try:
            cliente_id_raw = str(getattr(os_obj, "os_clie", "") or "").strip()
            if cliente_id_raw.isdigit():
                cliente = Entidades.objects.using(banco).filter(
                    enti_empr=empresa_id,
                    enti_clie=int(cliente_id_raw),
                ).first()
                cliente_nome = (getattr(cliente, "enti_nome", "") or "") if cliente else ""
        except Exception:
            cliente_nome = ""

        zero = Value(Decimal("0.00"))

        # Pecas
        pecas = PecasOs.objects.using(banco).filter(
            peca_empr=empresa_id,
            peca_fili=filial_id,
            peca_os=os_id,
        )

        custo_peca_cuge_sq = Tabelaprecos.objects.using(banco).filter(
            tabe_empr=empresa_id, tabe_fili=filial_id, tabe_prod=OuterRef("peca_prod")
        ).values("tabe_cuge")[:1]
        
        custo_peca_cust_sq = Tabelaprecos.objects.using(banco).filter(
            tabe_empr=empresa_id, tabe_fili=filial_id, tabe_prod=OuterRef("peca_prod")
        ).values("tabe_cust")[:1]

        custo_peca_unitario = Coalesce(
            Subquery(custo_peca_cuge_sq, output_field=DecimalField()),
            Subquery(custo_peca_cust_sq, output_field=DecimalField()),
            zero,
        )

        qtd_peca = Coalesce(F("peca_quan"), zero)
        unit_peca = Coalesce(F("peca_unit"), zero)
        receita_peca_expr = Coalesce(
            F("peca_tota"),
            ExpressionWrapper(qtd_peca * unit_peca, output_field=DecimalField()),
            zero,
        )

        pecas = pecas.annotate(
            receita_total=ExpressionWrapper(receita_peca_expr, output_field=DecimalField()),
            custo_total=ExpressionWrapper(qtd_peca * Coalesce(custo_peca_unitario, zero), output_field=DecimalField()),
        )

        resumo_pecas = pecas.aggregate(receita=Sum("receita_total"), custo=Sum("custo_total"))

        # Serviços
        servicos = ServicosOs.objects.using(banco).filter(
            serv_empr=empresa_id,
            serv_fili=filial_id,
            serv_os=os_id,
        )

        custo_serv_cuge_sq = Tabelaprecos.objects.using(banco).filter(
            tabe_empr=empresa_id, tabe_fili=filial_id, tabe_prod=OuterRef("serv_prod")
        ).values("tabe_cuge")[:1]

        custo_serv_cust_sq = Tabelaprecos.objects.using(banco).filter(
            tabe_empr=empresa_id, tabe_fili=filial_id, tabe_prod=OuterRef("serv_prod")
        ).values("tabe_cust")[:1]

        custo_serv_unitario = Coalesce(
            Subquery(custo_serv_cuge_sq, output_field=DecimalField()),
            Subquery(custo_serv_cust_sq, output_field=DecimalField()),
            zero,
        )

        qtd_serv = Coalesce(F("serv_quan"), zero)
        unit_serv = Coalesce(F("serv_unit"), zero)
        receita_serv_expr = Coalesce(
            F("serv_tota"),
            ExpressionWrapper(qtd_serv * unit_serv, output_field=DecimalField()),
            zero,
        )

        servicos = servicos.annotate(
            receita_total=ExpressionWrapper(receita_serv_expr, output_field=DecimalField()),
            custo_total=ExpressionWrapper(qtd_serv * Coalesce(custo_serv_unitario, zero), output_field=DecimalField()),
        )

        resumo_servicos = servicos.aggregate(receita=Sum("receita_total"), custo=Sum("custo_total"))

        receita = (resumo_pecas.get("receita") or Decimal("0")) + (resumo_servicos.get("receita") or Decimal("0"))
        custo = (resumo_pecas.get("custo") or Decimal("0")) + (resumo_servicos.get("custo") or Decimal("0"))
        lucro = receita - custo
        margem = (lucro / receita * 100) if receita > 0 else Decimal("0")

        # Agrupar peças
        pecas_group = pecas.values("peca_prod").annotate(
            quantidade=Sum("peca_quan"),
            receita=Sum("receita_total"),
            custo=Sum("custo_total"),
        ).annotate(
            lucro=ExpressionWrapper(
                Coalesce(F("receita"), zero) - Coalesce(F("custo"), zero),
                output_field=DecimalField(),
            )
        ).order_by("-lucro")

        # Agrupar serviços
        servicos_group = servicos.values("serv_prod").annotate(
            quantidade=Sum("serv_quan"),
            receita=Sum("receita_total"),
            custo=Sum("custo_total"),
        ).annotate(
            lucro=ExpressionWrapper(
                Coalesce(F("receita"), zero) - Coalesce(F("custo"), zero),
                output_field=DecimalField(),
            )
        ).order_by("-lucro")

        itens_list = []
        for row in pecas_group:
            receita_item = row.get("receita") or Decimal("0")
            custo_item = row.get("custo") or Decimal("0")
            lucro_item = row.get("lucro") or (receita_item - custo_item)
            margem_item = (lucro_item / receita_item * 100) if receita_item > 0 else Decimal("0")
            itens_list.append({
                "tipo": "Peça",
                "prod_codi": row.get("peca_prod") or "",
                "quantidade": float(row.get("quantidade") or 0),
                "receita": float(receita_item),
                "custo": float(custo_item),
                "lucro": float(lucro_item),
                "margem": float(round(margem_item, 2)),
            })

        for row in servicos_group:
            receita_item = row.get("receita") or Decimal("0")
            custo_item = row.get("custo") or Decimal("0")
            lucro_item = row.get("lucro") or (receita_item - custo_item)
            margem_item = (lucro_item / receita_item * 100) if receita_item > 0 else Decimal("0")
            itens_list.append({
                "tipo": "Serviço",
                "prod_codi": row.get("serv_prod") or "",
                "quantidade": float(row.get("quantidade") or 0),
                "receita": float(receita_item),
                "custo": float(custo_item),
                "lucro": float(lucro_item),
                "margem": float(round(margem_item, 2)),
            })

        return {
            "os": {
                "numero": int(os_obj.os_os),
                "empresa": int(os_obj.os_empr),
                "filial": int(os_obj.os_fili),
                "cliente": str(os_obj.os_clie),
                "cliente_nome": cliente_nome,
                "data": os_obj.os_data_aber.isoformat() if getattr(os_obj, "os_data_aber", None) else None,
            },
            "resumo": {
                "receita": float(receita),
                "custo": float(custo),
                "lucro": float(lucro),
                "margem": float(round(margem, 2)),
            },
            "itens": itens_list,
        }
