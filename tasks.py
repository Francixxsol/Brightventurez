from django_q.tasks import async_task
from core.models import Wallet
from django.contrib.auth.models import User

def create_wallet_async(user_id):
    try:
        user = User.objects.get(id=user_id)
        Wallet.objects.get_or_create(user=user)
    except Exception as e:
        print("Wallet creation failed:", e)
