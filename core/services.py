# core/services.py
import hmac
import hashlib
import json
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple, Dict, Any

import requests
from django.conf import settings
from django.utils.encoding import force_bytes

from .models import Wallet, Transaction, PriceTable
from django.contrib.auth import get_user_model

User = get_user_model()

# config pulled from Django settings (add these if missing)
PAYSTACK_SECRET = getattr(settings, "PAYSTACK_SECRET_KEY", "")
PAYSTACK_BASE = getattr(settings, "PAYSTACK_BASE_URL", "https://api.paystack.co")
VTU_API_KEY = getattr(settings, "VTU_API_KEY", "")
VTU_BASE_URL = getattr(settings, "VTU_BASE_URL", "https://api.epins.com.ng/sandbox/data/")
VTU_AIRTIME_URL = getattr(settings, "VTU_AIRTIME_URL", "https://api.epins.com.ng/sandbox/airtime/")
PROVIDER_SUBACCOUNT = getattr(settings, "PROVIDER_SUBACCOUNT", "ACCT_q1us193ulmhcyzo")

PROCESSING_FEE = Decimal(str(getattr(settings, "PROCESSING_FEE", 40)))
PLATFORM_MIN_PROFIT = Decimal(str(getattr(settings, "PLATFORM_MIN_PROFIT", 150)))
MIN_PLATFORM_PCT = Decimal(str(getattr(settings, "MIN_PLATFORM_PCT", 2)))
MAX_PLATFORM_PCT = Decimal(str(getattr(settings, "MAX_PLATFORM_PCT", 30)))
HTTP_TIMEOUT = int(getattr(settings, "EXTERNAL_TIMEOUT", 20))


def compute_dynamic_split(amount_naira: Decimal) -> Tuple[int, int]:
    """
    Returns (platform_pct_int, provider_pct_int)
    Ensures provider gets majority and platform gets at least enough to cover PLATFORM_MIN_PROFIT.
    """
    if amount_naira <= 0:
        return (10, 90)

    pct_needed = (PLATFORM_MIN_PROFIT / amount_naira) * Decimal(100)
    pct_needed = pct_needed.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    platform_pct = max(pct_needed, MIN_PLATFORM_PCT)
    platform_pct = min(platform_pct, MAX_PLATFORM_PCT)

    provider_pct = (Decimal(100) - platform_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    platform_int = int(platform_pct.to_integral_value(rounding=ROUND_HALF_UP))
    provider_int = int(provider_pct.to_integral_value(rounding=ROUND_HALF_UP))

    # final safety adjustments
    if platform_int + provider_int > 100:
        platform_int = 100 - provider_int
    if provider_int <= platform_int:
        provider_int = platform_int + 1
        if provider_int > 100:
            provider_int = 100
            platform_int = 0

    return platform_int, provider_int


class PaystackService:
    SECRET_KEY = PAYSTACK_SECRET
    BASE_URL = PAYSTACK_BASE

    @classmethod
    def initialize_transaction(cls, email: str, amount_naira: Decimal, metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize Paystack transaction using dynamic split (subaccounts).
        """
        platform_pct, provider_pct = compute_dynamic_split(amount_naira)

        payload = {
            "email": email,
            "amount": int((amount_naira * Decimal(100)).to_integral_value(rounding=ROUND_HALF_UP)),
            "callback_url": getattr(settings, "PAYSTACK_CALLBACK_URL", ""),
            "metadata": metadata or {},
            "subaccounts": [
                {"subaccount": PROVIDER_SUBACCOUNT, "share": provider_pct}
            ],
        }
        headers = {"Authorization": f"Bearer {cls.SECRET_KEY}", "Content-Type": "application/json"}
        resp = requests.post(f"{cls.BASE_URL}/transaction/initialize", json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json()

    @classmethod
    def verify_transaction(cls, reference: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {cls.SECRET_KEY}"}
        resp = requests.get(f"{cls.BASE_URL}/transaction/verify/{reference}", headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def verify_signature(raw_body: bytes, signature: Optional[str]) -> bool:
        """
        Very simple signature check: compute hmac if secret present.
        In production, use real Paystack signature verification.
        """
        if not PAYSTACK_SECRET or not signature:
            return True
        computed = hmac.new(force_bytes(PAYSTACK_SECRET), msg=raw_body, digestmod=hashlib.sha512).hexdigest()
        return hmac.compare_digest(computed, signature)


class WalletService:
    @staticmethod
    def credit_user(user, amount_naira: Decimal, reference: Optional[str] = None, note: str = ""):
        wallet, _ = Wallet.objects.get_or_create(user=user)
        wallet.balance = (wallet.balance or Decimal("0.00")) + Decimal(str(amount_naira))
        wallet.save()
        tx = Transaction.objects.create(
            user=user,
            transaction_type="Wallet Funding",
            amount=Decimal(str(amount_naira)),
            status="Successful",
            reference=reference or str(uuid.uuid4())[:12],
            description=note,
        )
        return tx

    @staticmethod
    def debit_user(user, amount_naira: Decimal, reference: Optional[str] = None, note: str = ""):
        wallet, _ = Wallet.objects.get_or_create(user=user)
        if (wallet.balance or Decimal("0.00")) < Decimal(str(amount_naira)):
            return False, None
        wallet.balance = (wallet.balance or Decimal("0.00")) - Decimal(str(amount_naira))
        wallet.save()
        tx = Transaction.objects.create(
            user=user,
            transaction_type="Debit",
            amount=Decimal(str(amount_naira)),
            status="Successful",
            reference=reference or str(uuid.uuid4())[:12],
            description=note,
        )
        return True, tx


class VTUService:
    @staticmethod
    def buy_data(network: str, mobile_number: str, plan_code: str) -> dict:
        payload = {"networkId": network, "MobileNumber": mobile_number, "DataPlan": plan_code, "ref": str(uuid.uuid4())[:12]}
        headers = {"Authorization": f"Token {VTU_API_KEY}", "Content-Type": "application/json"}
        try:
            resp = requests.post(VTU_BASE_URL, json=payload, headers=headers, timeout=HTTP_TIMEOUT)
            return resp.json()
        except Exception as e:
            return {"error": "request_failed", "message": str(e)}

    @staticmethod
    def buy_airtime(network: str, phone: str, amount):
        payload = {"network": network, "phone": phone, "amount": float(amount), "ref": str(uuid.uuid4())[:12]}
        headers = {"Authorization": f"Token {VTU_API_KEY}", "Content-Type": "application/json"}
        try:
            resp = requests.post(VTU_AIRTIME_URL, json=payload, headers=headers, timeout=HTTP_TIMEOUT)
            return resp.json()
        except Exception as e:
            return {"error": "request_failed", "message": str(e)}

    @staticmethod
    def get_plan_object(plan_id: int):
        return PriceTable.objects.filter(id=plan_id).first()
