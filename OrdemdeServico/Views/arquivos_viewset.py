from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .base import BaseMultiDBModelViewSet
from ..models import Osarquivos
from ..serializers.imagens import OsArquSerializer
from ..services.os_arquivo_service import OsArquivoService

import base64


class OsArquViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = "OrdemdeServico"
    queryset = Osarquivos.objects.all()
    serializer_class = OsArquSerializer
    permission_classes = [IsAuthenticated]

    def _get_empresa_filial(self, request):
        empresa = request.headers.get("X-Empresa") or request.query_params.get("empresa") or request.query_params.get("empr") or request.data.get("empresa")
        filial = request.headers.get("X-Filial") or request.query_params.get("filial") or request.query_params.get("fili") or request.data.get("filial")
        return empresa, filial

    @action(detail=True, methods=["get"])
    def arquivo(self, request, pk=None):
        obj = self.get_object()
        data = self.get_serializer(obj).data
        prev = OsArquivoService.preview(obj)
        if isinstance(prev, bytes):
            prev = base64.b64encode(prev).decode("utf-8")
        data["preview"] = prev
        return Response(data)

    @action(detail=False, methods=["get"])
    def por_os(self, request):
        banco = self.get_banco()
        os_nume = request.query_params.get("os") or request.query_params.get("numero_os")
        if not os_nume:
            return Response({"erro": "parâmetro os/numero_os obrigatório"}, status=400)

        empresa, filial = self._get_empresa_filial(request)
        if not (empresa and filial):
            return Response({"erro": "empresa e filial obrigatórias"}, status=400)

        qs = (
            Osarquivos.objects.using(banco)
            .filter(os_empr=empresa, os_fili=filial, os_nume=os_nume)
            .order_by("-os_data")
        )

        data = []
        for obj in qs:
            item = self.get_serializer(obj).data
            prev = OsArquivoService.preview(obj)
            if isinstance(prev, bytes):
                prev = base64.b64encode(prev).decode("utf-8")
            item["preview"] = prev
            data.append(item)

        return Response(data)

    @action(detail=False, methods=["post"])
    def upload(self, request):
        banco = self.get_banco()
        os_nume = request.data.get("numero_os") or request.data.get("os_nume")
        arquivos = request.data.get("arquivos")

        user = getattr(request.user, "pk", None) or request.data.get("usuario") or 0
        empresa, filial = self._get_empresa_filial(request)

        if not os_nume:
            return Response({"erro": "numero_os obrigatório"}, status=400)
        if not (empresa and filial):
            return Response({"erro": "empresa e filial obrigatórias"}, status=400)

        if isinstance(arquivos, str):
            OsArquivoService.salvar_um(os_nume, arquivos, user, empresa, filial, banco=banco)
            return Response({"msg": "1 arquivo enviado"})

        if isinstance(arquivos, list):
            objs = OsArquivoService.salvar_multiplos(os_nume, arquivos, user, empresa, filial, banco=banco)
            return Response({"msg": f"{len(objs)} arquivos enviados"})

        return Response({"erro": "formato inválido"}, status=status.HTTP_400_BAD_REQUEST)
