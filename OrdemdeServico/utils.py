from django.db import connections
from django.db.models import Max
from OrdemdeServico.models import Ordemservicopecas


def get_next_item_number_sequence(banco, peca_orde, peca_empr, peca_fili):
    last_item = Ordemservicopecas.objects.using(banco).filter(
        peca_empr=peca_empr,
        peca_fili=peca_fili,
        peca_orde=peca_orde
    ).aggregate(Max('peca_id'))['peca_id__max']

    if last_item:
        ultimo_local = int(str(last_item)[-3:])  
    else:
        ultimo_local = 0

    novo_local = ultimo_local + 1
    novo_peca_id = int(f"{peca_orde}{novo_local:03d}")  

    return novo_peca_id
