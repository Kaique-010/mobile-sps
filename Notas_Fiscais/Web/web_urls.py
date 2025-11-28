from django.urls import path

from .Views.nota.nota_list import NotaListView
from .Views.nota.nota_detail import NotaDetailView
from .Views.nota.nota_emissao import NotaEmissaoView
from .Views.nota.nota_update import NotaUpdateView
from .Views.nota.autocomplete import (
    entidades_autocomplete,
    produtos_autocomplete,
    produto_detalhe,
    cfop_autocomplete,
    transportadoras_autocomplete,
)


urlpatterns = [
    path('', NotaListView.as_view(), name='notas_list_web'),
    path('<int:pk>/', NotaDetailView.as_view(), name='nota_detail_web'),
    path('<int:pk>/editar/', NotaUpdateView.as_view(), name='nota_update_web'),
    path('emissao/', NotaEmissaoView.as_view(), name='nota_emissao_web'),
    path('entidades-autocomplete/', entidades_autocomplete, name='entidades_autocomplete_web'),
    path('produtos-autocomplete/', produtos_autocomplete, name='produtos_autocomplete_web'),
    path('produto-detalhe/<str:codigo>/', produto_detalhe, name='produto_detalhe_web'),
    path('cfop-autocomplete/', cfop_autocomplete, name='cfop_autocomplete_web'),
    path('transportadoras-autocomplete/', transportadoras_autocomplete, name='transportadoras_autocomplete_web'),
]
