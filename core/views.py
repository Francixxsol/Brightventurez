# core/views.py
import json
import uuid
from decimal import Decimal, InvalidOperation
import random
import time
import string 

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

import csv
from uuid import uuid4
from core.utils import generate_reference
from django.utils.dateparse import parse_date
from .forms import RegisterForm
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Wallet, WalletTransaction, PriceTable, SellRequest
from .models import WalletTransaction as Transaction
from .services import PaystackService, WalletService, VTUService, PROCESSING_FEE
from django.db import transaction
from .utils.helpers import parse_decimal
User = get_user_model()


# -----------------------------
# Home
# -----------------------------
@csrf_exempt
def home(request):
    return render(request, "core/home.html")

    # Get all networks dynamically
    networks_list = []

    # Get distinct networks
    distinct_networks = PriceTable.objects.values("network").distinct()

    for n in distinct_networks:
        network_name = n["network"]
        # Get all plans for this network
        plans = PriceTable.objects.filter(network=network_name).order_by("plan_type", "my_price")
        networks_list.append({
            "name": network_name,
            "plans": plans
        })

    # Get reviews if you have them
    reviews = Review.objects.all()[:5]  # adjust as needed

    return render(request, "core/home.html", {
        "networks": networks_list,
        "reviews": reviews
    })

# -----------------------------
# Register - creates wallet immediately and enqueues background job
# -----------------------------
@csrf_exempt
def register_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()

            # ✅ Ensure wallet exists immediately (synchronous)
            Wallet.objects.get_or_create(user=user)

            messages.success(request, "Account created successfully! You can now log in.")
            return redirect("core:login")
    else:
        form = RegisterForm()

    return render(request, "core/register.html", {"form": form})

# -----------------------------
# Login
# -----------------------------
@csrf_exempt
def register_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Save form but don’t commit yet
            user = form.save(commit=False)

            # Hash the password
            user.set_password(form.cleaned_data.get("password"))
            user.save()

            # Ensure wallet exists immediately
            Wallet.objects.get_or_create(user=user)

            # Authenticate and log the user in immediately
            user = authenticate(
                request,
                username=form.cleaned_data.get("username"),
                password=form.cleaned_data.get("password")
            )
            if user:
                login(request, user)

            messages.success(request, "Account created successfully! You are now logged in.")
            return redirect("core:dashboard")  # or wherever you want users to land

    else:
        form = RegisterForm()

    return render(request, "core/register.html", {"form": form})

# -----------------------------
# Logout
# -----------------------------
@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect("core:login")


# -----------------------------
# Dashboard
# -----------------------------
@login_required
def dashboard(request):
    # Get or create wallet
    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    # Fetch latest 3 transactions
    latest_txns = Transaction.objects.filter(user=request.user).order_by('-created_at')[:3]

    # Render dashboard template
    return render(request, "core/dashboard.html", {
        "wallet_balance": wallet.balance,
        "latest_txns": latest_txns,
    })

# -----------------------------
# Change password
# -----------------------------
@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password updated successfully!")
            return redirect("core:dashboard")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "core/change_password.html", {"form": form})


# -----------------------------
# Fund wallet view (class wrapper)
# -----------------------------
@method_decorator(csrf_exempt, name="dispatch")
class FundWalletView(View):
    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        return render(request, "core/fund_wallet.html", {"wallet": wallet})

    def post(self, request):
        raw_amount = request.POST.get("amount")
        naira_amount = parse_decimal(raw_amount)
        if naira_amount <= 0:
            messages.error(request, "Amount must be greater than zero.")
            return redirect("core:fund_wallet")

        metadata = {"intent": "wallet_funding", "user_id": request.user.id}
        try:
            res = PaystackService.initialize_transaction(request.user.email, naira_amount, metadata)
        except Exception as e:
            messages.error(request, f"Could not initialize payment: {e}")
            return redirect("core:fund_wallet")

        if res.get("status") and res.get("data", {}).get("authorization_url"):
            return redirect(res["data"]["authorization_url"])

        messages.error(request, "Unable to initialize payment. Try again.")
        return redirect("core:fund_wallet")


