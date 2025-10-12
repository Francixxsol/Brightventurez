
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
        {"name": "Uche", "text": "Bright Venturez is  ^=^t  ^=^t  ^=^t "},
    ]

    return {
        "wallet_balance": wallet_balance,
        "reviews": reviews,
    }

# core/context_processors.py

def nav_links(request):
    """
    Returns a list of navigation links available across the site.
    """
    links = [
        {"title": "Home", "url_name": "home"},
        {"title": "Buy Data", "url_name": "buy_data"},
        {"title": "Airtime", "url_name": "airtime"},
        {"title": "Transactions", "url_name": "transactions"},
    ]

    # Show admin link only if user is staff
    if request.user.is_authenticated and request.user.is_staff:
        links.append({"title": "Admin", "url_name": "admin:index"})

    return {"nav_links": links}
