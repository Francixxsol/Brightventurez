# core/utils/helpers.py
import uuid
import time
from decimal import Decimal, InvalidOperation

def parse_decimal(value, default=Decimal("0.00")):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default

def extract_message(data):
    """
    Safely extract response message from EPINS response.
    Handles both string and dict descriptions.
    """
    description = data.get("description")

    if isinstance(description, dict):
        return description.get("response_description", "Transaction processed")

    if isinstance(description, str):
        return description

    return data.get("message", "Transaction processed")
