from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import EntidadesViewSet, EntidadesRelatorioAPI
from .Views.entilogin_view import EntidadesLoginViewSet
from .Views.relatorios import PedidosViewSet, OrcamentosViewSet, OrdemServicoViewSet, OsViewSet, PedidosGeralViewSet
from .Views.dashboard_clientes import ClienteDashboardViewSet

router = DefaultRouter()
router.register(r'entidades', EntidadesViewSet, basename='entidades')
router.register(r'dashboards/cliente-dashboard', ClienteDashboardViewSet, basename='cliente-dashboard'),
router.register(r'pedidos', PedidosViewSet, basename='pedidos'),
router.register(r'pedidos-geral', PedidosGeralViewSet, basename='pedidos-geral'),
router.register(r'orcamentos', OrcamentosViewSet, basename='orcamentos'),
router.register(r'ordem-servico', OrdemServicoViewSet, basename='ordem-servico'),
router.register(r'os', OsViewSet, basename='os')




# Rota específica para login e funções relacionadas a entidades clientes
urlpatterns = [
    path('login/', EntidadesLoginViewSet.as_view({'post': 'create'}), name='entidades-login'),
    path('relatorio/', EntidadesRelatorioAPI.as_view(), name='relatorio-entidades'),

    
    
] + router.urls