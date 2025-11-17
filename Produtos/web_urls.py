from django.urls import path
from .web_views import (
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
)

urlpatterns = [
    path('', ProdutoListView.as_view(), name='produtos_web'),
    path('new/', ProdutoCreateView.as_view(), name='produto_create_web'),
    path('<str:prod_codi>/edit/', ProdutoUpdateView.as_view(), name='produto_edit_web'),
    path('<str:prod_codi>/delete/', ProdutoDeleteView.as_view(), name='produto_delete_web'),
    path('exportar/', ExportarProdutosView.as_view(), name='exportar_produtos_web'),
    path('<str:prod_codi>/foto/', ProdutoFotoView.as_view(), name='produto_foto_web'),
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
]