from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PermissaoModuloViewSet, AtualizaPermissoesModulosView, ParametroSistemaViewSet,
    ParametrosPorModuloView
)


router = DefaultRouter()

router.register(r'permissoes-modulos', PermissaoModuloViewSet, basename='permissoes-modulos')
router.register(r'parametros-sistema', ParametroSistemaViewSet, basename='parametros-sistema')



urlpatterns = [
    path('', include(router.urls)),
       
    
    # Endpoints específicos para compatibilidade com frontend
    path('modulos_liberados/', PermissaoModuloViewSet.as_view({'get': 'modulos_liberados'}), name='modulos_liberados'),
    path('permissoes-usuario/', PermissaoModuloViewSet.as_view({'get': 'permissoes_usuario'}), name='permissoes-usuario'),
    path('configuracao-completa/', PermissaoModuloViewSet.as_view({'get': 'configuracao_completa'}), name='configuracao-completa'),
    path('atualizapermissoes/', AtualizaPermissoesModulosView.as_view(), name='atualiza-permissoes'),
    path('parametros-por-modulo/', ParametrosPorModuloView.as_view(), name='parametros-por-modulo'),
]