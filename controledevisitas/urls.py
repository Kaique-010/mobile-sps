from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ControleVisitaViewSet, EtapaVisitaViewSet, ItensVisitaViewSet
from .autocomplete import (
    etapas_autocomplete,
    produtos_autocomplete,
    clientes_autocomplete,
    vendedores_autocomplete,
)

router = DefaultRouter()

router.register(r'controle-visitas', ControleVisitaViewSet, basename='controle-visitas')
router.register(r'etapas-visita', EtapaVisitaViewSet, basename='etapas-visita')
router.register(r'itens-visita', ItensVisitaViewSet, basename='itens-visita')

urlpatterns = [
    path('', include(router.urls)),
    path('autocomplete/etapas/', etapas_autocomplete, name='cv-etapas-autocomplete'),
    path('autocomplete/produtos/', produtos_autocomplete, name='cv-produtos-autocomplete'),
    path('autocomplete/clientes/', clientes_autocomplete, name='cv-clientes-autocomplete'),
    path('autocomplete/vendedores/', vendedores_autocomplete, name='cv-vendedores-autocomplete'),
]
