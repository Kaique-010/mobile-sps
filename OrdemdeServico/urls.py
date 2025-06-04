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
router.register(r'ordens', OrdemServicoViewSet, basename='ordens')
router.register(r'pecas', OrdemServicoPecasViewSet, basename='pecas')
router.register(r'servicos', OrdemServicoServicosViewSet, basename='servicos')
router.register(r'fotos', FotosViewSet, basename='fotos')
router.register(r'imagens/antes', ImagemAntesViewSet, 'imagensantes')
router.register(r'imagens/durante', ImagemDuranteViewSet, 'iamegsndurante')
router.register(r'imagens/depois', ImagemDepoisViewSet, basename='imagensdepois')

urlpatterns = router.urls

# Rotas Financeiras
urlpatterns += [
    path('financeiro/gerar-titulos/', GerarTitulosOSView.as_view(), name='gerar_titulos'),
    path('financeiro/remover-titulos/', RemoverTitulosOSView.as_view(), name='remover_titulos'),
    path('financeiro/consultar-titulos/<int:orde_nume>/', ConsultarTitulosOSView.as_view(), name='consultar_titulos'),
    path('financeiro/relatorio/', RelatorioFinanceiroOSView.as_view(), name='relatorio_financeiro'),
]
