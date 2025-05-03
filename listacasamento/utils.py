from django.db.models import Max
from listacasamento.models import ItensListaCasamento

def get_next_item_number(item_empr, item_fili, item_list):
        from .models import ItensListaCasamento

        ultimo_item = (
            ItensListaCasamento.objects
            .filter(item_empr=item_empr, item_fili=item_fili, item_list=item_list)
            .order_by('-item_item')
            .first()
        )
        return (ultimo_item.item_item + 1) if ultimo_item else 1
