from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings

from .models import Wallet, Transaction, PriceTable, SellRequest, DataPlan, VirtualPlan, ProviderPlan, DataTransaction
from .forms import RegisterForm, SellDataRequestForm
from .utils.wallet_helpers import get_or_create_wallet
from .utils.vtu_mapping import VTU_DATA_CODES
from .utils import buy_data as process_data_purchase
from .utils.vtu_api import send_vtu_request

import uuid
import requests

# ---------- Home ----------
@csrf_exempt
def home(request):
    return render(request, "core/home.html")

# ---------- Register ----------
def register_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            if not Wallet.objects.filter(user=user).exists():
                Wallet.objects.create(user=user)
            messages.success(request, "Account created! You can now login.")
            return redirect("core:login")
    else:
        form = RegisterForm()
    return render(request, "core/register.html", {"form": form})

# ---------- Login ----------
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("core:dashboard")
        messages.error(request, "Invalid credentials")
    return render(request, "core/login.html")

# ---------- Logout ----------
@csrf_exempt
@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "Logged out successfully")
    return redirect("core:login")

# ---------- Dashboard ----------
@csrf_exempt
@login_required
def dashboard(request):
    wallet = Wallet.objects.get(user=request.user)
    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')[:10]
    return render(request, 'core/dashboard.html', {
        'wallet': wallet,
        'transactions': transactions
    })

# ---------- Change Password ----------
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

@csrf_exempt
@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password updated successfully!')
            return redirect('core:dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'core/change_password.html', {'form': form})

# ---------- User Transactions ----------
@csrf_exempt
@login_required
def user_transactions(request):
    transactions = Transaction.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "core/user_transactions.html", {"transactions": transactions})

# ---------- Fund Wallet ----------
@csrf_exempt
@login_required
def fund_wallet(request):
    if request.method == "POST":
        amount = int(request.POST.get("amount", 0)) * 100  # convert to kobo
        email = request.user.email
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "email": email,
            "amount": amount,
            "callback_url": request.build_absolute_uri("/payment/verify/")
        }
        res = requests.post(f"{settings.PAYSTACK_BASE_URL}/transaction/initialize", json=payload, headers=headers)
        data = res.json()
        if data.get("status"):
            return redirect(data["data"]["authorization_url"])
        messages.error(request, "Unable to initialize payment. Try again.")
    return render(request, "core/fund_wallet.html")

# ---------- Verify Payment ----------
@csrf_exempt
@login_required
def verify_payment(request):
    reference = request.GET.get("reference")
    if reference:
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        }
        res = requests.get(f"{settings.PAYSTACK_BASE_URL}/transaction/verify/{reference}", headers=headers)
        data = res.json()
        if data.get("status") and data["data"]["status"] == "success":
            amount = data["data"]["amount"] / 100  # convert back from kobo
            wallet = Wallet.objects.get(user=request.user)
            wallet.balance += amount
            wallet.save()
            Transaction.objects.create(
                user=request.user,
                amount=amount,
                type="credit",
                description=f"Wallet funded via Paystack (Ref: {reference})"
            )
            messages.success(request, f"Wallet funded with ₦{amount}")
            return redirect("core:dashboard")
    messages.error(request, "Payment verification failed")
    return redirect("core:fund_wallet")

# ---------- Sell Data ----------
@csrf_exempt
@login_required
def sell_data(request):
    if request.method == "POST":
        form = SellDataRequestForm(request.POST)
        if form.is_valid():
            sell_request = form.save(commit=False)
            sell_request.user = request.user
            sell_request.save()
            messages.success(request, "Sell request submitted. Admin will review and credit your wallet.")
            return redirect("core:sell_data")
    else:
        form = SellDataRequestForm()
    user_requests = SellRequest.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "core/sell_data.html", {"form": form, "user_requests": user_requests})

# ---------- Approve Sell Request (Admin) ----------
@csrf_exempt
@login_required
def approve_sell_request(request, request_id):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized.")
        return redirect("core:dashboard")
    sell_req = SellRequest.objects.get(id=request_id)
    if not sell_req.approved:
        sell_req.approved = True
        sell_req.save()
        wallet = Wallet.objects.get(user=sell_req.user)
        wallet.balance += sell_req.amount
        wallet.save()
        Transaction.objects.create(
            user=sell_req.user,
            amount=sell_req.amount,
            type="credit",
            description=f"Approved sell data request #{sell_req.id}"
        )
        messages.success(request, f"Sell request approved and ₦{sell_req.amount} credited to {sell_req.user.username}.")
    return redirect("core:sell_requests")

