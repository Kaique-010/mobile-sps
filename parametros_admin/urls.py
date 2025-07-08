from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ParametrosGeraisViewSet, PermissoesModulosViewSet,
    ConfiguracaoEstoqueViewSet, ConfiguracaoFinanceiroViewSet,
    LogParametrosViewSet
)

router = DefaultRouter()
router.register(r'parametros-gerais', ParametrosGeraisViewSet, basename='parametros-gerais')
router.register(r'permissoes-modulos', PermissoesModulosViewSet, basename='permissoes-modulos')
router.register(r'configuracao-estoque', ConfiguracaoEstoqueViewSet, basename='configuracao-estoque')
router.register(r'configuracao-financeiro', ConfiguracaoFinanceiroViewSet, basename='configuracao-financeiro')
router.register(r'logs', LogParametrosViewSet, basename='logs')

urlpatterns = [
    path('', include(router.urls)),
]