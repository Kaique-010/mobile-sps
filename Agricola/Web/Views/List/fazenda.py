from django.http import JsonResponse
from django.views.generic import ListView
from .base import BaseListView
from Agricola.models import Fazenda



class FazendaListView(BaseListView):
    model = Fazenda
    template_name = 'Agricola/fazenda_list.html'
    context_object_name = 'fazendas'
    empresa_field = 'faze_empr'
    filial_field = 'faze_fili'
    order_by_field = 'faze_nome'