from django.urls import path
from .Views.listar import NcmFiscalPadraoListView, NcmListView
from .Views.criar import NcmFiscalPadraoCreateView, NcmCreateView
from .Views.update import NcmFiscalPadraoUpdateView, NcmUpdateView
from .Views.jobViews import job_importar_ibpt
from .Views.web_views import (
    ProdutoListView,
    ProdutoCreateView,
    ProdutoUpdateView,
    ProdutoDeleteView,
    ExportarProdutosView,
    ProdutoFotoView,
    GrupoListView,
    GrupoCreateView,
    GrupoUpdateView,
    GrupoDeleteView,
    SubgrupoListView,
    SubgrupoCreateView,
    SubgrupoUpdateView,
    SubgrupoDeleteView,
    FamiliaListView,
    FamiliaCreateView,
    FamiliaUpdateView,
    FamiliaDeleteView,
    MarcaListViewWeb,
    MarcaCreateView,
    MarcaUpdateView,
    MarcaDeleteView,
    SaldosDashboardView,
    autocomplete_produtos,
    UnidadeMedidaListView,
    UnidadeMedidaCreateView,
    UnidadeMedidaUpdateView,
    UnidadeMedidaDeleteView,
    SimularImpostosView
)
from .Views.autocompletes import autocomplete_unidades, autocomplete_grupos, autocomplete_marcas, autocomplete_subgrupos, autocomplete_familias, autocomplete_ncms


urlpatterns = [
    path("simular-impostos/", SimularImpostosView.as_view(), name="simular_impostos_web"),
    path("ncm-fiscal-padrao/", NcmFiscalPadraoListView.as_view(), name="ncmfiscalpadrao_list"),
    path("ncm-fiscal-padrao/novo/", NcmFiscalPadraoCreateView.as_view(), name="ncmfiscalpadrao_create"),
    path("ncm-fiscal-padrao/<int:pk>/editar/", NcmFiscalPadraoUpdateView.as_view(), name="ncmfiscalpadrao_update"),
    path("ncm/", NcmListView.as_view(), name="ncm_list"),
    path("ncm/novo/", NcmCreateView.as_view(), name="ncm_create"),
    path("ncm/<int:pk>/editar/", NcmUpdateView.as_view(), name="ncm_update"),
    path("autocomplete/ncms/", autocomplete_ncms, name="autocomplete_ncms"),
    path('', ProdutoListView.as_view(), name='produtos_web'),
    path('new/', ProdutoCreateView.as_view(), name='produto_create_web'),
    path('<str:prod_codi>/edit/', ProdutoUpdateView.as_view(), name='produto_edit_web'),
    path('<str:prod_codi>/delete/', ProdutoDeleteView.as_view(), name='produto_delete_web'),
    path('exportar/', ExportarProdutosView.as_view(), name='exportar_produtos_web'),
    path('<str:prod_codi>/foto/', ProdutoFotoView.as_view(), name='produto_foto_web'),
    
    # Unidades de Medida
    path('unidades/', UnidadeMedidaListView.as_view(), name='unidades_web'),
    path('unidades/new/', UnidadeMedidaCreateView.as_view(), name='unidade_create_web'),
    path('unidades/<str:codigo>/edit/', UnidadeMedidaUpdateView.as_view(), name='unidade_edit_web'),
    path('unidades/<str:codigo>/delete/', UnidadeMedidaDeleteView.as_view(), name='unidade_delete_web'),
    # Grupos
    path('grupos/', GrupoListView.as_view(), name='grupos_web'),
    path('grupos/new/', GrupoCreateView.as_view(), name='grupo_create_web'),
    path('grupos/<str:codigo>/edit/', GrupoUpdateView.as_view(), name='grupo_edit_web'),
    path('grupos/<str:codigo>/delete/', GrupoDeleteView.as_view(), name='grupo_delete_web'),
    # Subgrupos
    path('subgrupos/', SubgrupoListView.as_view(), name='subgrupos_web'),
    path('subgrupos/new/', SubgrupoCreateView.as_view(), name='subgrupo_create_web'),
    path('subgrupos/<str:codigo>/edit/', SubgrupoUpdateView.as_view(), name='subgrupo_edit_web'),
    path('subgrupos/<str:codigo>/delete/', SubgrupoDeleteView.as_view(), name='subgrupo_delete_web'),
    # Famílias
    path('familias/', FamiliaListView.as_view(), name='familias_web'),
    path('familias/new/', FamiliaCreateView.as_view(), name='familia_create_web'),
    path('familias/<str:codigo>/edit/', FamiliaUpdateView.as_view(), name='familia_edit_web'),
    path('familias/<str:codigo>/delete/', FamiliaDeleteView.as_view(), name='familia_delete_web'),
    # Marcas
    path('marcas/', MarcaListViewWeb.as_view(), name='marcas_web'),
    path('marcas/new/', MarcaCreateView.as_view(), name='marca_create_web'),
    path('marcas/<int:codigo>/edit/', MarcaUpdateView.as_view(), name='marca_edit_web'),
    path('marcas/<int:codigo>/delete/', MarcaDeleteView.as_view(), name='marca_delete_web'),
    
    # Jobs
    path('jobs/importar-ibpt/', job_importar_ibpt, name='job_importar_ibpt'),
    
    # Saldos
    path('saldos/', SaldosDashboardView.as_view(), name='saldos_web'),
    path('autocomplete/produtos/', autocomplete_produtos, name='autocomplete_produtos'),
    
    # Autocompletes
    path('autocomplete/grupos/', autocomplete_grupos, name='autocomplete_grupos'),
    path('autocomplete/unidades/', autocomplete_unidades, name='autocomplete_unidades'),
    path('autocomplete/marcas/', autocomplete_marcas, name='autocomplete_marcas'),
    path('autocomplete/subgrupos/', autocomplete_subgrupos, name='autocomplete_subgrupos'),
    path('autocomplete/familias/', autocomplete_familias, name='autocomplete_familias'),
]
