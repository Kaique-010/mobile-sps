from django import template
from ..service import get_children

register = template.Library()


@register.simple_tag(takes_context=True)
def get_children_tag(context, cc, empresa_id):
    try:
        request = context.get('request')
        db_alias = getattr(request, 'db_alias', None)
        codigo = getattr(cc, 'cecu_expa', None) or str(cc)
        return list(get_children(codigo, int(empresa_id), db_alias=db_alias))
    except Exception:
        return []

