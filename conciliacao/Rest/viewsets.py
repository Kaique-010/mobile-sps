
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError
from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from Licencas.authentication import CustomJWTAuthentication
from conciliacao.contexto import obter_contexto
from conciliacao.models import ConciliacaoBancaria, ItemExtrato
from conciliacao.services.importador_ofx import ImportarOFXService

from .serializers import (
    ConciliacaoFiltroSerializer,
    ConciliacaoSerializer,
    ImportarOFXSerializer,
    ItemExtratoSerializer,
)


class ConciliacaoPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = None


class ConciliacaoViewSet(viewsets.GenericViewSet):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]
    pagination_class = ConciliacaoPagination
    serializer_class = ConciliacaoSerializer
    filter_backends = []
    http_method_names = ["get", "post", "head", "options"]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        self.ctx = obter_contexto(
            request,
            kwargs.get("slug"),
            acao="add" if self.action == "importar_ofx" else "view",
        )

    def handle_exception(self, exc):
        if isinstance(exc, DjangoValidationError):
            return Response(
                {"detail": exc.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if isinstance(exc, DatabaseError):
            return Response(
                {
                    "detail": (
                        "Não foi possível concluir a operação "
                        "de conciliação."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return super().handle_exception(exc)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["ctx"] = self.ctx
        return context

    def get_serializer_class(self):
        if self.action == "importar_ofx":
            return ImportarOFXSerializer

        if self.action == "itens":
            return ItemExtratoSerializer

        return ConciliacaoSerializer

    def get_queryset(self):
        """
        Queryset base sempre limitado à empresa e filial autenticadas.
        Não aplica filtros da query string.
        """
        return ConciliacaoBancaria.objects.using(
            self.ctx.db_alias
        ).filter(
            empresa=self.ctx.empresa,
            filial=self.ctx.filial,
        )

    def get_list_queryset(self):
        """
        Aplica filtros somente à listagem.
        """
        filtros = ConciliacaoFiltroSerializer(
            data=self.request.query_params,
            context=self.get_serializer_context(),
        )
        filtros.is_valid(raise_exception=True)

        dados = dict(filtros.validated_data)

        # O escopo é sempre definido pelo contexto autenticado.
        dados.pop("empresa", None)
        dados.pop("filial", None)

        if "numero" in dados:
            dados["nume"] = dados.pop("numero")

        return self.get_queryset().filter(
            **dados
        ).only(
            "nume",
            "empresa",
            "filial",
            "codigo_banco",
            "data",
        ).order_by("-nume")

    def get_object(self):
        """
        Busca pela chave composta:
        empresa + filial + número da conciliação.
        """
        empresa = self.kwargs["empresa"]
        filial = self.kwargs["filial"]
        numero = self.kwargs["numero"]

        if (
            empresa != self.ctx.empresa
            or filial != self.ctx.filial
        ):
            raise NotFound("Conciliação não encontrada.")

        obj = get_object_or_404(
            self.get_queryset().filter(
                nume=numero,
            )
        )

        self.check_object_permissions(
            self.request,
            obj,
        )

        return obj

    def list(self, request, *args, **kwargs):
        queryset = self.get_list_queryset()

        page = self.paginate_queryset(queryset)

        serializer = self.get_serializer(
            page,
            many=True,
        )

        return self.get_paginated_response(
            serializer.data
        )

    def retrieve(self, request, *args, **kwargs):
        conciliacao = self.get_object()

        serializer = self.get_serializer(
            conciliacao
        )

        return Response(serializer.data)

    def itens(self, request, *args, **kwargs):
        conciliacao = self.get_object()

        queryset = ItemExtrato.objects.using(
            self.ctx.db_alias
        ).filter(
            empresa=self.ctx.empresa,
            filial=self.ctx.filial,
            nume=conciliacao.nume,
        ).order_by(
            "linha",
            "id",
        )

        page = self.paginate_queryset(queryset)

        serializer = self.get_serializer(
            page,
            many=True,
        )

        return self.get_paginated_response(
            serializer.data
        )

    def importar_ofx(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        resultado = ImportarOFXService(
            empresa=self.ctx.empresa,
            filial=self.ctx.filial,
            codigo_banco=serializer.validated_data[
                "codigo_banco"
            ],
            db_alias=self.ctx.db_alias,
        ).importar_upload(
            serializer.validated_data["arquivo"]
        )

        return Response(
            {
                "conc_nume": resultado[
                    "numero_conciliacao"
                ],
                "conc_empr": resultado["empresa"],
                "conc_fili": resultado["filial"],
                "quantidade": resultado[
                    "total_importado"
                ],
                "mensagem": (
                    "Arquivo OFX importado com sucesso."
                ),
            },
            status=status.HTTP_201_CREATED,
        )