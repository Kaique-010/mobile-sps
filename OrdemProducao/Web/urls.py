from django.urls import path

from .Views import (
    OrdemproducaoListView,
    OrdemproducaoCreateView,
    OrdemproducaoUpdateView,
    OrdemproducaoDeleteView,
    OurivesCreateView,
    OurivesUpdateView,
    EtapaCreateView,
    EtapaUpdateView,
    OrdemProdutoPrevCreateView,
    ConsumoMateriaPrimaView,
    MoveetapaCreateView,
    MoveetapaUpdateView,
    autocomplete_clientes,
    autocomplete_vendedores,
    autocomplete_produtos,
)

app_name = 'ordem_producao_web'

urlpatterns = [
    path('', OrdemproducaoListView.as_view(), name='ordemproducao_list'),
    path('nova/', OrdemproducaoCreateView.as_view(), name='ordemproducao_create'),
    path('<int:orpr_codi>/editar/', OrdemproducaoUpdateView.as_view(), name='ordemproducao_update'),
    path('<int:orpr_codi>/excluir/', OrdemproducaoDeleteView.as_view(), name='ordemproducao_delete'),
    path('ourives/novo/', OurivesCreateView.as_view(), name='ourives_create'),
    path('ourives/<int:ouri_codi>/editar/', OurivesUpdateView.as_view(), name='ourives_update'),
    path('etapas/nova/', EtapaCreateView.as_view(), name='etapa_create'),
    path('etapas/<int:etap_codi>/editar/', EtapaUpdateView.as_view(), name='etapa_update'),
    path('<int:orpr_codi>/materia-prima/nova/', OrdemProdutoPrevCreateView.as_view(), name='ordem_materia_prev_create'),
    path('<int:orpr_codi>/materia-prima/<int:produto_codigo>/consumo/', ConsumoMateriaPrimaView.as_view(), name='ordem_materia_consumo'),
    path('<int:orpr_codi>/movimentacao/nova/', MoveetapaCreateView.as_view(), name='ordem_mov_create'),
    path('movimentacao/<int:moet_codi>/editar/', MoveetapaUpdateView.as_view(), name='ordem_mov_update'),
    path('autocomplete/clientes/', autocomplete_clientes, name='autocomplete_clientes'),
    path('autocomplete/vendedores/', autocomplete_vendedores, name='autocomplete_vendedores'),
    path('autocomplete/produtos/', autocomplete_produtos, name='autocomplete_produtos'),
]
