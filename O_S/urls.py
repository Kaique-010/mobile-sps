from rest_framework import routers
from django.urls import path
from .views import *
from .views_financeiro import (
    GerarTitulosOSView, 
    RemoverTitulosOSView,
    ConsultarTitulosOSView,
    RelatorioFinanceiroOSView
)

router = routers.DefaultRouter()
router.register(r'ordens', OsViewSet, basename='ordens')
router.register(r'pecas', OsPecasViewSet, basename='pecas')
router.register(r'servicos', OsServicosViewSet, basename='servicos')

urlpatterns = router.urls

# Rotas Financeiras
urlpatterns += [
    path('financeiro/gerar-titulos/', GerarTitulosOSView.as_view(), name='gerar_titulos'),
    path('financeiro/remover-titulos/', RemoverTitulosOSView.as_view(), name='remover_titulos'),
    path('financeiro/consultar-titulos/<int:orde_nume>/', ConsultarTitulosOSView.as_view(), name='consultar_titulos'),
]
