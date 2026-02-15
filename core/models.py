from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from decimal import Decimal
from django.dispatch import receiver

# -------------------------------
# Global Choices
# -------------------------------
NETWORK_CHOICES = (
        ("01", "MTN"),
        ("02", "GLO"),
        ("03", "9MOBILE"),
        ("04", "AIRTEL"),
        ("smile", "SMILE"),
    )


TRANSACTION_TYPE = [
    ("Airtime Purchase", "Airtime Purchase"),
    ("Data Purchase", "Data Purchase"),
    ("Wallet Funding", "Wallet Funding"),
    ("Withdrawal", "Withdrawal"),
]

TRANSACTION_STATUS = [
    ("Pending", "Pending"),
    ("Successful", "Successful"),
    ("Failed", "Failed"),
]

REQUEST_STATUS = [
    ("Pending", "Pending"),
    ("Approved", "Approved"),
    ("Rejected", "Rejected"),
]

# -------------------------------
# Wallet Model
# -------------------------------

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username} - ₦{self.balance}"

    class Meta:
        verbose_name = "Wallet"
        verbose_name_plural = "Wallets"


# -------------------------------
# Wallet Transaction History
# -------------------------------
class WalletTransaction(models.Model):

    TRANSACTION_TYPES = (
        ("credit", "Credit"),
        ("debit", "Debit"),
        ("airtime", "Airtime"),
        ("data", "Data"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reference = models.CharField(max_length=100, unique=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} | {self.transaction_type} | ₦{self.amount} | {self.status}"

# -------------------------------
# Price Table (Data Plans)
# -------------------------------
class PriceTable(models.Model):

    PLAN_TYPE_CHOICES = [
        ("SME", "SME"),
        ("GIFTING", "Gifting"),
        ("CG", "Corporate Gifting"),
        ("CG_LITE", "CG Lite"),
        ("AWOOF", "Awoof Gifting"),
        ("DIRECT", "Direct Data"),
        ("DATACARD", "Data Card"),
        ("SMILE_DIRECT", "Smile Direct"),
    ]

    NETWORK_CHOICES = [
        ("MTN", "MTN"),
        ("GLO", "GLO"),
        ("AIRTEL", "AIRTEL"),
        ("9MOBILE", "9MOBILE"),
        ("SMILE", "SMILE"),
    ]

    network = models.CharField(
        max_length=20,
        choices=NETWORK_CHOICES
    )

    # ✅ MUST be integer for ePins
    network_id = models.PositiveIntegerField(
        help_text="ePins numeric network ID (e.g. MTN=1, GLO=2, 9MOBILE=3, AIRTEL=4)"
    )

    plan_type = models.CharField(
        max_length=20,
        choices=PLAN_TYPE_CHOICES,
        default="SME"
    )

    plan_name = models.CharField(max_length=100)

    duration = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    vtu_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    my_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # ✅ MUST be integer for ePins (this is DataPlan)
    plan_code = models.PositiveIntegerField(
        help_text="ePins epincode / DataPlan ID"
    )

    # Smile requires direct endpoint
    smile_direct = models.BooleanField(default=False)

    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.network} | {self.plan_type} | {self.plan_name} | ₦{self.my_price}"

    class Meta:
        verbose_name = "Price Table"
        verbose_name_plural = "Price Tables"

# Sell Request (for manual sales or top-ups)
# -------------------------------
class SellRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    network = models.CharField(max_length=20, choices=NETWORK_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    phone_number = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=REQUEST_STATUS, default="Pending")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.network} - ₦{self.amount}"

    class Meta:
        verbose_name = "Sell Request"
        verbose_name_plural = "Sell Requests"

# -------------------------------
# Helper Function: Auto-create Wallet when new User registers
# -------------------------------
@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_wallet(sender, instance, **kwargs):
    instance.wallet.save()

class VTUTransaction(models.Model):

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    ]

    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    reference = models.CharField(max_length=50, unique=True)

    service = models.CharField(max_length=20)  # airtime / data
    network = models.CharField(max_length=20)

    phone = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    response = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reference} - {self.status}"
