# dashboards/urls.py
from django.urls import path, include
from .views import DashboardAPIView, DashboardEstoqueView, DashboardVendasView, EnviarEmail, EnviarWhats
from .views_financeiro import DashboardFinanceiroView, OrcamentoAnaliticoViewSet
from .view_extratocaixa import ExtratoCaixaViewSet
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'orcamento-analitico', OrcamentoAnaliticoViewSet, basename='orcamento-analitico')
router.register(r'extrato-caixa', ExtratoCaixaViewSet, basename='extrato-caixa')


urlpatterns = [
    path('dashboard/', DashboardAPIView.as_view(), name='dashboard'),
    path('vendas/', DashboardVendasView.as_view(), name='vendas'),
    path('estoque/', DashboardEstoqueView.as_view(), name='estoque'),
    path('envio/email/', EnviarEmail.as_view(), name='enviar_email'),
    path('envio/whatsapp/', EnviarWhats.as_view(), name='enviar_whatsapp'),
    path('financeiro/', DashboardFinanceiroView.as_view(), name='financeiro'),
] + router.urls
