from rest_framework import routers
from django.urls import path
from .views import *

from ..views_financeiro import (
    GerarTitulosOS, 
    RemoverTitulosOSView,
    ConsultarTitulosOSView
)
from ..view_dash import OrdemServicoGeralViewSet

router = routers.DefaultRouter()
router.register(r'ordens', OsViewSet, basename='ordens')
router.register(r'pecas', PecasOsViewSet, basename='pecas')
router.register(r'servicos', ServicosOsViewSet, basename='servicos')
router.register(r'os-geral', OrdemServicoGeralViewSet, basename='os-geral')

urlpatterns = router.urls

# Rotas Financeiras
urlpatterns += [
    path('financeiro/gerar-titulos/', GerarTitulosOS.as_view(), name='gerar_titulos'),
    path('financeiro/remover-titulos/', RemoverTitulosOSView.as_view(), name='remover_titulos'),
    path('financeiro/consultar-titulos/<int:orde_nume>/', ConsultarTitulosOSView.as_view(), name='consultar_titulos'),
]
