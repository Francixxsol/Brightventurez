from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.forms import PasswordChangeForm
from decimal import Decimal
from .models import Wallet, Transaction, PriceTable, SellRequest
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.core.cache import cache  # ✅ add here, not inside any function
from .models import PriceTable, Wallet
from .forms import RegisterForm
import uuid
import requests


# ------------------------------
# Home
# ------------------------------
@csrf_exempt
def home(request):
    return render(request, "core/home.html")


# ------------------------------
# Register
# ------------------------------
@csrf_exempt
def register_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()

            # 🔹 Run wallet creation in the background instead of blocking here
            from django_q.tasks import async_task
            from core.tasks import create_wallet_async
            async_task(create_wallet_async, user.id)

            messages.success(request, "Account created successfully! You can now log in.")
            return redirect("core:login")

    else:
        form = RegisterForm()

    return render(request, "core/register.html", {"form": form})

# ------------------------------
# Login
# ------------------------------
from django_q.tasks import async_task
from core.tasks import create_wallet_async
@csrf_exempt
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            # Run wallet creation asynchronously
            async_task(create_wallet_async, user.id)
            return redirect("core:dashboard")
        messages.error(request, "Invalid username or password.")
    return render(request, "core/login.html")

# ------------------------------
# Logout
# ------------------------------
@csrf_exempt
@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You’ve been logged out successfully.")
    return redirect("core:login")


# ------------------------------
# Dashboard
# ------------------------------
@csrf_exempt
@login_required
def dashboard(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')[:10]
    return render(request, 'core/dashboard.html', {
        'wallet': wallet,
        'transactions': transactions
    })


# ------------------------------
# Change Password
# ------------------------------
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


# ------------------------------
# Transactions
# ------------------------------
@csrf_exempt
@login_required
def user_transactions(request):
    transactions = Transaction.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "core/user_transactions.html", {"transactions": transactions})


# ------------------------------
# Fund Wallet (Paystack)
# ------------------------------
@csrf_exempt
@login_required
def fund_wallet(request):
    if request.method == "POST":
        amount = int(request.POST.get("amount", 0)) * 100  # kobo
        email = request.user.email
        payload = {
            "email": email,
            "amount": amount,
            "callback_url": request.build_absolute_uri("/payment/verify/"),
        }
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        res = requests.post(f"{settings.PAYSTACK_BASE_URL}/transaction/initialize", json=payload, headers=headers)
        data = res.json()
        if data.get("status"):
            return redirect(data["data"]["authorization_url"])
        messages.error(request, "Unable to initialize payment.")
    return render(request, "core/fund_wallet.html")


# ------------------------------
# Verify Payment (Paystack)
# ------------------------------
@csrf_exempt
@login_required
def verify_payment(request):
    reference = request.GET.get("reference")
    if reference:
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"
        }

        try:
            res = requests.get(
                f"{settings.PAYSTACK_BASE_URL}/transaction/verify/{reference}",
                headers=headers
            )
            data = res.json()

            if data.get("status") and data["data"]["status"] == "success":
                amount = data["data"]["amount"] / 100  # Paystack returns kobo, so divide by 100
                amount = Decimal(str(amount))  # Convert to Decimal

                wallet, _ = Wallet.objects.get_or_create(user=request.user)
                wallet.balance += amount
                wallet.save()

                Transaction.objects.create(
                    user=request.user,
                    transaction_type="Wallet Funding",
                    amount=amount,
                    status="Successful",
                    reference=reference,
                )

                messages.success(request, f"Wallet funded successfully with ₦{amount}")
                return redirect("core:dashboard")

            else:
                messages.error(request, "Payment verification failed.")
                return redirect("core:fund_wallet")

        except Exception as e:
            messages.error(request, f"Error verifying payment: {e}")
            return redirect("core:fund_wallet")

    messages.error(request, "Invalid payment reference.")
    return redirect("core:fund_wallet")

# ------------------------------
# Sell Data Request
# ------------------------------
@csrf_exempt
@login_required
def sell_data(request):
    if request.method == "POST":
        network = request.POST.get("network")
        amount = request.POST.get("amount")
        phone_number = request.POST.get("phone")
        if not all([network, amount, phone_number]):
            messages.error(request, "All fields are required.")
            return redirect("core:sell_data")
        SellRequest.objects.create(
            user=request.user,
            network=network,
            amount=amount,
            phone_number=phone_number,
        )
        messages.success(request, "Sell request submitted successfully.")
        return redirect("core:sell_data")

    user_requests = SellRequest.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "core/sell_data.html", {"user_requests": user_requests})


