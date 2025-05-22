# utils.py

from .models import ItensListaCasamento
from django.db.models import Max

def get_next_item_number(item_empr, item_fili, item_list, banco):
    maior = ItensListaCasamento.objects.using(banco).filter(
        item_empr=item_empr,
        item_fili=item_fili,
        item_list=item_list
    ).aggregate(Max('item_item'))['item_item__max'] or 0
    return maior + 1
