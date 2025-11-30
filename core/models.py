from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

# -------------------------------
# Network Choices
# -------------------------------
NETWORK_CHOICES = [
    ("MTN", "MTN"),
    ("AIRTEL", "Airtel"),
    ("GLO", "Glo"),
    ("9MOBILE", "9mobile"),
]

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
# models.py
class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username} - ₦{self.balance}"

    class Meta:
        verbose_name = "Wallet"
        verbose_name_plural = "Wallets"

class WalletTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    description = models.CharField(max_length=255)
    reference = models.CharField(max_length=100, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} ₦{self.amount}"
# -------------------------------
# Plan Type Choices
# -------------------------------
PLAN_TYPE_CHOICES = [
    ('SME', 'SME'),
    ('GIFTING', 'Gifting'),
]

class PriceTable(models.Model):
    network = models.CharField(max_length=20, choices=NETWORK_CHOICES)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES, default="SME")  # <- changed
    plan_name = models.CharField(max_length=100)
    duration = models.CharField(max_length=20, blank=True, null=True)  # <-- new field
    vtu_cost = models.DecimalField(max_digits=10, decimal_places=2)
    my_price = models.DecimalField(max_digits=10, decimal_places=2)
    api_code = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.network} - {self.plan_type} - {self.plan_name}"  # <- updated to plan_type

    class Meta:
        verbose_name = "Price Table"
        verbose_name_plural = "Price Tables"

# -------------------------------
# Transaction (Wallet + Airtime/Data + Funding)
# -------------------------------
class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default="Pending")
    reference = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - ₦{self.amount}"

    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

# -------------------------------
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
