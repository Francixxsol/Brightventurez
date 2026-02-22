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
    {"name": "Blessing", "text": "Cheapest data ever! My wallet is finally breathing 😅", "rating": 5},
    {"name": "Chidi", "text": "Fast VTU top-up in seconds. I blinked and it was done.", "rating": 5},
    {"name": "Kemi", "text": "I sold my data and the cash landed instantly. No stories!", "rating": 5},
    {"name": "Uche", "text": "Bright Venturez is reliable and trustworthy. 10/10 honestly.", "rating": 5},
    {"name": "Tosin", "text": "Smooth transactions, zero delay. Even my bank app should learn from this.", "rating": 5},
    {"name": "Aisha", "text": "Very secure platform. I feel safe using it every time.", "rating": 5},
    {"name": "Emeka", "text": "Customer support responds fast. I wasn’t even done worrying 😄", "rating": 5},
    {"name": "Halima", "text": "Affordable prices and instant delivery. My data arrives before I refresh the page.", "rating": 5},
    {"name": "David", "text": "Best VTU platform I’ve used this year. No cap.", "rating": 5},
    {"name": "Daniel O.", "text": "Professional service with transparent pricing. Very impressive system.", "rating": 5},
    {"name": "Esther A.", "text": "Stable even during peak hours. That consistency is rare.", "rating": 5},
    {"name": "Tobi", "text": "Used it at 2am and it still delivered instantly 🔥 Night owls approved.", "rating": 5},
    {"name": "Amaka", "text": "Finally a VTU platform that doesn’t stress me. My BP says thank you.", "rating": 5},
    {"name": "Samuel", "text": "Honest pricing and dependable service. Exactly what they promise.", "rating": 5},
    {"name": "Mercy", "text": "They deliver exactly what they promise. No suspense, just results.", "rating": 5},
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
