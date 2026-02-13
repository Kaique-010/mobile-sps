from django.urls import path
from .Views.List import (
    FazendaListView, TalhaoListView, CategoriaProdutoListView,
    ProdutoAgroListView, EstoqueFazendaListView, MovimentacaoEstoqueListView,
    HistoricoMovimentacaoListView, AplicacaoInsumosListView,
    AnimalListView, EventoAnimalListView
)
from .Views.Create import (
    FazendaCreateView, TalhaoCreateView, CategoriaProdutoCreateView,
    ProdutoAgroCreateView, EstoqueFazendaCreateView, MovimentacaoEstoqueCreateView,
    HistoricoMovimentacaoCreateView, AplicacaoInsumosCreateView,
    AnimalCreateView, EventoAnimalCreateView,
    LoteCreateView, LoteCreateHTMXView, LoteFormHTMXView
)
from .Views.Update import (
    FazendaUpdateView, TalhaoUpdateView, CategoriaProdutoUpdateView,
    ProdutoAgroUpdateView, EstoqueFazendaUpdateView, MovimentacaoEstoqueUpdateView,
    GerarFinanceiroMovimentacaoView, MovimentacaoFinanceiroListView,
    HistoricoMovimentacaoUpdateView, AplicacaoInsumosUpdateView,
    AnimalUpdateView, EventoAnimalUpdateView
)
from .Views.Delete import (
    FazendaDeleteView, TalhaoDeleteView, CategoriaProdutoDeleteView,
    ProdutoAgroDeleteView, EstoqueFazendaDeleteView, MovimentacaoEstoqueDeleteView,
    HistoricoMovimentacaoDeleteView, AplicacaoInsumosDeleteView,
    AnimalDeleteView, EventoAnimalDeleteView
)
from .Views.Reports import (
    RelatorioProdutosPorLoteView,
    RelatorioProdutosSemLoteView,
    RelatorioExtratoMovimentacaoView
)
from .Views.Update import lotes as lotes_update
from .Views.Delete import lotes as lotes_delete
from Agricola.Rest.autocompletes import FazendaAutocompleteView, CategoriaProdutoAutocomplete, ProdutoAutocompleteView, TalhaoAutocompleteView, AnimalAutocompleteView, EntidadeAutocompleteView
from Agricola.views import ParametrosAgricolasView

app_name = 'AgricolaWeb'

