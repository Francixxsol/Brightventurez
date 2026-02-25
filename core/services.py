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
from .utils import generate_reference
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
)

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
    def _generate_wallet_reference():
        return uuid.uuid4().hex.upper()

    @staticmethod
    def _create_transaction(user, transaction_type, amount, note, status, reference=None):
        for _ in range(3):
            try:
                return WalletTransaction.objects.create(
                    user=user,
                    transaction_type=transaction_type,
                    amount=amount,
                    reference=reference or WalletService._generate_wallet_reference(),
                    description=note,
                    status=status
                )
            except IntegrityError:
                if reference:
                    raise
        raise Exception("Could not generate unique reference")

    @staticmethod
    @transaction.atomic
    def debit_user(user, amount, note="", reference=None):
        wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
        amount = Decimal(amount)

        if wallet.balance < amount:
            return False, "Insufficient balance", None

        wallet.balance -= amount
        wallet.save(update_fields=["balance"])

        tx = WalletService._create_transaction(
            user=user,
            transaction_type="debit",
            amount=amount,
            note=note,
            status="pending",
            reference=reference
        )

        return True, None, tx

    @staticmethod
    @transaction.atomic
    def credit_user(user, amount, note="", reference=None):
        wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
        amount = Decimal(amount)

        wallet.balance += amount
        wallet.save(update_fields=["balance"])

        tx = WalletService._create_transaction(
            user=user,
            transaction_type="credit",
            amount=amount,
            note=note,
            status="success",
            reference=reference
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

    @staticmethod
    @transaction.atomic
    def buy_data(user, plan_id, phone):

        try:
            plan = PriceTable.objects.get(id=plan_id, active=True)
        except PriceTable.DoesNotExist:
            return {"success": False, "message": "Data plan not found"}

        if not plan.network_id or not plan.plan_code:
            return {"success": False, "message": "Invalid VTU configuration"}

        vtu_reference = generate_reference()
        while VTUTransaction.objects.filter(reference=vtu_reference).exists():
            vtu_reference = generate_reference()

        # Debit wallet
        ok, err, wallet_tx = WalletService.debit_user(
            user=user,
            amount=plan.my_price,
            note=f"{plan.network} {plan.plan_name} {phone}",
            reference=vtu_reference
        )

        if not ok:
            return {"success": False, "message": err}

        tx = VTUTransaction.objects.create(
            user=user,
            reference=vtu_reference,
            service="data",
            network=plan.network,
            phone=phone,
            amount=plan.my_price,
            status="pending"
        )

        payload = {
            "networkId": int(plan.network_id),
            "MobileNumber": phone,
            "DataPlan": int(plan.plan_code),
            "ref": vtu_reference
        }

        try:
            r = requests.post(VTU_DATA_URL, json=payload, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()

            tx.response = data

            if data.get("code") == 101:
                tx.status = "success"
                tx.save(update_fields=["status", "response"])
                WalletService.mark_success(wallet_tx)
                return {"success": True, "message": "Data sent successfully"}

            # API failure
            WalletService.mark_failed(wallet_tx)
            WalletService.credit_user(user, plan.my_price, note="Refund - Data Failed")

            tx.status = "failed"
            tx.save(update_fields=["status", "response"])

            return {"success": False, "message": "VTU Failed, wallet refunded"}

        except Exception as e:
            WalletService.mark_failed(wallet_tx)
            WalletService.credit_user(user, plan.my_price, note="Refund - Data Error")

            tx.status = "failed"
            tx.response = {"error": str(e)}
            tx.save(update_fields=["status", "response"])

            return {"success": False, "message": "Transaction error, wallet refunded"}

    @staticmethod
    @transaction.atomic
    def buy_airtime(user, network, phone, amount):

        amount = Decimal(amount)

        vtu_reference = generate_reference()
        while VTUTransaction.objects.filter(reference=vtu_reference).exists():
            vtu_reference = generate_reference()

        ok, err, wallet_tx = WalletService.debit_user(
            user=user,
            amount=amount,
            note=f"Airtime {network} {phone}",
            reference=vtu_reference
        )

        if not ok:
            return {"success": False, "message": err}

        tx = VTUTransaction.objects.create(
            user=user,
            reference=vtu_reference,
            service="airtime",
            network=network,
            phone=phone,
            amount=amount,
            status="pending"
        )

        payload = {
            "network": network,
            "phone": phone,
            "amount": int(amount),
            "ref": vtu_reference
        }

        try:
            r = requests.post(VTU_AIRTIME_URL, json=payload, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()

            tx.response = data

            if data.get("code") == 101:
                tx.status = "success"
                tx.save(update_fields=["status", "response"])
                WalletService.mark_success(wallet_tx)
                return {"success": True, "message": "Airtime sent successfully!"}

            WalletService.mark_failed(wallet_tx)
            WalletService.credit_user(user, amount, note="Refund - Airtime Failed")

            tx.status = "failed"
            tx.save(update_fields=["status", "response"])

            return {"success": False, "message": "Airtime failed, wallet refunded"}

        except Exception as e:
            WalletService.mark_failed(wallet_tx)
            WalletService.credit_user(user, amount, note="Refund - Airtime Error")

            tx.status = "failed"
            tx.response = {"error": str(e)}
            tx.save(update_fields=["status", "response"])

            return {"success": False, "message": "Airtime error, wallet refunded"}


    def get_plan_object(plan_id: int) -> Optional[PriceTable]:
        """
        Retrieve a PriceTable object by its ID.

        Args:
            plan_id (int): The ID of the price plan.

        Returns:
            PriceTable | None: The PriceTable instance if found, else None.
        """
        return PriceTable.objects.filter(id=plan_id).first()