# -----------------------------
# Verify payment (redirect after user completes on Paystack)
# -----------------------------
@csrf_exempt
def verify_payment(request):
    reference = request.GET.get("reference")
    if not reference:
        messages.error(request, "Invalid payment reference.")
        return redirect("core:fund_wallet")

    # 1. Verify on Paystack
    try:
        res = PaystackService.verify_transaction(reference)
    except Exception as exc:
        messages.error(request, f"Error verifying payment: {exc}")
        return redirect("core:fund_wallet")

    data = res.get("data", {})

    if not res.get("status") or data.get("status") != "success":
        messages.error(request, "Payment verification failed.")
        return redirect("core:fund_wallet")

    # 2. Get user (session OR paystack metadata)
    metadata = data.get("metadata", {})
    user_id = metadata.get("user_id")

    if request.user.is_authenticated:
        user = request.user
    else:
        from django.contrib.auth.models import User
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            messages.error(request, "User not found for this transaction.")
            return redirect("core:fund_wallet")

    # 3. Compute amounts
    gross = Decimal(str(data["amount"] / 100))
    credited = max(gross - PROCESSING_FEE, Decimal("0"))

    # 4. Prevent double-crediting
    if Transaction.objects.filter(reference=reference).exists():
        messages.info(request, "Payment already processed.")
        return redirect("core:dashboard")

    # 5. Wallet credit
    note = f"Funded via Paystack (gross {gross}, fee {PROCESSING_FEE})"
    WalletService.credit_user(
        user=user,
        amount=credited,
        reference=reference,
        note=note
    )

    # 6. Final redirect
    messages.success(request, f"Wallet funded successfully with  ^b {credited}")
    return redirect("core:dashboard")

# -------------------- Buy Data --------------------
@method_decorator(login_required, name="dispatch")
class BuyDataView(View):

    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)

        return render(request, "core/buy_data.html", {
            "wallet": wallet
        })

    def post(self, request):
        network = request.POST.get("network", "").strip()
        plan_id = request.POST.get("plan_id", "").strip()
        phone = request.POST.get("phone", "").strip()

        # 1. Basic validation
        if not all([network, plan_id, phone]):
            messages.error(request, "All fields are required.")
            return redirect("core:buy_data")

        # 2. Get plan
        plan = PriceTable.objects.filter(
            id=plan_id,
            network=network
        ).first()

        if not plan:
            messages.error(request, "Invalid plan selected.")
            return redirect("core:buy_data")

        amount = plan.my_price

        # 3. Call Service Layer (Service handles debit + VTU + refund logic)
        response = VTUService.buy_data(
            user=request.user,
            plan_network=plan.network,
            plan_code=plan.plan_code,
            phone=phone,
            amount=amount
        )

        # 4. Handle response
        if not response.get("success"):
            messages.error(
                request,
                response.get("message", "Transaction failed")
            )
            return redirect("core:buy_data")

        messages.success(
            request,
            f"{plan.plan_name} successfully sent to {phone}"
        )

        return redirect("core:buy_data")

#-----------------
#buy airtime
#-----------------
@method_decorator(login_required, name="dispatch")
class BuyAirtimeView(View):

    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        return render(request, "core/buy_airtime.html", {"wallet": wallet})

    @transaction.atomic
    def post(self, request):
        network = request.POST.get("network")
        phone = request.POST.get("phone")
        amount = request.POST.get("amount")

        if not all([network, phone, amount]):
            messages.error(request, "All fields are required.")
            return redirect("core:buy_airtime")

        try:
            amount = Decimal(amount)
            if amount <= 0:
                raise ValueError
        except:
            messages.error(request, "Invalid airtime amount.")
            return redirect("core:buy_airtime")

        # ✅ Check Wallet Balance FIRST
        wallet, _ = Wallet.objects.get_or_create(user=request.user)

        if wallet.balance < amount:
            messages.error(request, "Insufficient wallet balance. Please fund your wallet.")
            return redirect("core:fund_wallet")

        # Call VTUService
        response = VTUService.buy_airtime(
            user=request.user,
            network=network,
            phone=phone,
            amount=amount
        )

        if not response.get("success"):
            messages.error(request, response.get("message", "Airtime purchase failed"))
        else:
            messages.success(request, f"Airtime {amount} successfully sent to {phone}")

        return redirect("core:buy_airtime")


