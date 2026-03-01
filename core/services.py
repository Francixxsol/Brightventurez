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
from django.db import transaction
from .models import Wallet, WalletTransaction, PriceTable
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from core.utils import generate_reference, extract_message
from .models import PriceTable, VTUTransaction

User = get_user_model()

# config pulled from Django settings (add these if missing)
PAYSTACK_SECRET = getattr(settings, "PAYSTACK_SECRET_KEY", "")
PAYSTACK_BASE = getattr(settings, "PAYSTACK_BASE_URL", "https://api.paystack.co")

# =========================
# VTU CONFIG
# =========================
VTU_API_KEY = getattr(settings, "VTU_API_KEY", "")

VTU_BASE_URL = getattr(
    settings,
    "VTU_BASE_URL",
    "https://api.epins.com.ng/sandbox"
).rstrip("/")  # removes trailing slash if present

VTU_DATA_URL = f"{VTU_BASE_URL}/data/"
VTU_AIRTIME_URL = f"{VTU_BASE_URL}/airtime/"

HEADERS = {
    "Authorization": f"Bearer {VTU_API_KEY}",
    "Content-Type": "application/json",
}


# =========================
# PLATFORM SETTINGS
# =========================

PROVIDER_SUBACCOUNT = getattr(
    settings,
    "PROVIDER_SUBACCOUNT",
    "ACCT_q1us193ulmhcyzo"
)

PROCESSING_FEE = Decimal(
    str(getattr(settings, "PROCESSING_FEE", 40))
)

PLATFORM_MIN_PROFIT = Decimal(
    str(getattr(settings, "PLATFORM_MIN_PROFIT", 150))
)

MIN_PLATFORM_PCT = Decimal(
    str(getattr(settings, "MIN_PLATFORM_PCT", 2))
)

MAX_PLATFORM_PCT = Decimal(
    str(getattr(settings, "MAX_PLATFORM_PCT", 30))
)

HTTP_TIMEOUT = int(
    getattr(settings, "EXTERNAL_TIMEOUT", 20)
)

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


#wallet servuces
class WalletService:

    @staticmethod
    @transaction.atomic
    def debit_user(user, amount, note="", reference=None):
        wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
        amount = Decimal(amount)
        if wallet.balance < amount:
            return False, "Insufficient balance", None

        wallet.balance -= amount
        wallet.save(update_fields=["balance"])

        # Generate a separate unique reference for the wallet transaction
        wallet_ref = reference or uuid.uuid4().hex[:12].upper()
        for _ in range(5):
            if not WalletTransaction.objects.filter(reference=wallet_ref).exists():
                break
            wallet_ref = uuid.uuid4().hex[:12].upper()
        else:
            raise Exception("Could not generate unique wallet transaction reference after 5 attempts")

        tx = WalletTransaction.objects.create(
            user=user,
            transaction_type="debit",
            amount=amount,
            reference=wallet_ref,
            description=note,
            status="pending"
        )
        return True, None, tx

    @staticmethod
    @transaction.atomic
    def credit_user(user, amount, note="", reference=None):
        wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
        wallet.balance += Decimal(amount)
        wallet.save(update_fields=["balance"])

        wallet_ref = reference or uuid.uuid4().hex[:12].upper()
        for _ in range(5):
            if not WalletTransaction.objects.filter(reference=wallet_ref).exists():
                break
            wallet_ref = uuid.uuid4().hex[:12].upper()
        else:
            raise Exception("Could not generate unique wallet transaction reference after 5 attempts")

        tx = WalletTransaction.objects.create(
            user=user,
            transaction_type="credit",
            amount=amount,
            reference=wallet_ref,
            description=note,
            status="success"
        )
        return True, None, tx

    @staticmethod
    def mark_success(wallet_tx):
        wallet_tx.status = "success"
        wallet_tx.save(update_fields=["status"])

    @staticmethod
    def mark_failed(wallet_tx):
        wallet_tx.status = "failed"
        wallet_tx.save(update_fields=["status"])


