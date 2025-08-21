from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import EntidadesViewSet
from .entilogin_view import EntidadesLoginViewSet, PedidosViewSet, OrcamentosViewSet, OrdemServicoViewSet, OsViewSet, PedidosGeralViewSet, ClienteDashboardViewSet

router = DefaultRouter()
router.register(r'entidades', EntidadesViewSet, basename='entidades')
router.register(r'pedidos', PedidosViewSet, basename='pedidos')
router.register(r'pedidos-geral', PedidosGeralViewSet, basename='pedidos-geral')
router.register(r'orcamentos', OrcamentosViewSet, basename='orcamentos')
router.register(r'ordem-servico', OrdemServicoViewSet, basename='ordem-servico')
router.register(r'os', OsViewSet, basename='os')
router.register(r'dashboards/cliente-dashboard', ClienteDashboardViewSet, basename='cliente-dashboard')

# Rota específica para login
urlpatterns = [
    path('login/', EntidadesLoginViewSet.as_view({'post': 'create'}), name='entidades-login'),
    
] + router.urls