from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PermissaoModuloViewSet,
    ConfiguracaoEstoqueViewSet, ConfiguracaoFinanceiroViewSet,
    LogParametrosViewSet
)

router = DefaultRouter()
# Removido parametros-gerais pois o modelo não existe
router.register(r'permissoes-modulos', PermissaoModuloViewSet, basename='permissoes-modulos')
router.register(r'configuracao-estoque', ConfiguracaoEstoqueViewSet, basename='configuracao-estoque')
router.register(r'configuracao-financeiro', ConfiguracaoFinanceiroViewSet, basename='configuracao-financeiro')
router.register(r'logs', LogParametrosViewSet, basename='logs')

urlpatterns = [
    path('', include(router.urls)),
    
    
    
    # Endpoints específicos para compatibilidade com frontend
    path('modulos-liberados/', PermissaoModuloViewSet.as_view({'get': 'modulos_liberados'}), name='modulos-liberados'),
    path('permissoes-usuario/', PermissaoModuloViewSet.as_view({'get': 'permissoes_usuario'}), name='permissoes-usuario'),
    path('configuracao-completa/', PermissaoModuloViewSet.as_view({'get': 'configuracao_completa'}), name='configuracao-completa'),
]