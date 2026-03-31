# financeiro/api/views/orcamento_views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.utils import get_licenca_db_config
from Financeiro.Rest.serializers import (
    OrcamentoResumoFiltroSerializer,
    OrcamentoSalvarSerializer,
)
from Financeiro.services import OrcamentoService


class OrcamentoViewSet(viewsets.ViewSet):
    def _service(self, request):
        db_alias = get_licenca_db_config(request)
        empresa_id = request.session.get("empresa_id") or request.headers.get("X-Empresa")
        filial_id = request.session.get("filial_id") or request.headers.get("X-Filial")

        if not empresa_id:
            raise ValueError("Empresa não informada.")

        return OrcamentoService(
            db_alias=db_alias,
            empresa_id=int(empresa_id),
            filial_id=int(filial_id) if filial_id else None,
        )

    @action(detail=False, methods=["get"], url_path="resumo")
    def resumo(self, request):
        serializer = OrcamentoResumoFiltroSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        service = self._service(request)
        data = service.resumo_raiz(
            orcamento_id=serializer.validated_data["orcamento_id"],
            ano=serializer.validated_data["ano"],
            mes=serializer.validated_data["mes"],
        )
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="salvar-previsto")
    def salvar_previsto(self, request):
        serializer = OrcamentoSalvarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = self._service(request)
        item = service.salvar_previsto(
            orcamento_id=serializer.validated_data["orcamento_id"],
            centro_custo_id=serializer.validated_data["centro_custo_id"],
            ano=serializer.validated_data["ano"],
            mes=serializer.validated_data["mes"],
            valor=serializer.validated_data["valor"],
        )

        return Response(
            {
                "id": item.orci_id,
                "mensagem": "Previsto salvo com sucesso.",
            },
            status=status.HTTP_200_OK,
        )