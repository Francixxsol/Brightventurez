import json
import uuid
import time
import requests
from decimal import Decimal, InvalidOperation

from .models import (
    Provider,
    ProviderPlan,
    VirtualPlan,
    DataTransaction,
    Wallet
)

# ======================================================
# SAFE DECIMAL PARSER
# ======================================================
def parse_decimal(value, default=Decimal("0.00")):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


# ======================================================
# JSON SAFE PARSER
# ======================================================
def json_or_text(resp):
    try:
        return resp.json()
    except Exception:
        return {"text": getattr(resp, "text", "")}


# ======================================================
# TIMESTAMPED REFERENCE GENERATOR
# ALWAYS UNIQUE
# Example: 7f23ab3c-91f2-4d39-aa33-2b8a08e93712-1733800201
# ======================================================
def generate_reference():
    return f"{uuid.uuid4()}-{int(time.time())}"


# ======================================================
# FETCH PROVIDER PLANS
# Sync provider → ProviderPlan
# ======================================================
def fetch_provider_plans(provider_id):
    provider = Provider.objects.get(id=provider_id)
    headers = {"Authorization": f"Bearer {provider.api_key}"}

    url = f"{provider.api_base_url}/data-plans"

    try:
        response = requests.get(url, headers=headers, timeout=30)
    except Exception as e:
        return {"status": False, "error": str(e)}

    if response.status_code != 200:
        return {"status": False, "error": response.text}

    data = response.json()

    for plan in data.get("plans", []):
        ProviderPlan.objects.update_or_create(
            provider=provider,
            plan_code=plan["code"],
            defaults={
                "plan_name": plan["name"],
                "network": plan["network"],
                "size_mb": plan["size"],
                "price": parse_decimal(plan["price"]),
            },
        )

    return {"status": True}


# ======================================================
# BUY DATA (Virtual + Provider)
# Returns DataTransaction object
# Supported statuses:
#  - SUCCESS
#  - FAILED
#  - PENDING
# ======================================================
def buy_data(user, network, plan_id, phone_number, plan_type="VIRTUAL"):

    # --------------------------
    # SELECT PLAN TYPE
    # --------------------------
    if plan_type == "VIRTUAL":
        plan = VirtualPlan.objects.get(id=plan_id)
        amount = plan.selling_price
        provider_plan = plan.linked_provider_plan
        plan_name = plan.plan_name

    else:  # PROVIDER DIRECT
        plan = ProviderPlan.objects.get(id=plan_id)
        amount = plan.price
        provider_plan = plan
        plan_name = plan.plan_name

    # --------------------------
    # CREATE NEW TRANSACTION (PENDING)
    # --------------------------
    txn = DataTransaction.objects.create(
        user=user,
        network=network,
        phone_number=phone_number,
        plan_type=plan_type,
        plan_name=plan_name,
        amount=amount,
        reference=ref,
        status="PENDING"
    )

    # --------------------------
    # CALL PROVIDER API
    # --------------------------
    try:
        provider = provider_plan.provider

        headers = {"Authorization": f"Bearer {provider.api_key}"}
        payload = {
            "network": network,
            "plan_code": provider_plan.plan_code,
            "phone": phone_number,
            "reference": ref,
        }

        url = f"{provider.api_base_url}/buy-data"

        res = requests.post(url, json=payload, headers=headers, timeout=40)
        data = json_or_text(res)

        # Store response
        txn.provider_response = json.dumps(data)

        # --------------------------
        # DECIDE TRANSACTION STATUS
        # --------------------------
        provider_status = str(data.get("status", "")).lower()

        if res.status_code == 200:
            if provider_status in ["success", "successful", "ok", "completed"]:
                txn.status = "SUCCESS"
            elif provider_status in ["pending", "processing"]:
                txn.status = "PENDING"
            else:
                txn.status = "FAILED"
        else:
            txn.status = "FAILED"

        txn.save()
        return txn

    except Exception as e:
        txn.status = "FAILED"
        txn.provider_response = str(e)
        txn.save()
        return txn

def generate_reference(prefix="TXN"):
    """
    Generate a unique transaction reference.
    Example: TXN-1702308392-9f1b2c
    """
    ts = int(time.time())
    unique_id = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{ts}-{unique_id}"


# ======================================================
# GET OR CREATE USER WALLET
# ======================================================
def get_or_create_wallet(user):
    wallet, created = Wallet.objects.get_or_create(
        user=user,
        defaults={"balance": Decimal("0.00")}
    )
    return wallet
