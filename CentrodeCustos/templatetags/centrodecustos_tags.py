from django import template
from ..service import get_children

register = template.Library()


@register.filter(name='get_children')
def get_children_filter(cc, empresa_id):
    try:
        codigo = getattr(cc, 'cecu_expa', None) or str(cc)
        return list(get_children(codigo, int(empresa_id)))
    except Exception:
        return []