#Vtu services
class VTUService:
    MAX_RETRIES = 3        # retry attempts for network requests
    RETRY_DELAY = 2        # seconds between retries

    # Mapping for data (numeric codes) according to Epins network variation
    DATA_NETWORK_CODES = {
        "MTN": "01",
        "GLO": "02",
        "9MOBILE": "03",
        "AIRTEL": "04"
    }

    @staticmethod
    @transaction.atomic
    def buy_airtime(user, network, phone, amount):
        """Send Airtime via EPINS (network names, string)"""
        amount = int(amount)
        ref = generate_reference()

        payload = {
            "network": str(network).upper().strip(),  # string name for airtime
            "phone": str(phone).strip(),
            "amount": amount,
            "ref": ref
        }

        print("Sending Airtime payload:", payload)

        # Debit wallet
        ok, error, wallet_tx = WalletService.debit_user(
            user=user,
            amount=amount,
            note=f"Airtime {network} {phone}",
            reference=ref
        )
        if not ok:
            return {"success": False, "message": error}

        tx = VTUTransaction.objects.create(
            user=user,
            reference=ref,
            service="airtime",
            network=network,
            phone=phone,
            amount=amount,
            status="pending"
        )

        for attempt in range(1, VTUService.MAX_RETRIES + 1):
            try:
                response = requests.post(
                    VTU_AIRTIME_URL,
                    json=payload,
                    headers=HEADERS,
                    timeout=30
                )
                data = response.json()
                tx.response = data

                if response.status_code == 200 and str(data.get("code")) == "101":
                    tx.status = "success"
                    tx.save(update_fields=["status", "response"])
                    WalletService.mark_success(wallet_tx)
                    return {"success": True, "message": extract_message(data)}

                break  # No retry if provider returned an error

            except requests.exceptions.RequestException as e:
                print(f"Airtime attempt {attempt} failed: {e}")
                if attempt < VTUService.MAX_RETRIES:
                    import time; time.sleep(VTUService.RETRY_DELAY)
                else:
                    tx.response = {"error": str(e)}
                    break

        # Refund if failed
        WalletService.mark_failed(wallet_tx)
        WalletService.credit_user(
            user=user,
            amount=amount,
            note=f"Refund - Airtime {network} Failed",
            reference=ref
        )
        tx.status = "failed"
        tx.save(update_fields=["status", "response"])
        return {"success": False, "message": "Transaction failed or network error. Wallet refunded."}

    @staticmethod
    @transaction.atomic
    def buy_data(user, plan_network, plan_code, phone, amount):
        """Send Data via EPINS (networkId numeric codes)"""
        amount = int(amount)
        ref = generate_reference()

        network_id = VTUService.DATA_NETWORK_CODES.get(plan_network.upper())
        if not network_id:
            return {"success": False, "message": f"Unsupported network: {plan_network}"}

        payload = {
            "networkId": network_id,              # numeric code for data
            "MobileNumber": str(phone).strip(),
            "DataPlan": int(plan_code),
            "ref": ref
        }

        print("Sending Data payload:", payload)

        # Debit wallet
        ok, error, wallet_tx = WalletService.debit_user(
            user=user,
            amount=amount,
            note=f"Data Purchase {phone} Plan {plan_code}",
            reference=ref
        )
        if not ok:
            return {"success": False, "message": error}

        tx = VTUTransaction.objects.create(
            user=user,
            reference=ref,
            service="data",
            network=plan_network,
            phone=phone,
            amount=amount,
            status="pending"
        )

        try:
            response = requests.post(
                VTU_DATA_URL,
                json=payload,
                headers=HEADERS,
                timeout=30
            )
            data = response.json()
            tx.response = data

            print("VTU Response:", data, "Status Code:", response.status_code)

            if response.status_code == 200 and str(data.get("code")) == "101":
                tx.status = "success"
                tx.save(update_fields=["status", "response"])
                WalletService.mark_success(wallet_tx)
                return {"success": True, "message": extract_message(data)}

            # Failed → Refund
            WalletService.mark_failed(wallet_tx)
            WalletService.credit_user(
                user=user,
                amount=amount,
                note=f"Refund - Data {plan_code} Failed",
                reference=ref
            )
            tx.status = "failed"
            tx.save(update_fields=["status", "response"])
            return {"success": False, "message": extract_message(data)}

        except requests.exceptions.RequestException as e:
            WalletService.mark_failed(wallet_tx)
            WalletService.credit_user(
                user=user,
                amount=amount,
                note=f"Refund - Data {plan_code} Network Error",
                reference=ref
            )
            tx.status = "failed"
            tx.response = {"error": str(e)}
            tx.save(update_fields=["status", "response"])
            return {"success": False, "message": f"Network error. Wallet refunded: {str(e)}"}

#-+-+-+-+-+-+-+-
#get plans
#-+-+-+-+-+-+-+-+
    def get_plan_object(plan_id: int) -> Optional[PriceTable]:
        """
        Retrieve a PriceTable object by its ID.

        Args:
            plan_id (int): The ID of the price plan.

        Returns:
            PriceTable | None: The PriceTable instance if found, else None.
        """
        return PriceTable.objects.filter(id=plan_id).first()
