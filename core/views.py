# core/views.py
import json
import uuid
from decimal import Decimal, InvalidOperation

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

from django_q.tasks import async_task
import csv
from django.utils.dateparse import parse_date
from .forms import RegisterForm
from django.core.paginator import Paginator
from django.db.models import Q
from .models import PriceTable, Wallet, Transaction, SellRequest
from .services import PaystackService, WalletService, VTUService, PROCESSING_FEE
from .utils.helpers import parse_decimal
User = get_user_model()


# -----------------------------
# Home
# -----------------------------
@csrf_exempt
def home(request):
    return render(request, "core/home.html")


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
            # ensure wallet exists immediately (synchronous)
            Wallet.objects.get_or_create(user=user)

            # enqueue any heavy post-signup tasks (welcome email, analytics, etc.)
            async_task("core.tasks.post_signup_tasks", user.id, hook=None)

            messages.success(request, "Account created successfully! You can now log in.")
            return redirect("core:login")
    else:
        form = RegisterForm()

    return render(request, "core/register.html", {"form": form})


# -----------------------------
# Login
# -----------------------------
@csrf_exempt
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            # ensure wallet exists on login too (defensive)
            Wallet.objects.get_or_create(user=user)
            return redirect("core:dashboard")
        messages.error(request, "Invalid username or password.")
    return render(request, "core/login.html")


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
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = Transaction.objects.filter(user=request.user).order_by("-created_at")[:25]
    return render(request, "core/dashboard.html", {"wallet": wallet, "transactions": transactions})


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
@login_required
def verify_payment(request):
    reference = request.GET.get("reference")
    if not reference:
        messages.error(request, "Invalid payment reference.")
        return redirect("core:fund_wallet")

    try:
        res = PaystackService.verify_transaction(reference)
    except Exception as e:
        messages.error(request, f"Error verifying payment: {e}")
        return redirect("core:fund_wallet")

    if res.get("status") and res.get("data", {}).get("status") == "success":
        amount_naira = Decimal(str(res["data"]["amount"] / 100))
        credited = max(amount_naira - PROCESSING_FEE, Decimal("0.00"))

        # idempotency: ensure we haven't processed this reference before
        if Transaction.objects.filter(reference=reference).exists():
            messages.info(request, "Payment already processed.")
            return redirect("core:dashboard")

        WalletService.credit_user(request.user, credited, reference=reference,
                                  note=f"Funded via Paystack (gross ₦{amount_naira}, fee ₦{PROCESSING_FEE})")
        messages.success(request, f"Wallet funded successfully with ₦{credited}")
        return redirect("core:dashboard")

    messages.error(request, "Payment verification failed.")
    return redirect("core:fund_wallet")


# -----------------------------
# Buy data view (class)
# -----------------------------
@method_decorator(csrf_exempt, name="dispatch")
class BuyDataView(View):
    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        plans = PriceTable.objects.all()
        return render(request, "core/buy_data.html", {"wallet": wallet, "plans": plans})

    def post(self, request):
        network = request.POST.get("network")
        plan_id = request.POST.get("plan_id")
        phone = request.POST.get("phone")

        if not all([network, plan_id, phone]):
            messages.error(request, "All fields are required.")
            return redirect("core:buy_data")

        plan = VTUService.get_plan_object(plan_id)
        if not plan:
            messages.error(request, "Plan not found.")
            return redirect("core:buy_data")

        amount = Decimal(str(plan.my_price or plan.vtu_cost or 0))
        wallet, _ = Wallet.objects.get_or_create(user=request.user)

        # If user has enough in platform wallet — debit & call provider
        if (wallet.balance or Decimal("0.00")) >= amount:
            ok, tx = WalletService.debit_user(request.user, amount, reference=str(uuid.uuid4())[:12],
                                             note=f"Auto data purchase: {plan.plan_name}")
            if not ok:
                messages.error(request, "Insufficient wallet balance.")
                return redirect("core:buy_data")

            provider_resp = VTUService.buy_data(plan.api_code or plan.plan_name, phone, plan.api_code or plan.plan_name)
            success = False
            if isinstance(provider_resp, dict):
                if provider_resp.get("status") in ("success", True) or provider_resp.get("code") in (101, "101"):
                    success = True

            if success:
                messages.success(request, f"{network} data plan {plan.plan_name} sent to {phone} successfully!")
            else:
                messages.error(request, f"VTU API Error: {provider_resp}")
            return redirect("core:buy_data")

        # Wallet insufficient => initialize Paystack checkout with dynamic split (auto-purchase intent)
        metadata = {
            "intent": "auto_purchase",
            "user_id": request.user.id,
            "purchase_type": "data",
            "plan_id": plan.id,
            "plan_name": plan.plan_name,
            "phone": phone,
            "amount": str(amount)
        }
        try:
            res = PaystackService.initialize_transaction(request.user.email, amount, metadata)
        except Exception as e:
            messages.error(request, f"Could not initialize payment: {e}")
            return redirect("core:buy_data")

        if res.get("status") and res.get("data", {}).get("authorization_url"):
            return redirect(res["data"]["authorization_url"])

        messages.error(request, "Unable to initialize payment. Try again.")
        return redirect("core:buy_data")