# ------------------------------
# Admin: Approve Sell Request
# ------------------------------
@csrf_exempt
@login_required
def approve_sell_request(request, request_id):
    if not request.user.is_staff:
        messages.error(request, "Unauthorized action.")
        return redirect("core:dashboard")

    sell_req = get_object_or_404(SellRequest, id=request_id)
    if sell_req.status != "Approved":
        sell_req.status = "Approved"
        sell_req.save()
        wallet, _ = Wallet.objects.get_or_create(user=sell_req.user)
        wallet.balance += sell_req.amount
        wallet.save()
        Transaction.objects.create(
            user=sell_req.user,
            transaction_type="Wallet Funding",
            amount=sell_req.amount,
            status="Successful",
            reference=str(uuid.uuid4())[:8],
        )
        messages.success(request, f"Request approved and ₦{sell_req.amount} credited to {sell_req.user.username}.")
    return redirect("core:sell_requests_list")


# ------------------------------
# Admin: Sell Requests List
# ------------------------------
@csrf_exempt
@login_required
def sell_requests_list(request):
    if not request.user.is_staff:
        messages.error(request, "Unauthorized")
        return redirect("core:dashboard")
    requests_list = SellRequest.objects.all().order_by("-created_at")
    return render(request, "core/sell_requests_list.html", {"requests": requests_list})


# ------------------------------
# Buy Airtime (Offline Simulation)
# ------------------------------
@csrf_exempt
@login_required
def buy_airtime(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
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
                transaction_type="Airtime Purchase",
                amount=amount,
                status="Successful",
                reference=str(uuid.uuid4())[:8],
            )
            messages.success(request, f"Airtime ₦{amount} sent to {phone} ({network}) successfully!")
        else:
            messages.error(request, "Insufficient wallet balance.")
        return redirect("core:buy_airtime")

    return render(request, "core/buy_airtime.html", {"wallet": wallet})


# ------------------------------
# Wallet Balance API
# ------------------------------
@csrf_exempt
@login_required
def wallet_balance_api(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    data = {
        "username": request.user.username,
        "balance": float(wallet.balance),
    }
    return JsonResponse(data)

# ------------------------------
# Buy Data (Offline Simulation)
# ------------------------------


VTU_API_KEY = "3e1aafc7efe00b49a0f640049b7ac7"
VTU_BASE_URL = "https://vtu.com.ng/wp-json/api/v1/data"

@csrf_exempt
@login_required
def buy_data(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    plans = PriceTable.objects.all()

    if request.method == "POST":
        network = request.POST.get("network")
        plan_id = request.POST.get("plan_id")
        phone = request.POST.get("phone")

        plan = get_object_or_404(PriceTable, id=plan_id)
        amount = plan.my_price

        if wallet.balance < amount:
            messages.error(request, "❌ Insufficient wallet balance.")
            return redirect("core:buy_data")

        payload = {
            "network": network,
            "mobile_number": phone,
            "plan": plan.api_code,  # make sure your PriceTable has this field
            "Ported_number": "true",
        }

        headers = {
            "Authorization": f"Token {VTU_API_KEY}"
        }

        try:
            response = requests.post(VTU_BASE_URL, data=payload, headers=headers)
            data = response.json()
            print("🔍 VTU Response:", json.dumps(data, indent=2))

            # ✅ Log transaction immediately for tracking
            trx = Transaction.objects.create(
                user=request.user,
                transaction_type="Data Purchase",
                amount=amount,
                status="Pending",
                reference=data.get("order_id", str(uuid.uuid4())[:8]),
                description=f"Network: {network}, Phone: {phone}",
            )

            if data.get("status") == "success":
                wallet.balance -= amount
                wallet.save()
                trx.status = "Successful"
                trx.save()
                messages.success(
                    request,
                    f"✅ {network} data plan {plan.plan_name} sent to {phone} successfully!"
                )
            else:
                error_message = data.get("message", "Unknown VTU error")
                trx.status = "Failed"
                trx.description += f" | VTU Error: {error_message}"
                trx.save()
                messages.error(
                    request,
                    f"❌ VTU API Error: {error_message}"
                )

        except Exception as e:
            error = str(e)
            Transaction.objects.create(
                user=request.user,
                transaction_type="Data Purchase",
                amount=amount,
                status="Failed",
                reference=str(uuid.uuid4())[:8],
                description=f"Exception: {error}",
            )
            messages.error(request, f"⚠️ Request failed: {error}")

        return redirect("core:buy_data")

    return render(request, "core/buy_data.html", {"wallet": wallet, "plans": plans})

# Data Plans API
# ------------------------------
@csrf_exempt
def get_plans(request):
    network = request.GET.get("network")
    data_type = request.GET.get("data_type")

    plans = PriceTable.objects.filter(network=network, data_type=data_type).values(
        "id", "plan_name", "vtu_cost", "my_price"
    )

    plan_list = []
    for p in plans:
        # Extract size and duration from the plan name
        size = None
        duration = None
        words = p["plan_name"].split()
        for w in words:
            if "GB" in w or "MB" in w:
                size = w
            if "Day" in w or "Days" in w:
                duration = w

        plan_list.append({
            "id": p["id"],
            "plan_name": p["plan_name"],
            "size": size or "",
            "duration": duration or "",
            "selling_price": float(p["my_price"]),
        })

    return JsonResponse({"plans": plan_list})
