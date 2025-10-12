from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    # Home
    path("", views.home, name="home"),

    # Auth
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("change-password/", views.change_password, name="change_password"),

    # Dashboard & Transactions
    path("dashboard/", views.dashboard, name="dashboard"),
    path("transactions/", views.user_transactions, name="user_transactions"),

    # Wallet Funding
    path("fund-wallet/", views.fund_wallet, name="fund_wallet"),
    path("payment/verify/", views.verify_payment, name="verify_payment"),

    # VTU Services
    path("buy-airtime/", views.buy_airtime, name="buy_airtime"),
    path("buy-data/", views.buy_data, name="buy_data"),

    # Sell Data
    path("sell-data/", views.sell_data, name="sell_data"),
    path("sell-requests/", views.sell_requests_list, name="sell_requests"),

    # Wallet API
    path("api/wallet/", views.wallet_balance_api, name="wallet_balance_api"),

    # Data Plans API
    path("get_plans/", views.get_plans, name="get_plans"),
]
