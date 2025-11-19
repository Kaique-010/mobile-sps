# notas_fiscais/api/autocomplete_viewsets.py

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.filters import SearchFilter
from django.db.models import Q

from core.utils import get_licenca_db_config
from Entidades.models import Entidades
from Produtos.models import Produtos

from .autocomplete_serializers import (
    EntidadeAutocompleteSerializer,
    ProdutoAutocompleteSerializer,
)


class EntidadeAutocompleteViewSet(viewsets.ViewSet):

    def list(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request) or "default"
        empresa = request.session.get("empresa_id")

        q = request.query_params.get("q", "").strip()

        qs = Entidades.objects.using(banco).filter(enti_empr=empresa)

        if q:
            qs = qs.filter(
                Q(enti_nome__iregex=q) |
                Q(enti_cnpj__icontains=q) |
                Q(enti_cpf__icontains=q)
            )

        qs = qs.only(
            "enti_clie", "enti_nome", "enti_cnpj", "enti_cpf"
        ).order_by("enti_nome")[:20]

        data = EntidadeAutocompleteSerializer(qs, many=True).data
        return Response(data)


class ProdutoAutocompleteViewSet(viewsets.ViewSet):

    def list(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request) or "default"
        empresa = request.session.get("empresa_id")

        q = request.query_params.get("q", "").strip()

        qs = Produtos.objects.using(banco).filter(prod_empr=empresa)

        if q:
            qs = qs.filter(
                Q(prod_desc__iregex=q) |
                Q(prod_refe__iregex=q) |
                Q(prod_codi__iexact=q)
            )

        qs = qs.only(
            "prod_codi", "prod_desc", "prod_refe"
        ).order_by("prod_desc")[:20]

        data = ProdutoAutocompleteSerializer(qs, many=True).data
        return Response(data)
