# core/utils/helpers.py
import uuid
import time
from decimal import Decimal, InvalidOperation

def parse_decimal(value, default=Decimal("0.00")):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default

def generate_reference(prefix="TXN"):
    ts = int(time.time())
    unique_id = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{ts}-{unique_id}"
