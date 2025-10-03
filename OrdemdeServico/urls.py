from rest_framework import routers
from django.urls import path
from .views import (
    OrdemServicoViewSet, OrdemServicoPecasViewSet, OrdemServicoServicosViewSet,
    ImagemAntesViewSet, ImagemDuranteViewSet, ImagemDepoisViewSet, 
    WorkflowSetorViewSet, OrdemServicoFaseSetorViewSet
)
from .views_financeiro import (
    GerarTitulosOSView, 
    RemoverTitulosOSView,
    ConsultarTitulosOSView,
    RelatorioFinanceiroOSView
)

from .view_historico import HistoricoWorkflowViewSet

from .view_dash import OrdensEletroViewSet

router = routers.DefaultRouter()
router.register(r'ordens', OrdemServicoViewSet, basename='ordens')
router.register(r'pecas', OrdemServicoPecasViewSet, basename='pecas')
router.register(r'servicos', OrdemServicoServicosViewSet, basename='servicos')
router.register(r'imagens-antes', ImagemAntesViewSet, basename='imagens-antes')
router.register(r'imagens-durante', ImagemDuranteViewSet, basename='imagens-durante')
router.register(r'imagens-depois', ImagemDepoisViewSet, basename='imagens-depois')
router.register(r'fase-setor', OrdemServicoFaseSetorViewSet, basename='fase-setor')
router.register(r'workflow-setor', WorkflowSetorViewSet, basename='workflow-setor')
router.register(r'historico-workflow', HistoricoWorkflowViewSet, basename='historico-workflow')
router.register(r'ordens-eletro', OrdensEletroViewSet, basename='ordens-eletro')



urlpatterns = router.urls

# Rotas Financeiras
urlpatterns += [
    path('financeiro/gerar-titulos/', GerarTitulosOSView.as_view(), name='gerar_titulos'),
    path('financeiro/remover-titulos/', RemoverTitulosOSView.as_view(), name='remover_titulos'),
    path('financeiro/consultar-titulos/<int:orde_nume>/', ConsultarTitulosOSView.as_view(), name='consultar_titulos'),
    path('financeiro/relatorio/', RelatorioFinanceiroOSView.as_view(), name='relatorio_financeiro'),
    # Novos end points
    path('ordens/<int:id>/avancar-setor/', OrdemServicoViewSet.as_view({'post': 'avancar_setor'}), name='avancar_setor'),
    path('ordens/<int:id>/proximos-setores/', OrdemServicoViewSet.as_view({'get': 'proximos_setores'}), name='proximos_setores'),
    path('ordens/<int:id>/historico-workflow/', OrdemServicoViewSet.as_view({'get': 'historico_workflow'}), name='historico_workflow'),
]

