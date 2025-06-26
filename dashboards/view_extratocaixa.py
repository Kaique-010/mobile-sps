from .models import ExtratoCaixa
from .serializers import ExtratoCaixaSerializer
from core.decorator import ModuloRequeridoMixin
from core.middleware import get_licenca_slug
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend



class ExtratoCaixaViewSet(ModelViewSet, ModuloRequeridoMixin):
    serializer_class = ExtratoCaixaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ('data', 'pedido', 'nome_cliente', 'forma_de_recebimento')
    search_fields = ('pedido', 'nome_cliente', 'produto', 'descricao', 'forma_de_recebimento')
    

    def get_queryset(self):
        slug = get_licenca_slug()
        if not slug:
            return ExtratoCaixa.objects.none()
        
        empresa = self.request.query_params.get('empresa')
        filial = self.request.query_params.get('filial')

        qs = ExtratoCaixa.objects.using(slug).all()
        if empresa:
            qs = qs.filter(empresa=empresa)
        if filial:
            qs = qs.filter(filial=filial)

        return qs.order_by('data')

      
