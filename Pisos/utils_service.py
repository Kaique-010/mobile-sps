# services/utils_service.py
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

def parse_decimal(value, default="0"):
    """Converte qualquer valor (str, float, None) em Decimal seguro."""
    if value is None:
        return Decimal(default)
    try:
        if isinstance(value, str):
            value = value.strip().replace(',', '.')
            if not value:
                return Decimal(default)
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)

def arredondar(valor, casas=2):
    if valor is None:
        return Decimal("0.00")
    return parse_decimal(valor).quantize(Decimal(10) ** -casas, rounding=ROUND_HALF_UP)
