# views.py
from rest_framework import viewsets
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db import transaction
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

    def perform_create(self, serializer):
        db_alias = getattr(self.request, 'db_alias', 'default')
        max_id = ListaCasamento.objects.using(db_alias).aggregate(models.Max('list_codi'))['list_codi__max'] or 0
        serializer.save(list_codi=max_id + 1)
class ItensListaCasamentoViewSet(viewsets.ModelViewSet):
    serializer_class = ItensListaCasamentoSerializer

    def get_queryset(self):
        db_alias = getattr(self.request, 'db_alias', 'default')
        return ItensListaCasamento.objects.using(db_alias).all()

    def create(self, request, *args, **kwargs):
        db_alias = getattr(request, 'db_alias', 'default')
        data = request.data

        if isinstance(data, list):
            results = []
            with transaction.atomic(using=db_alias):
                for item_data in data:
                    serializer = self.get_serializer(data=item_data)
                    serializer.is_valid(raise_exception=True)
                    instance = serializer.save()
                    results.append(serializer.data)
            return Response(results, status=status.HTTP_201_CREATED)
        else:
            return super().create(request, *args, **kwargs)
