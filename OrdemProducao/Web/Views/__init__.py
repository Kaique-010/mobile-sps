from .list_view import OrdemproducaoListView
from .create_view import OrdemproducaoCreateView
from .update_view import OrdemproducaoUpdateView
from .delete_view import OrdemproducaoDeleteView
from .autocompletes import autocomplete_clientes, autocomplete_vendedores, autocomplete_produtos
from .ourives_views import OurivesCreateView, OurivesUpdateView
from .etapa_views import EtapaCreateView, EtapaUpdateView
from .filhos_views import OrdemProdutoPrevCreateView, MoveetapaCreateView, MoveetapaUpdateView
from .consumo_materia_prima_view import ConsumoMateriaPrimaView

__all__ = [
    'OrdemproducaoListView',
    'OrdemproducaoCreateView',
    'OrdemproducaoUpdateView',
    'OrdemproducaoDeleteView',
    'autocomplete_clientes',
    'autocomplete_vendedores',
    'autocomplete_produtos',
    'OurivesCreateView',
    'OurivesUpdateView',
    'EtapaCreateView',
    'EtapaUpdateView',
    'OrdemProdutoPrevCreateView',
    'MoveetapaCreateView',
    'MoveetapaUpdateView',
    'ConsumoMateriaPrimaView',
]
