from .models import Wallet, PriceTable

def global_context(request):
    wallet_balance = 0
    if request.user.is_authenticated:
        try:
            wallet_balance = Wallet.objects.get(user=request.user).balance
        except Wallet.DoesNotExist:
            wallet_balance = 0

    # dummy reviews (later fetch from DB if needed)
    reviews = [
        {"name": "Blessing", "text": "Cheapest data ever!"},
        {"name": "Chidi", "text": "Fast VTU top-up in seconds."},
        {"name": "Kemi", "text": "I sold my data, cash came instantly."},
        {"name": "Uche", "text": "Bright Venturez is 🔥🔥🔥"},
    ]

    return {
        "wallet_balance": wallet_balance,
        "reviews": reviews,
    }
