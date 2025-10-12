import requests
from .models import Provider, ProviderPlan

def fetch_provider_plans(provider_id):
    provider = Provider.objects.get(id=provider_id)
    headers = {"Authorization": f"Bearer {provider.api_key}"}
    
    # Example: adjust endpoint path depending on your provider
    response = requests.get(f"{provider.api_base_url}/data-plans", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        for plan in data.get('plans', []):
            ProviderPlan.objects.update_or_create(
                provider=provider,
                plan_code=plan['code'],
                defaults={
                    'plan_name': plan['name'],
                    'network': plan['network'],
                    'size_mb': plan['size'],
                    'price': plan['price'],
                }
            )
        return True
    return False

import uuid
import requests
from .models import VirtualPlan, ProviderPlan, Provider, DataTransaction

def buy_data(user, network, plan_id, phone_number, plan_type="VIRTUAL"):
    ref = str(uuid.uuid4())[:8]  # short unique ref

    if plan_type == "VIRTUAL":
        plan = VirtualPlan.objects.get(id=plan_id)
        amount = plan.selling_price
        provider_plan = plan.linked_provider_plan

    else:
        plan = ProviderPlan.objects.get(id=plan_id)
        amount = plan.price
        provider_plan = plan

    # create transaction
    txn = DataTransaction.objects.create(
        user=user,
        network=network,
        phone_number=phone_number,
        plan_type=plan_type,
        plan_name=f"{network} {plan.size_mb}MB",
        amount=amount,
        reference=ref,
    )

    # --- provider API call ---
    try:
        provider = provider_plan.provider
        headers = {"Authorization": f"Bearer {provider.api_key}"}
        payload = {
            "network": network,
            "plan_code": provider_plan.plan_code,
            "phone": phone_number,
            "ref": ref,
        }

        res = requests.post(f"{provider.api_base_url}/buy-data", json=payload, headers=headers, timeout=20)
        data = res.json()

        txn.provider_response = str(data)

        if res.status_code == 200 and data.get("status") in ["success", "ok"]:
            txn.status = "SUCCESS"
        else:
            txn.status = "FAILED"

        txn.save()
        return txn

    except Exception as e:
        txn.status = "FAILED"
        txn.provider_response = str(e)
        txn.save()
        return txn

from .models import Wallet

def get_or_create_wallet(user):
    wallet, created = Wallet.objects.get_or_create(user=user, defaults={'balance': 0})
    return wallet