# -----------------------------
# Paystack webhook (robust)
# -----------------------------
@csrf_exempt
def paystack_webhook(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid method")

    signature = request.headers.get("X-Paystack-Signature") or request.META.get("HTTP_X_PAYSTACK_SIGNATURE")
    raw = request.body or b""
    if not PaystackService.verify_signature(raw, signature):
        return JsonResponse({"error": "invalid signature"}, status=401)

    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as e:
        return JsonResponse({"error": "invalid json", "detail": str(e)}, status=400)

    event = payload.get("event")
    if event != "charge.success":
        return JsonResponse({"status": "ignored"}, status=200)

    data = payload.get("data", {})
    reference = data.get("reference")
    amount_kobo = int(data.get("amount", 0))
    email = data.get("customer", {}).get("email")
    if not reference or not email:
        return JsonResponse({"error": "incomplete data"}, status=400)

    # idempotency
    if Transaction.objects.filter(reference=reference).exists():
        return JsonResponse({"status": "already_processed"}, status=200)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return JsonResponse({"error": "user not found"}, status=404)

    amount_naira = Decimal(amount_kobo) / Decimal(100)

    # extract subaccount split info robustly
    split_payload = data.get("split") or data.get("authorization", {}).get("split") or {}
    subaccounts = split_payload.get("subaccounts") or data.get("subaccounts") or []

    provider_total_received = Decimal("0.00")
    subaccounts_info = []

    if subaccounts and isinstance(subaccounts, list):
        for s in subaccounts:
            sub = {"subaccount": s.get("subaccount"), "share": s.get("share"), "amount": None}
            if s.get("amount") is not None:
                try:
                    amt_kobo = int(s.get("amount"))
                    amt_naira = Decimal(amt_kobo) / Decimal(100)
                    sub["amount"] = amt_naira
                    provider_total_received += amt_naira
                except Exception:
                    sub["amount"] = None
            subaccounts_info.append(sub)

    # if provider amounts not present, compute by share percentages
    if provider_total_received == Decimal("0.00") and subaccounts_info:
        total_provider_pct = sum([int(s.get("share") or 0) for s in subaccounts_info])
        if total_provider_pct > 0:
            for s in subaccounts_info:
                share = Decimal(s.get("share") or 0)
                amt = (share / Decimal(100)) * amount_naira
                amt = amt.quantize(Decimal("0.01"))
                s["amount"] = amt
                provider_total_received += amt

    platform_received = (amount_naira - provider_total_received).quantize(Decimal("0.01")) if provider_total_received > 0 else amount_naira

    try:
        credited_amount = platform_received if platform_received is not None else Decimal("0.00")
        WalletService.credit_user(user, credited_amount, reference=reference,
                                  note=f"Webhook credit (gross ₦{amount_naira}, platform ₦{credited_amount})")

        # store a log transaction with provider receipts info
        Transaction.objects.create(
            user=user,
            transaction_type="Webhook Split Log",
            amount=provider_total_received,
            status="Successful",
            reference=f"split-{reference}",
            description=json.dumps({"subaccounts": subaccounts_info}),
        )
    except Exception as e:
        return JsonResponse({"error": f"credit failed: {str(e)}"}, status=500)

    # If the webhook metadata indicated an auto_purchase intent, attempt to finish it:
    metadata = data.get("metadata") or {}
    if metadata.get("intent") == "auto_purchase":
        # We schedule an async job to finish the auto_purchase (safer than blocking webhook)
        async_task("core.tasks.process_auto_purchase_from_metadata", metadata, reference)

    return JsonResponse({"status": "success", "credited": float(credited_amount), "provider_received": float(provider_total_received)})

@login_required
def user_transactions(request):
    """
    List user transactions with optional search, date filtering, pagination,
    and CSV export.
    """
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = Transaction.objects.filter(user=request.user).order_by("-created_at")

    # Search
    query = request.GET.get("q", "")
    if query:
        transactions = transactions.filter(
            Q(reference__icontains=query) |
            Q(transaction_type__icontains=query) |
            Q(status__icontains=query)
        )

    # Date filtering
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    if start_date:
        sd = parse_date(start_date)
        if sd:
            transactions = transactions.filter(created_at__date__gte=sd)
    if end_date:
        ed = parse_date(end_date)
        if ed:
            transactions = transactions.filter(created_at__date__lte=ed)

    # CSV export
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
        writer = csv.writer(response)
        writer.writerow(["Reference", "Type", "Amount", "Status", "Date"])
        for tx in transactions:
            writer.writerow([
                tx.reference,
                tx.transaction_type,
                float(tx.amount),
                tx.status,
                tx.created_at.strftime("%Y-%m-%d %H:%M")
            ])
        return response

    # Pagination
    paginator = Paginator(transactions, 20)  # 20 per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "core/user_transactions.html", {
        "wallet": wallet,
        "transactions": page_obj,
        "query": query,
        "start_date": start_date,
        "end_date": end_date,
    })

