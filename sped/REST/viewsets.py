from django.http import HttpResponse

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.utils import get_licenca_db_config
from sped.REST.serializers import GerarSpedSerializer
from sped.Services.gerador import GeradorSpedService


def _to_int(v):
    try:
        return int(v)
    except Exception:
        return None


class SpedViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _resolve_empresa_filial(self, request, validated):
        empresa = (
            validated.get("empresa_id")
            or _to_int(request.headers.get("X-Empresa"))
            or _to_int(request.headers.get("Empresa_id"))
            or request.session.get("empresa_id")
            or _to_int(getattr(request.user, "usua_empr", None))
        )

        filial = (
            validated.get("filial_id")
            or _to_int(request.headers.get("X-Filial"))
            or _to_int(request.headers.get("Filial_id"))
            or request.session.get("filial_id")
            or _to_int(getattr(request.user, "usua_fili", None))
        )
        return empresa, filial

    def gerar(self, request):
        serializer = GerarSpedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        db_alias = get_licenca_db_config(request)
        if not db_alias:
            return Response({"detail": "Banco de dados não encontrado."}, status=status.HTTP_400_BAD_REQUEST)

        empresa, filial = self._resolve_empresa_filial(request, serializer.validated_data)
        if not empresa or not filial:
            return Response({"detail": "Empresa e filial são obrigatórias."}, status=status.HTTP_400_BAD_REQUEST)

        texto = GeradorSpedService(
            db_alias=db_alias,
            empresa_id=empresa,
            filial_id=filial,
            data_inicio=serializer.validated_data["data_inicio"],
            data_fim=serializer.validated_data["data_fim"],
            cod_receita=serializer.validated_data.get("cod_receita"),
            data_vencimento=serializer.validated_data.get("data_vencimento"),
        ).gerar()

        nome = "SPED_{empresa}_{filial}_{ini}_{fim}.txt".format(
            empresa=empresa,
            filial=filial,
            ini=serializer.validated_data["data_inicio"].strftime("%Y%m%d"),
            fim=serializer.validated_data["data_fim"].strftime("%Y%m%d"),
        )
        resp = HttpResponse(texto, content_type="text/plain; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="{0}"'.format(nome)
        return resp

    def preview(self, request):
        serializer = GerarSpedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        db_alias = get_licenca_db_config(request)
        if not db_alias:
            return Response({"detail": "Banco de dados não encontrado."}, status=status.HTTP_400_BAD_REQUEST)

        empresa, filial = self._resolve_empresa_filial(request, serializer.validated_data)
        if not empresa or not filial:
            return Response({"detail": "Empresa e filial são obrigatórias."}, status=status.HTTP_400_BAD_REQUEST)

        texto = GeradorSpedService(
            db_alias=db_alias,
            empresa_id=empresa,
            filial_id=filial,
            data_inicio=serializer.validated_data["data_inicio"],
            data_fim=serializer.validated_data["data_fim"],
            cod_receita=serializer.validated_data.get("cod_receita"),
            data_vencimento=serializer.validated_data.get("data_vencimento"),
        ).gerar()

        return Response({"texto": texto})
