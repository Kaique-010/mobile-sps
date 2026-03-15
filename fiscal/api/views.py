from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import get_licenca_db_config
from fiscal.api.serializers import (
    GerarDevolucaoSerializer,
    ImportarXMLSerializer,
    NFeDocumentoSerializer,
)
from fiscal.models import NFeDocumento
from fiscal.services.gerar_devolucao_service import GerarDevolucaoService
from fiscal.services.importar_xml_service import ImportarXMLService


class ImportarXMLView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ImportarXMLSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        banco = get_licenca_db_config(request) or "default"
        service = ImportarXMLService(banco=banco)

        try:
            empresa = serializer.validated_data["empresa"]
            filial = serializer.validated_data["filial"]
            xml = (serializer.validated_data.get("xml") or "").strip()
            chave = (serializer.validated_data.get("chave") or "").strip()

            if xml:
                doc = service.importar(empresa=empresa, filial=filial, xml=xml)
            else:
                doc = service.importar_por_chave(empresa=empresa, filial=filial, chave=chave)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "id": doc.id,
                "empresa": doc.empresa,
                "filial": doc.filial,
                "chave": doc.chave,
                "tipo": doc.tipo,
            },
            status=status.HTTP_201_CREATED,
        )


class DocumentosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request) or "default"

        qs = NFeDocumento.objects.using(banco).all().order_by("-criado_em")
        empresa = request.query_params.get("empresa")
        filial = request.query_params.get("filial")
        if empresa is not None:
            qs = qs.filter(empresa=int(empresa))
        if filial is not None:
            qs = qs.filter(filial=int(filial))

        data = NFeDocumentoSerializer(qs[:200], many=True).data
        return Response(data)


class GerarDevolucaoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = GerarDevolucaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        banco = get_licenca_db_config(request) or "default"
        service = GerarDevolucaoService(banco=banco)

        try:
            nota = service.gerar(
                documento_id=serializer.validated_data["documento_id"],
                empresa=serializer.validated_data["empresa"],
                filial=serializer.validated_data["filial"],
                emitir=serializer.validated_data.get("emitir") or False,
            )
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "nota_id": nota.id,
                "empresa": nota.empresa,
                "filial": nota.filial,
                "finalidade": nota.finalidade,
                "tipo_operacao": nota.tipo_operacao,
            },
            status=status.HTTP_201_CREATED,
        )

