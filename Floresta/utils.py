# utils.py

from .models import Propriedades
from django.db.models import Max

def get_next_prop_number(prop_empr, prop_fili, banco):
    """Gera próximo número de propriedade"""
    maior = Propriedades.objects.using(banco).filter(
        prop_empr=prop_empr,
        prop_fili=prop_fili
    ).aggregate(Max('prop_codi'))['prop_codi__max'] or 0
    return maior + 1
