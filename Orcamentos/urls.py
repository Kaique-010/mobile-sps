# urls.py

from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import OrcamentoViewSet

router = DefaultRouter()
router.register(r'orcamentos', OrcamentoViewSet, basename='orcamentos')

# URLs customizadas para chave composta
custom_patterns = [
    path('orcamentos/<int:empresa>/<int:filial>/<int:numero>/', 
         OrcamentoViewSet.as_view({
             'get': 'retrieve',
             'put': 'update', 
             'patch': 'partial_update',
             'delete': 'destroy'
         }), name='orcamento-detail-composto'),
    # Adicionar URL para transformar-em-pedido
    path('orcamentos/<int:empresa>/<int:filial>/<int:numero>/transformar-em-pedido/', 
         OrcamentoViewSet.as_view({
             'post': 'transformar_em_pedido'
         }), name='orcamento-transformar-pedido'),
]

urlpatterns = custom_patterns + router.urls
