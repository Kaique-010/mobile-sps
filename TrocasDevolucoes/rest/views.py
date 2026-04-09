from rest_framework import status, viewsets
from rest_framework.response import Response

from core.utils import get_licenca_db_config
from TrocasDevolucoes.rest.serializers import TrocaDevolucaoSerializer
from TrocasDevolucoes.services.troca_devolucao_service import TrocaDevolucaoService


class TrocaDevolucaoViewSet(viewsets.ModelViewSet):
    serializer_class = TrocaDevolucaoSerializer
    lookup_field = 'tdvl_nume'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        filtros = {
            'tdvl_empr': self.request.query_params.get('tdvl_empr'),
            'tdvl_fili': self.request.query_params.get('tdvl_fili'),
            'tdvl_pdor': self.request.query_params.get('tdvl_pdor'),
            'tdvl_stat': self.request.query_params.get('tdvl_stat'),
        }
        return TrocaDevolucaoService.listar(banco, filtros=filtros)

    def create(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        itens = serializer.validated_data.pop('itens', [])
        troca = TrocaDevolucaoService.criar_com_itens(banco, serializer.validated_data, itens)
        out = self.get_serializer(troca)
        return Response(out.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        dados = {k: v for k, v in serializer.validated_data.items() if k != 'itens'}
        instance = TrocaDevolucaoService.atualizar(banco, instance, dados)
        return Response(self.get_serializer(instance).data)