@login_required
def wallet_balance_api(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    return JsonResponse({"balance": float(wallet.balance or 0)})

@login_required
def sell_data_view(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    return render(request, "core/sell_data.html", {"wallet": wallet})

@login_required
def get_plans(request):
    network = request.GET.get("network", "").strip()
    data_type = request.GET.get("data_type", "").strip().lower()

    plans = []

    if network and data_type:
        qs = PriceTable.objects.filter(
            network=network,
            plan_type__iexact=data_type
        ).order_by("my_price")

        plans = [
            {
                "id": plan.id,
                "plan_name": plan.plan_name,
                "duration": getattr(plan, "duration", ""),
                "my_price": str(plan.my_price),  # safer than float
                "api_code": getattr(plan, "plan_code", plan.plan_name)
            }
            for plan in qs
        ]

    return JsonResponse({"plans": plans})

def generate_reference(length=12):
    """
    Generates a random alphanumeric reference for transactions.
    """
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def about(request):
    return render(request, "core/about.html")

def services(request):
    return render(request, "core/services.html")

def contact(request):
    return render(request, "core/contact.html")

def plans(request):
    # Full plans data (only "Our Price")
    networks = [
        {
            "name": "9Mobile",
            "color": "#28a745",  # Greenish highlight for 9Mobile
            "plans": [
                {"plan_type": "CG", "plan_name": "1GB (CG) - 30days", "our_price": 380},
                {"plan_type": "CG", "plan_name": "1.5GB (CG) - 30days", "our_price": 500},
                {"plan_type": "CG", "plan_name": "2GB (CG) - 30days", "our_price": 680},
                {"plan_type": "CG", "plan_name": "3GB (CG) - 30days", "our_price": 950},
                {"plan_type": "CG", "plan_name": "4GB (CG) - 30days", "our_price": 1220},
                {"plan_type": "CG", "plan_name": "5GB (CG) - 30days", "our_price": 1520},
                {"plan_type": "CG", "plan_name": "10GB (CG) - 30days", "our_price": 2950},
                {"plan_type": "SME", "plan_name": "1.6GB (SME) - 30days", "our_price": 580},
                {"plan_type": "SME", "plan_name": "2.3GB (SME) - 30days", "our_price": 780},
                {"plan_type": "SME", "plan_name": "3.3GB (SME) - 30days", "our_price": 1080},
                {"plan_type": "SME", "plan_name": "4.5GB (SME) - 30days", "our_price": 1780},
                {"plan_type": "SME", "plan_name": "5GB (SME) - 30days", "our_price": 1880},
                {"plan_type": "SME", "plan_name": "10GB (SME) - 30days", "our_price": 3150},
            ]
        },
        {
            "name": "Glo",
            "color": "#ffc107",  # Yellow highlight for Glo
            "plans": [
                {"plan_type": "CG", "plan_name": "500MB (CG) - 30days", "our_price": 315},
                {"plan_type": "CG", "plan_name": "1GB (CG) - 30days", "our_price": 500},
                {"plan_type": "CG", "plan_name": "2GB (CG) - 30days", "our_price": 950},
                {"plan_type": "CG", "plan_name": "3GB (CG) - 30days", "our_price": 1370},
                {"plan_type": "CG", "plan_name": "5GB (CG) - 30days", "our_price": 2230},
                {"plan_type": "CG", "plan_name": "10GB (CG) - 30days", "our_price": 4400},
                {"plan_type": "SME", "plan_name": "500MB (SME) - 30days", "our_price": 340},
                {"plan_type": "SME", "plan_name": "1GB (SME) - 30days", "our_price": 580},
                {"plan_type": "SME", "plan_name": "2GB (SME) - 30days", "our_price": 1070},
                {"plan_type": "SME", "plan_name": "3GB (SME) - 30days", "our_price": 1580},
                {"plan_type": "SME", "plan_name": "10GB (SME) - 30days", "our_price": 5000},
                {"plan_type": "Special", "plan_name": "1GB (Special) - 3days", "our_price": 380},
                {"plan_type": "Special", "plan_name": "1GB (Special) - 7days", "our_price": 450},
                {"plan_type": "Special", "plan_name": "3GB (Special) - 7days", "our_price": 1100},
                {"plan_type": "Special", "plan_name": "5GB (Special) - 7days", "our_price": 1810},
            ]
        },
        {
            "name": "MTN",
            "color": "#007bff",  # Blue highlight for MTN
            "plans": [
                {"plan_type": "SME", "plan_name": "500MB (SME) - 30days", "our_price": 480},
                {"plan_type": "SME", "plan_name": "1GB (SME) - 7days", "our_price": 580},
                {"plan_type": "SME", "plan_name": "1GB (SME) - 30days", "our_price": 645},
                {"plan_type": "SME", "plan_name": "2GB (SME) - 30days", "our_price": 1220},
                {"plan_type": "SME", "plan_name": "3GB (SME) - 30days", "our_price": 1810},
                {"plan_type": "SME", "plan_name": "5GB (SME) - 30days", "our_price": 2920},
                {"plan_type": "SME", "plan_name": "20GB (SME) - 7days", "our_price": 11500},
                {"plan_type": "Special", "plan_name": "1GB DAILY", "our_price": 245},
                {"plan_type": "Special", "plan_name": "500MB (Special) - 7days", "our_price": 450},
                {"plan_type": "Special", "plan_name": "2.5GB DAILY", "our_price": 630},
            ]
        },
        {
            "name": "Airtel",
            "color": "#dc3545",  # Red highlight for Airtel
            "plans": [
                {"plan_type": "SME", "plan_name": "1GB Weekly Plan (7 Days)", "our_price": 870},
                {"plan_type": "SME", "plan_name": "2GB Monthly Plan", "our_price": 1580},
                {"plan_type": "SME", "plan_name": "3GB Binge Plan", "our_price": 1080},
                {"plan_type": "SME", "plan_name": "8.5GB Weekly Plan", "our_price": 3080},
                {"plan_type": "Special", "plan_name": "250MB Night Plan", "our_price": 50},
                {"plan_type": "Special", "plan_name": "200MB Social Plan", "our_price": 100},
                {"plan_type": "Special", "plan_name": "3GB Monthly Plan", "our_price": 2080},
            ]
        },
    ]
    return render(request, "core/plans.html", {"networks": networks})
