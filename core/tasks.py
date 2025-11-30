# core/tasks.py
import json
from decimal import Decimal
from django.contrib.auth import get_user_model
from .models import Wallet, Transaction
from .services import VTUService, WalletService
from django.utils import timezone

User = get_user_model()

def post_signup_tasks(user_id):
    """
    Runs in background after signup.
    Keep idempotent and minimal.
    """
    try:
        user = User.objects.get(id=user_id)
        Wallet.objects.get_or_create(user=user)
        # Add any welcome credit or send email here (use external mailer or another task)
    except User.DoesNotExist:
        return False
    return True


def process_auto_purchase_from_metadata(metadata, paystack_reference):
    """
    Called from webhook via async_task. metadata is the Paystack metadata dict.
    Attempts to complete an auto_purchase that was initiated at checkout.
    """
    try:
        user_id = metadata.get("user_id")
        user = User.objects.get(id=user_id)
    except Exception:
        return {"error": "user_not_found"}

    purchase_type = metadata.get("purchase_type")
    if purchase_type == "data":
        plan_id = metadata.get("plan_id")
        phone = metadata.get("phone")
        plan_obj = None
        from .models import PriceTable
        plan_obj = PriceTable.objects.filter(id=plan_id).first()
        amount = Decimal(str(metadata.get("amount", "0")))
        # credit user wallet with platform portion was already done by webhook.
        # attempt to debit and call provider
        from .services import WalletService, VTUService
        wallet, _ = Wallet.objects.get_or_create(user=user)
        if (wallet.balance or Decimal("0.00")) >= amount:
            ok, tx = WalletService.debit_user(user, amount, reference=paystack_reference, note="Auto purchase post-webhook")
            if ok:
                provider_resp = VTUService.buy_data(plan_obj.api_code or plan_obj.plan_name, metadata.get("phone"), plan_obj.api_code or plan_obj.plan_name)
                return {"status": "provider_called", "response": provider_resp}
            else:
                return {"error": "insufficient_balance_after_webhook"}
        else:
            return {"error": "not_enough_after_webhook"}

    if purchase_type == "airtime":
        phone = metadata.get("phone")
        amount = Decimal(str(metadata.get("amount", "0")))
        from .services import WalletService, VTUService
        wallet, _ = Wallet.objects.get_or_create(user=user)
        if (wallet.balance or Decimal("0.00")) >= amount:
            ok, tx = WalletService.debit_user(user, amount, reference=paystack_reference, note="Auto airtime post-webhook")
            if ok:
                provider_resp = VTUService.buy_airtime(metadata.get("network", ""), phone, amount)
                return {"status": "provider_called", "response": provider_resp}
            else:
                return {"error": "insufficient_balance_after_webhook"}
        return {"error": "not_enough_after_webhook"}

    return {"error": "unknown_purchase_type"}
