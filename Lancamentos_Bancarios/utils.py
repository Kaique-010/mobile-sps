# utils.py

from .models import Lctobancario
from django.db.models import Max
from datetime import date

def get_next_lcto_number(lcto_empr, lcto_fili, banco):
    """Gera próximo número de lançamento bancário"""
    maior = Lctobancario.objects.using(banco).filter(
        laba_empr=lcto_empr,
        laba_fili=lcto_fili
    ).aggregate(Max('laba_ctrl'))['laba_ctrl__max'] or 0
    return maior + 1
