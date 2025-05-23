# dashboards/urls.py
from django.urls import path
from .views import DashboardAPIView, DashboardEstoqueView, DashboardVendasView

urlpatterns = [
    path('dashboard/', DashboardAPIView.as_view(), name='dashboard'),
    path('vendas/', DashboardVendasView.as_view(), name='vendas'),
    path('estoque/', DashboardEstoqueView.as_view(), name='estoque'),
]
