# core/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "core"

urlpatterns = [
    # Home & Auth
    path("", views.home, name="home"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("change-password/", views.change_password, name="change_password"),

    # Transactions
    path("transactions/", views.user_transactions, name="user_transactions"),

    # Fund & verify wallet
    path("fund-wallet/", views.FundWalletView.as_view(), name="fund_wallet"),
    path("payment/verify/", views.verify_payment, name="verify_payment"),

    # Buy data/airtime
    path("buy-data/", views.BuyDataView.as_view(), name="buy_data"),
    path("buy-airtime/", views.BuyAirtimeView.as_view(), name="buy_airtime"),
# Add under buy data/airtime
path("sell-data/", views.sell_data_view, name="sell_data"),		
    # AJAX endpoints
    path("get_plans/", views.get_plans, name="get_plans"),
    path("api/wallet-balance/", views.wallet_balance_api, name="wallet_balance_api"),  # <-- added

    # Webhook
    path("paystack/webhook/", views.paystack_webhook, name="paystack_webhook"),

    # Password reset using built-in views
    path(
        "password_reset/",
        auth_views.PasswordResetView.as_view(template_name="core/password_reset.html"),
        name="password_reset"
    ),
    path(
        "password_reset_done/",
        auth_views.PasswordResetDoneView.as_view(template_name="core/password_reset_done.html"),
        name="password_reset_done"
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(template_name="core/password_reset_confirm.html"),
        name="password_reset_confirm"
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(template_name="core/password_reset_complete.html"),
        name="password_reset_complete"
    ),
]
