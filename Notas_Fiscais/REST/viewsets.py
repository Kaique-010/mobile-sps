# notas_fiscais/api/viewsets.py

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter

from ..models import Nota, NotaEvento
from .serializers import (
    NotaDetailSerializer,
    NotaCreateUpdateSerializer,
)
from ..services.evento_service import EventoService
from core.utils import get_licenca_db_config 
from ..services.nota_service import NotaService


class NotaViewSet(viewsets.ModelViewSet):
    """
    API de Notas Fiscais (saída).
    GET    /api/notas/           -> lista
    POST   /api/notas/           -> cria
    GET    /api/notas/{id}/      -> detalhe
    PUT    /api/notas/{id}/      -> atualiza completa
    PATCH  /api/notas/{id}/      -> atualiza parcial
    POST   /api/notas/{id}/cancelar/ -> cancela nota
    """

    queryset = Nota.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["modelo", "serie", "numero", "status", "tipo_operacao", "finalidade"]
    search_fields = ["chave_acesso", "destinatario__enti_nome", "destinatario__enti_cnpj", "destinatario__enti_cpf"]
    ordering_fields = ["data_emissao", "numero", "status"]
    ordering = ["-data_emissao", "-numero"]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return NotaCreateUpdateSerializer
        return NotaDetailSerializer

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or "default"
        empresa = self.request.query_params.get("empresa") or self.request.session.get("empresa_id")
        filial = self.request.query_params.get("filial") or self.request.session.get("filial_id")

        qs = (
            Nota.objects.using(banco)
            .select_related("emitente", "destinatario")
            .prefetch_related("itens__impostos", "eventos")
        )

        if empresa:
            qs = qs.filter(empresa=empresa)
        if filial:
            qs = qs.filter(filial=filial)

        return qs

    # --------- CREATE ---------
    def create(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request) or "default"
        empresa = request.session.get("empresa_id")
        filial = request.session.get("filial_id")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        itens = data.pop("itens")
        impostos = data.pop("impostos", [])
        transporte = data.pop("transporte", None)

        impostos_map = {idx: imp for idx, imp in enumerate(impostos)} if impostos else None

        nota = NotaService.criar(
            data=data,
            itens=itens,
            impostos_map=impostos_map,
            transporte=transporte,
            empresa=empresa,
            filial=filial,
            database=banco,
        )

        out = NotaDetailSerializer(nota)
        return Response(out.data, status=status.HTTP_201_CREATED)

    # --------- UPDATE ---------
    def update(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request) or "default"
        partial = kwargs.pop("partial", False)

        nota = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        itens = data.pop("itens")
        impostos = data.pop("impostos", [])
        transporte = data.pop("transporte", None)

        impostos_map = {idx: imp for idx, imp in enumerate(impostos)} if impostos else None

        nota = NotaService.atualizar(
            nota=nota,
            data=data,
            itens=itens,
            impostos_map=impostos_map,
            transporte=transporte,
            database=banco,
        )

        out = NotaDetailSerializer(nota)
        return Response(out.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    # --------- CANCELAR ---------
    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        banco = get_licenca_db_config(request) or "default"
        nota = self.get_queryset().using(banco).get(pk=pk)

        descricao = request.data.get("descricao", "Cancelamento solicitado via API")
        xml = request.data.get("xml")
        protocolo = request.data.get("protocolo")

        NotaService.cancelar(
            nota=nota,
            descricao=descricao,
            xml=xml,
            protocolo=protocolo,
        )

        out = NotaDetailSerializer(nota)
        return Response(out.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def transmitir(self, request, pk=None):
        banco = get_licenca_db_config(request) or "default"
        nota = self.get_queryset().using(banco).get(pk=pk)

        if nota.status == 100:
            return Response({"detail": "Nota já autorizada"}, status=status.HTTP_400_BAD_REQUEST)

        chave = request.data.get("chave_acesso")
        protocolo = request.data.get("protocolo")
        xml = request.data.get("xml")
        descricao = request.data.get("descricao") or "Transmitida via painel"

        NotaService.transmitir(
            nota=nota,
            descricao=descricao,
            chave=chave,
            protocolo=protocolo,
            xml=xml,
        )

        out = NotaDetailSerializer(nota)
        return Response(out.data, status=status.HTTP_200_OK)


class NotaEventoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lista eventos de notas fiscais (cancelamento, CC-e, etc).
    """

    queryset = NotaEvento.objects.all()
    serializer_class = None  # simples: podemos reutilizar um serializer direto

    def list(self, request, *args, **kwargs):
        nota_id = request.query_params.get("nota")
        qs = NotaEvento.objects.all()
        if nota_id:
            qs = qs.filter(nota_id=nota_id)

        data = [
            {
                "id": e.id,
                "nota_id": e.nota_id,
                "tipo": e.tipo,
                "descricao": e.descricao,
                "protocolo": e.protocolo,
                "criado_em": e.criado_em,
            }
            for e in qs.order_by("-criado_em")
        ]
        return Response(data)
