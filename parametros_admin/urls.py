from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PermissaoModuloViewSet, AtualizaPermissoesModulosView

)

router = DefaultRouter()
# Removido parametros-gerais pois o modelo não existe
router.register(r'permissoes-modulos', PermissaoModuloViewSet, basename='permissoes-modulos')



urlpatterns = [
    path('', include(router.urls)),
    
    
    
    # Endpoints específicos para compatibilidade com frontend
    path('modulos-liberados/', PermissaoModuloViewSet.as_view({'get': 'modulos_liberados'}), name='modulos-liberados'),
    path('permissoes-usuario/', PermissaoModuloViewSet.as_view({'get': 'permissoes_usuario'}), name='permissoes-usuario'),
    path('configuracao-completa/', PermissaoModuloViewSet.as_view({'get': 'configuracao_completa'}), name='configuracao-completa'),
    path('atualizapermissoes/', AtualizaPermissoesModulosView.as_view(), name='atualiza-permissoes'),
]