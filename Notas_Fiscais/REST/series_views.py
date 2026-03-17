from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.utils import get_licenca_db_config
from series.models import Series


def _to_int(v, default=None):
    try:
        return int(v)
    except Exception:
        return default


def _fmt_serie(v):
    s = str(v or "").strip()
    if s.isdigit() and len(s) < 3:
        return s.zfill(3)
    return s


class SeriesSaNotaView(APIView):
    def get(self, request, slug=None):
        banco = get_licenca_db_config(request) or "default"
        empresa = (
            request.query_params.get("empresa")
            or request.session.get("empresa_id")
            or request.headers.get("X-Empresa")
        )
        filial = (
            request.query_params.get("filial")
            or request.session.get("filial_id")
            or request.headers.get("X-Filial")
        )

        empresa_id = _to_int(empresa, None)
        filial_id = _to_int(filial, None)
        if not empresa_id or not filial_id:
            return Response(
                {"detail": "Informe empresa e filial."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = (
            Series.objects.using(banco)
            .filter(seri_empr=empresa_id, seri_fili=filial_id, seri_nome="SA")
            .order_by("seri_codi")
            .values_list("seri_codi", flat=True)
        )
        codigos = [_fmt_serie(c) for c in list(qs)]
        opcoes = [{"value": c, "label": c} for c in codigos if c]
        default = opcoes[0]["value"] if opcoes else None

        return Response(
            {"default": default, "options": opcoes},
            status=status.HTTP_200_OK,
        )