# ---------- List all sell requests (Admin) ----------
@csrf_exempt
@login_required
def sell_requests_list(request):
    if not request.user.is_staff:
        messages.error(request, "Unauthorized")
        return redirect("core:dashboard")
    requests = SellRequest.objects.all().order_by("-created_at")
    return render(request, "core/sell_requests_list.html", {"requests": requests})

# ---------- Buy Data ----------
@csrf_exempt
@login_required
def buy_data(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user, defaults={'balance': 0})
    prices = PriceTable.objects.all()
    if request.method == "POST":
        network = request.POST.get("network")
        plan_id = request.POST.get("plan")
        phone_number = request.POST.get("phone")
        if not (network and plan_id and phone_number):
            messages.error(request, "Please fill all required fields.")
            return redirect("core:buy_data")
        try:
            plan = PriceTable.objects.get(id=plan_id)
        except PriceTable.DoesNotExist:
            messages.error(request, "Selected data plan does not exist.")
            return redirect("core:buy_data")
        amount = plan.my_price
        if wallet.balance < amount:
            messages.error(request, "Insufficient wallet balance. Please fund your wallet.")
            return redirect("core:buy_data")
        ref = str(uuid.uuid4())[:8]
        wallet.balance -= amount
        wallet.save()
        txn = Transaction.objects.create(
            user=request.user,
            amount=amount,
            type="debit",
            description=f"Buying {plan.data_plan} {plan.network} data for ₦{amount}",
            reference=ref,
        )
        try:
            provider = plan.provider
            headers = {"Authorization": f"Bearer {provider.api_key}"}
            payload = {
                "network": network,
                "plan_code": plan.plan_code,
                "phone": phone_number,
                "ref": ref,
            }
            res = requests.post(f"{provider.api_base_url}/buy-data", json=payload, headers=headers, timeout=20)
            data = res.json()
            txn.provider_response = str(data)
            if res.status_code == 200 and data.get("status") in ["success", "ok"]:
                txn.status = "SUCCESS"
                txn.save()
                messages.success(request, f"Data successfully sent to {phone_number}!")
            else:
                txn.status = "FAILED"
                txn.save()
                wallet.balance += amount  # refund on failure
                wallet.save()
                messages.error(request, f"Transaction failed. Reason: {data.get('message', 'Unknown')}")
        except Exception as e:
            txn.status = "FAILED"
            txn.provider_response = str(e)
            txn.save()
            wallet.balance += amount  # refund on exception
            wallet.save()
            messages.error(request, f"An error occurred: {e}")
        return redirect("core:buy_data")
    return render(request, "core/buy_data.html", {"wallet": wallet, "prices": prices})

# ---------- Buy Airtime ----------
@csrf_exempt
@login_required
def buy_airtime(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user, defaults={'balance': 0})
    if request.method == "POST":
        network = request.POST.get("network")
        phone = request.POST.get("phone")
        amount = request.POST.get("amount")
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            messages.error(request, "Invalid amount entered.")
            return redirect("core:buy_airtime")
        if wallet.balance >= amount:
            wallet.balance -= amount
            wallet.save()
            Transaction.objects.create(
                user=request.user,
                amount=amount,
                type="debit",
                description=f"Bought ₦{amount} airtime for {phone} ({network})"
            )
            messages.success(request, f"Airtime purchase successful: ₦{amount} to {phone} ({network})")
        else:
            messages.error(request, "Insufficient wallet balance.")
        return redirect("core:buy_airtime")
    return render(request, "core/buy_airtime.html", {"wallet": wallet})

# ---------- Wallet Balance API ----------
@csrf_exempt
@login_required
def wallet_balance_api(request):
    wallet = Wallet.objects.get(user=request.user)
    data = {
        "username": request.user.username,
        "balance": float(wallet.balance),
    }
    return JsonResponse(data)

# ---------- Get Plans ----------
def get_plans(request):
    network = request.GET.get('network')
    category = request.GET.get('category')
    plans = ProviderPlan.objects.filter(network=network, category=category)
    data = [
        {
            "id": p.id,
            "name": p.plan_name,
            "size": p.size,
            "price": p.selling_price,
            "validity": p.validity
        }
        for p in plans
    ]
    return JsonResponse(data, safe=False)
