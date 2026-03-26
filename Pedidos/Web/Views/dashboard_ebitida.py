from django.views.generic import TemplateView
from django.utils.dateparse import parse_date
from datetime import date
import json

from core.utils import get_licenca_db_config
from Pedidos.services.ebitda_service import EbitdaService


class DashboardEbitdaView(TemplateView):
    template_name = "Pedidos/pedidos_dashboard_ebitda.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        banco = get_licenca_db_config(self.request) or "default"

        hoje       = date.today()
        inicio_raw = self.request.GET.get("inicio")
        fim_raw    = self.request.GET.get("fim")
        inicio     = parse_date(inicio_raw) if inicio_raw else None
        fim        = parse_date(fim_raw)    if fim_raw    else None
        inicio     = inicio or hoje.replace(day=1)
        fim        = fim    or hoje

        empresa = (
            self.request.GET.get("empresa")
            or self.request.session.get("empresa_id")
            or self.request.headers.get("X-Empresa")
        )
        filial = (
            self.request.GET.get("filial")
            or self.request.session.get("filial_id")
            or self.request.headers.get("X-Filial")
        )
        produto = self.request.GET.get("produto") or ""

        service = EbitdaService(inicio, fim, empresa, filial, banco, produto=produto)

        # FIX: calcular() não recebe mais banco — já está em self.banco
        data = service.calcular()

        context.update(data)
        # FIX: json_script já serializa — não passar json.dumps() aqui.
        # Passar json.dumps() fazia json_script serializar novamente,
        # resultando em JSON dentro de JSON: o parse retornava string, não array.
        context["mensal_json"] = context.get("mensal") or []
        context["itens_json"]  = context.get("itens")  or []
        context["filtros"] = {
            "inicio":  inicio,
            "fim":     fim,
            "produto": service.produto or "",
        }
        return context