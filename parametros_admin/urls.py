from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PermissaoModuloViewSet, AtualizaPermissoesModulosView, ParametroSistemaViewSet,ParametrosPorModuloView
)


router = DefaultRouter()

router.register(r'permissoes-modulos', PermissaoModuloViewSet, basename='permissoes-modulos')
router.register(r'parametros-sistema', ParametroSistemaViewSet, basename='parametros-sistema')



urlpatterns = [
    path('', include(router.urls)),
       
    # Endpoints específicos para compatibilidade com frontend
    path('modulos_liberados/', PermissaoModuloViewSet.as_view({'get': 'modulos_liberados'}), name='modulos_liberados'),
    path('atualizapermissoes/', AtualizaPermissoesModulosView.as_view(), name='atualiza-permissoes'),
    path('parametros-por-modulo/', ParametrosPorModuloView.as_view(), name='parametros-por-modulo'),
    
    # NOVOS ENDPOINTS para compatibilidade com frontend
    path('permissoes_modulos/', PermissaoModuloViewSet.as_view({'get': 'permissoes_usuario'}), name='permissoes-usuario'),
    path('verificar-permissao/<str:tela>/<str:operacao>/', PermissaoModuloViewSet.as_view({'get': 'verificar_permissao'}), name='verificar-permissao'),
]