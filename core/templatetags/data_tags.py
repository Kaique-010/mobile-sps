from django import template
from decimal import Decimal

register = template.Library()


@register.filter(name="format_datas")
def format_datas(value: str) -> str:
    """Formata datas no formato yyyy-mm-dd. para dd/mm/yyyy."""
    if value is None:
        return ""
    try:
        year, month, day = value.split('-')
        return f"{day}/{month}/{year}"
    except Exception:
        return ""
