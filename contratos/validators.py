from datetime import date
from decimal import Decimal

TYPE_MAP = {
    int: int,
    float: (float, Decimal),
    str: str,
    "date": str  # depois você converte
}

def validate_schema(data, schema):
    errors = {}

    for field in schema["required"]:
        if field not in data or data[field] in [None, ""]:
            errors[field] = ["Campo obrigatório"]

    for field, expected in schema["types"].items():
        if field in data:
            expected_type = TYPE_MAP.get(expected, expected)

            if not isinstance(data[field], expected_type):
                errors[field] = [f"Tipo inválido"]

    if errors:
        raise ValidationError(errors)