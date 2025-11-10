from django.urls import path
from .web_views import (
    ProdutoListView,
    ProdutoCreateView,
    ProdutoUpdateView,
    ProdutoDeleteView,
    ExportarProdutosView,
    ProdutoFotoView,
)

urlpatterns = [
    path('', ProdutoListView.as_view(), name='produtos_web'),
    path('new/', ProdutoCreateView.as_view(), name='produto_create_web'),
    path('<str:prod_codi>/edit/', ProdutoUpdateView.as_view(), name='produto_edit_web'),
    path('<str:prod_codi>/delete/', ProdutoDeleteView.as_view(), name='produto_delete_web'),
    path('exportar/', ExportarProdutosView.as_view(), name='exportar_produtos_web'),
    path('<str:prod_codi>/foto/', ProdutoFotoView.as_view(), name='produto_foto_web'),
]