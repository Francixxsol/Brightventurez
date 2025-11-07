from django.contrib.auth.models import User
from core.models import Wallet

def create_wallet_async(user_id):
    """
    Create a wallet for a new user if it doesn't exist.
    This runs in the background via Django Q.
    """
    try:
        user = User.objects.get(id=user_id)
        Wallet.objects.get_or_create(user=user)
        print(f"✅ Wallet created for user: {user.username}")
    except Exception as e:
        print(f"❌ Wallet creation failed for user {user_id}: {e}")
