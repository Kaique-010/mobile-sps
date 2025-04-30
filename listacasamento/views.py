# views.py
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.response import Response
from rest_framework.filters import SearchFilter
from .models import ListaCasamento, ItensListaCasamento
from django.db import models
from rest_framework.decorators import action
from .serializers import ListaCasamentoSerializer, ItensListaCasamentoSerializer

class ListaCasamentoViewSet(viewsets.ModelViewSet):
    serializer_class = ListaCasamentoSerializer
    filter_backends = [SearchFilter]
    search_fields = ['list_noiv__nome', 'list_codi']

    def get_queryset(self):
        db_alias = getattr(self.request, 'db_alias', 'default')
        return ListaCasamento.objects.using(db_alias).all().order_by('list_codi')

class ItensListaCasamentoViewSet(viewsets.ModelViewSet):
    serializer_class = ItensListaCasamentoSerializer

    def get_queryset(self):
        db_alias = getattr(self.request, 'db_alias', 'default')
        lista_id = self.request.query_params.get("lista")
        qs = ItensListaCasamento.objects.using(db_alias)
        if lista_id:
            return qs.filter(item_list=lista_id)
        return qs.all()

    def perform_create(self, serializer):
        db_alias = getattr(self.request, 'db_alias', 'default')
        max_id = ItensListaCasamento.objects.using(db_alias).aggregate(
            models.Max("item_item")
        )["item_item__max"] or 0
        serializer.save(item_item=max_id + 1)

    @action(detail=False, methods=['post'])
    def adicionar_lote(self, request):
        db_alias = getattr(request, 'db_alias', 'default')
        lista_codi = request.data.get("lista")
        itens = request.data.get("itens", [])

        if not lista_codi or not isinstance(itens, list):
            return Response({"detail": "Parâmetros inválidos."}, status=400)

        criados = []
        max_id = ItensListaCasamento.objects.using(db_alias).aggregate(
            models.Max("item_item")
        )["item_item__max"] or 0

        for i, item in enumerate(itens):
            novo = ItensListaCasamento.objects.using(db_alias).create(
                item_item=max_id + i + 1,
                item_list=lista_codi,
                item_prod=item["produto"],  # deve ser o ID
                item_empr=request.data.get("empresa", 1),
                item_fili=request.data.get("filial", 1),
                item_usua=request.user,  # ou ajusta conforme a lógica
            )
            criados.append(novo)

        serializer = self.get_serializer(criados, many=True)
        return Response(serializer.data)