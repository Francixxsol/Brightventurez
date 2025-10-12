from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

# ------------------------
# Choices
# ------------------------
NETWORK_CHOICES = [
    ("MTN", "MTN"),
    ("GLO", "GLO"),
    ("AIRTEL", "AIRTEL"),
    ("9MOBILE", "9MOBILE"),
]

DATA_TYPE_CHOICES = [
    ("SME", "SME"),
    ("SME2", "SME2"),
    ("GIFTING", "GIFTING"),
    ("AWUF", "AWUF"),
]

TRANSACTION_STATUS = [
    ("PENDING", "Pending"),
    ("SUCCESS", "Success"),
    ("FAILED", "Failed"),
]

# ------------------------
# Wallet
# ------------------------
class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.user.username} Wallet - {self.balance}"

# ------------------------
# Transaction
# ------------------------
class Transaction(models.Model):
    TYPE_CHOICES = (
        ("credit", "Credit"),
        ("debit", "Debit"),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.type} - {self.amount}"

# ------------------------
# Sell Request
# ------------------------
class SellRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    data_type = models.CharField(max_length=20, choices=DATA_TYPE_CHOICES)
    size_mb = models.IntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.data_type} {self.size_mb}MB - {self.amount}"

# ------------------------
# Airtime
# ------------------------
class Airtime(models.Model):
    network = models.CharField(max_length=20, choices=NETWORK_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.network} - {self.amount}"

# ------------------------
# Price Table
# ------------------------
class PriceTable(models.Model):
    network = models.CharField(max_length=20, choices=NETWORK_CHOICES)
    plan_name = models.CharField(max_length=100)
    size_mb = models.IntegerField()
    vtu_cost = models.DecimalField(max_digits=12, decimal_places=2)
    my_price = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.network} - {self.plan_name} ({self.size_mb}MB)"

# ------------------------
# Data Models
# ------------------------
class DataCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    network = models.CharField(max_length=50, choices=NETWORK_CHOICES)
    api_code = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.network})"

class DataPlan(models.Model):
    category = models.ForeignKey(DataCategory, on_delete=models.CASCADE)
    size = models.CharField(max_length=20)
    duration = models.CharField(max_length=20)
    provider_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    api_code = models.CharField(max_length=50, blank=True, null=True)

    def profit(self):
        return round(self.selling_price - self.provider_price, 2)

    def __str__(self):
        return f"{self.category.name} - {self.size} ({self.selling_price})"

class DataTransaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    network = models.CharField(max_length=20, choices=NETWORK_CHOICES)
    phone_number = models.CharField(max_length=15)
    plan_type = models.CharField(max_length=20, choices=[("VIRTUAL", "Virtual"), ("PROVIDER", "Provider")])
    plan_name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=TRANSACTION_STATUS, default="PENDING")
    reference = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    provider_response = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.network} ({self.status})"

# ------------------------
# Providers
# ------------------------
class Provider(models.Model):
    name = models.CharField(max_length=100)
    api_base_url = models.URLField()
    api_key = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name

class ProviderPlan(models.Model):
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE)
    network = models.CharField(max_length=50, choices=NETWORK_CHOICES)
    category = models.CharField(max_length=50)
    plan_name = models.CharField(max_length=100)
    size = models.CharField(max_length=50)
    provider_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.provider.name} - {self.plan_name} ({self.network})"

class VirtualPlan(models.Model):
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE)  # <-- must exist for inline
    network = models.CharField(max_length=50, choices=NETWORK_CHOICES)
    plan_name = models.CharField(max_length=100)
    size = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    validity = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.network} - {self.plan_name} ({self.size})"

# ------------------------
# Auto-create wallet
# ------------------------
@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.get_or_create(user=instance, defaults={'balance': 0})
