from django.db.models import Max
from listacasamento.models import ItensListaCasamento

def get_next_item_number(item_list, item_empr, item_fili):
    ultimo = ItensListaCasamento.objects.filter(
        item_list=item_list,
        item_empr=item_empr,
        item_fili=item_fili
    ).aggregate(Max('item_item'))['item_item__max']
    return (ultimo or 0) + 1
