from .base import BaseListView
from Agricola.models import AplicacaoInsumos

class AplicacaoInsumosListView(BaseListView):
    model = AplicacaoInsumos
    template_name = 'Agricola/aplicacao_insumos_list.html'
    context_object_name = 'aplicacoes_insumos'
    empresa_field = 'apli_empr'
    filial_field = 'apli_fili'
    order_by_field = '-apli_data'

    