# -----------------------------
# Buy airtime view (class)
# -----------------------------
@method_decorator(csrf_exempt, name="dispatch")
class BuyAirtimeView(View):
    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        return render(request, "core/buy_airtime.html", {"wallet": wallet})

    def post(self, request):
        network = request.POST.get("network")
        phone = request.POST.get("phone")
        raw_amount = request.POST.get("amount")
        try:
            amount = Decimal(str(raw_amount))
        except (InvalidOperation, TypeError):
            messages.error(request, "Invalid amount")
            return redirect("core:buy_airtime")

        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        if (wallet.balance or Decimal("0.00")) >= amount:
            ok, tx = WalletService.debit_user(request.user, amount, reference=str(uuid.uuid4())[:12],
                                             note=f"Airtime {network} to {phone}")
            if not ok:
                messages.error(request, "Insufficient wallet balance.")
                return redirect("core:buy_airtime")

            provider_resp = VTUService.buy_airtime(network, phone, amount)
            success = False
            if isinstance(provider_resp, dict):
                if provider_resp.get("status") in ("success", True) or provider_resp.get("code") in (101, "101"):
                    success = True

            if success:
                messages.success(request, f"Airtime ₦{amount} sent to {phone} ({network})")
            else:
                messages.error(request, f"VTU API Error: {provider_resp}")
            return redirect("core:buy_airtime")

        # insufficient wallet -> init Paystack dynamic-split checkout
        metadata = {
            "intent": "auto_purchase",
            "user_id": request.user.id,
            "purchase_type": "airtime",
            "phone": phone,
            "amount": str(amount)
        }
        try:
            res = PaystackService.initialize_transaction(request.user.email, amount, metadata)
        except Exception as e:
            messages.error(request, f"Could not initialize payment: {e}")
            return redirect("core:buy_airtime")

        if res.get("status") and res.get("data", {}).get("authorization_url"):
            return redirect(res["data"]["authorization_url"])

        messages.error(request, "Unable to initialize payment. Try again.")
        return redirect("core:buy_airtime")


# -----------------------------
# AJAX: get plans
# -----------------------------
@csrf_exempt
def get_plans(request):
    network = request.GET.get("network")
    data_type = request.GET.get("data_type")
    if not network or not data_type:
        return JsonResponse({"error": "network and data_type required"}, status=400)

    qs = PriceTable.objects.filter(network=network, plan_type=data_type).values(
        "id", "plan_name", "vtu_cost", "my_price", "duration"
    )
    plans = []
    for p in qs:
        size = ""
        for token in (p.get("plan_name") or "").split():
            if "GB" in token or "MB" in token:
                size = token
                break
        plans.append({
            "id": p["id"],
            "plan_name": p["plan_name"],
            "size": size,
            "duration": p.get("duration") or "",
            "selling_price": float(p.get("my_price") or 0),
        })
    return JsonResponse({"plans": plans})


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
