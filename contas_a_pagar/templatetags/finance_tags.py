from django import template
from decimal import Decimal

register = template.Library()


def _format_brl(value: Decimal) -> str:
    # Formata com separador de milhar americano e converte para padrão BR
    s = f"{value:,.2f}"
    s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f"R$ {s}"


@register.filter(name="brl")
def brl(value) -> str:
    """Formata números para moeda BRL sem depender de locale do SO.
    Exemplos: 1234.5 -> R$ 1.234,50; None/invalid -> R$ 0,00
    """
    if value is None:
        return "R$ 0,00"
    try:
        val = Decimal(value)
    except Exception:
        try:
            val = Decimal(str(value).replace(',', '.'))
        except Exception:
            return "R$ 0,00"
    return _format_brl(val)

