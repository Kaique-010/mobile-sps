from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend

from .models import BalanceteCC
from .serializers import BalanceteCCSerializer
from core.middleware import get_licenca_slug
from core.decorator import ModuloRequeridoMixin


class BalanceteCCViewSet(ModelViewSet, ModuloRequeridoMixin):
    serializer_class = BalanceteCCSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ('empr', 'fili', 'ano', 'mes_ordem', 'centro_nome', 'mes_nome')
    search_fields = ('centro_nome',)

    def get_queryset(self):
        slug = get_licenca_slug()
        if not slug:
            return BalanceteCC.objects.none()

        empresa = self.request.query_params.get('empr')
        filial = self.request.query_params.get('fili')
        ano = self.request.query_params.get('ano')
        mes = self.request.query_params.get('mes')

        qs = BalanceteCC.objects.using(slug).all()

        if empresa:
            qs = qs.filter(empr=empresa)
        if filial:
            qs = qs.filter(fili=filial)
            
      

        return qs.order_by('ano', 'mes_ordem')