# core/utils/helpers.py
from decimal import Decimal, InvalidOperation

def parse_decimal(value, default=Decimal("0.00")):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default