urlpatterns = [
    # Autocompletes
    path('autocompletes/fazendas/', FazendaAutocompleteView.as_view(), name='autocomplete_fazendas'),
    path('autocompletes/categorias-produtos/', CategoriaProdutoAutocomplete.as_view(), name='autocomplete_categorias_produtos'),
    path('autocompletes/produtos-agro/', ProdutoAutocompleteView.as_view(), name='autocomplete_produtos_agro'),
    path('autocompletes/talhoes/', TalhaoAutocompleteView.as_view(), name='autocomplete_talhoes'),
    path('autocompletes/animais/', AnimalAutocompleteView.as_view(), name='autocomplete_animais'),
    path('autocompletes/entidades/', EntidadeAutocompleteView.as_view(), name='autocomplete_entidades'),
    


    # Fazenda
    path('fazendas/', FazendaListView.as_view(), name='fazenda_list'),
    path('fazendas/criar/', FazendaCreateView.as_view(), name='fazenda_create'),
    path('fazendas/<int:pk>/editar/', FazendaUpdateView.as_view(), name='fazenda_update'),
    path('fazendas/<int:pk>/excluir/', FazendaDeleteView.as_view(), name='fazenda_delete'),

    # Talhao
    path('talhoes/', TalhaoListView.as_view(), name='talhao_list'),
    path('talhoes/criar/', TalhaoCreateView.as_view(), name='talhao_create'),
    path('talhoes/<int:pk>/editar/', TalhaoUpdateView.as_view(), name='talhao_update'),
    path('talhoes/<int:pk>/excluir/', TalhaoDeleteView.as_view(), name='talhao_delete'),

    # CategoriaProduto
    path('categorias-produtos/', CategoriaProdutoListView.as_view(), name='categoria_produto_list'),
    path('categorias-produtos/criar/', CategoriaProdutoCreateView.as_view(), name='categoria_produto_create'),
    path('categorias-produtos/<int:pk>/editar/', CategoriaProdutoUpdateView.as_view(), name='categoria_produto_update'),
    path('categorias-produtos/<int:pk>/excluir/', CategoriaProdutoDeleteView.as_view(), name='categoria_produto_delete'),

    # ProdutoAgro
    path('produtos-agro/', ProdutoAgroListView.as_view(), name='produto_agro_list'),
    path('produtos-agro/criar/', ProdutoAgroCreateView.as_view(), name='produto_agro_create'),
    path('produtos-agro/<int:pk>/editar/', ProdutoAgroUpdateView.as_view(), name='produto_agro_update'),
    path('produtos-agro/<int:pk>/excluir/', ProdutoAgroDeleteView.as_view(), name='produto_agro_delete'),

    # EstoqueFazenda
    path('estoque-fazenda/', EstoqueFazendaListView.as_view(), name='estoque_fazenda_list'),
    path('estoque-fazenda/criar/', EstoqueFazendaCreateView.as_view(), name='estoque_fazenda_create'),
    path('estoque-fazenda/<int:pk>/editar/', EstoqueFazendaUpdateView.as_view(), name='estoque_fazenda_update'),
    path('estoque-fazenda/<int:pk>/excluir/', EstoqueFazendaDeleteView.as_view(), name='estoque_fazenda_delete'),

    # MovimentacaoEstoque
    path('movimentacoes-estoque/', MovimentacaoEstoqueListView.as_view(), name='movimentacao_estoque_list'),
    path('movimentacoes-estoque/criar/', MovimentacaoEstoqueCreateView.as_view(), name='movimentacao_estoque_create'),
    path('movimentacoes-estoque/<int:pk>/editar/', MovimentacaoEstoqueUpdateView.as_view(), name='movimentacao_estoque_update'),
    path('movimentacoes-estoque/<int:pk>/financeiro/', GerarFinanceiroMovimentacaoView.as_view(), name='movimentacao_estoque_financeiro'),
    path('movimentacoes-estoque/<int:pk>/financeiro-list/', MovimentacaoFinanceiroListView.as_view(), name='movimentacao_estoque_financeiro_list'),
    path('movimentacoes-estoque/<int:pk>/excluir/', MovimentacaoEstoqueDeleteView.as_view(), name='movimentacao_estoque_delete'),

    # HistoricoMovimentacao
    path('historico-movimentacoes/', HistoricoMovimentacaoListView.as_view(), name='historico_movimentacao_list'),
    path('historico-movimentacoes/criar/', HistoricoMovimentacaoCreateView.as_view(), name='historico_movimentacao_create'),
    path('historico-movimentacoes/<int:pk>/editar/', HistoricoMovimentacaoUpdateView.as_view(), name='historico_movimentacao_update'),
    path('historico-movimentacoes/<int:pk>/excluir/', HistoricoMovimentacaoDeleteView.as_view(), name='historico_movimentacao_delete'),

    # AplicacaoInsumos
    path('aplicacao-insumos/', AplicacaoInsumosListView.as_view(), name='aplicacao_insumos_list'),
    path('aplicacao-insumos/criar/', AplicacaoInsumosCreateView.as_view(), name='aplicacao_insumos_create'),
    path('aplicacao-insumos/<int:pk>/editar/', AplicacaoInsumosUpdateView.as_view(), name='aplicacao_insumos_update'),
    path('aplicacao-insumos/<int:pk>/excluir/', AplicacaoInsumosDeleteView.as_view(), name='aplicacao_insumos_delete'),

    # Animal
    path('animais/', AnimalListView.as_view(), name='animal_list'),
    path('animais/criar/', AnimalCreateView.as_view(), name='animal_create'),
    path('animais/<int:pk>/editar/', AnimalUpdateView.as_view(), name='animal_update'),
    path('animais/<int:pk>/excluir/', AnimalDeleteView.as_view(), name='animal_delete'),

    # EventoAnimal
    path('eventos-animais/', EventoAnimalListView.as_view(), name='evento_animal_list'),
    path('eventos-animais/criar/', EventoAnimalCreateView.as_view(), name='evento_animal_create'),
    path('eventos-animais/<int:pk>/editar/', EventoAnimalUpdateView.as_view(), name='evento_animal_update'),
    path('eventos-animais/<int:pk>/excluir/', EventoAnimalDeleteView.as_view(), name='evento_animal_delete'),

    # Parametros
    path('parametros/', ParametrosAgricolasView.as_view(), name='parametros_agricolas'),

    # Lote (HTMX)
    path('lotes/criar/', LoteCreateView.as_view(), name='lote_create'),
    path('lotes/htmx/criar/<int:produto_id>/', LoteCreateHTMXView.as_view(), name='lote_create_htmx'),
    path('lotes/htmx/form/<int:produto_id>/', LoteFormHTMXView.as_view(), name='lote_form_htmx'),
    path('lotes/<int:pk>/editar/', lotes_update.LoteProdutosUpdateView.as_view(), name='lote_update'),
    path('lotes/<int:pk>/excluir/', lotes_delete.LoteProdutosDeleteView.as_view(), name='lote_delete'),
    
    # Relatórios
    path('relatorios/produtos-por-lote/', RelatorioProdutosPorLoteView.as_view(), name='relatorio_produtos_lote'),
    path('relatorios/produtos-sem-lote/', RelatorioProdutosSemLoteView.as_view(), name='relatorio_produtos_sem_lote'),
    path('relatorios/extrato-movimentacao/', RelatorioExtratoMovimentacaoView.as_view(), name='relatorio_extrato_movimentacao'),
]
