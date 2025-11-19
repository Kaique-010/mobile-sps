from rest_framework import viewsets
from rest_framework.response import Response
from django.db.models import Q
from core.utils import get_licenca_db_config
from ..models import Cfop


class CfopBuscaViewSet(viewsets.ViewSet):
    def list(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request) or "default"
        empresa = request.session.get("empresa_id")
        q = request.query_params.get("q", "").strip()

        qs = Cfop.objects.using(banco).filter(cfop_empr=empresa)
        if q:
            qs = qs.filter(
                Q(cfop_cfop__icontains=q) | Q(cfop_desc__iregex=q)
            )

        qs = qs.only(
            "cfop_cfop", "cfop_desc", "cfop_trib_cst_icms", "cfop_trib_cst_pis", "cfop_trib_cst_cofins",
            "cfop_trib_aliq_ipi", "cfop_trib_perc_pis", "cfop_trib_perc_cofins"
        ).order_by("cfop_cfop")[:20]

        data = [
            {
                "value": str(x.cfop_cfop),
                "label": f"{x.cfop_cfop} • {x.cfop_desc}",
                "cst_icms": getattr(x, "cfop_trib_cst_icms", None),
                "cst_pis": getattr(x, "cfop_trib_cst_pis", None),
                "cst_cofins": getattr(x, "cfop_trib_cst_cofins", None),
                "ipi_aliquota": getattr(x, "cfop_trib_aliq_ipi", None),
                "pis_aliquota": getattr(x, "cfop_trib_perc_pis", None),
                "cofins_aliquota": getattr(x, "cfop_trib_perc_cofins", None),
            }
            for x in qs
        ]
        return Response(data)