# utils.py

from .models import Ordemservicopecas
from django.db.models import Max

def get_next_item_number(peca_empr, peca_fili, peca_orde, banco):
        ultimo = Ordemservicopecas.objects.using(banco).filter(
            peca_empr=peca_empr,
            peca_fili=peca_fili,
            peca_orde=peca_orde
        ).aggregate(max_id=Max('peca_id'))['max_id']
        return (ultimo or 0) + 1
