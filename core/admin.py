from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Wallet, Transaction, PriceTable, SellRequest
# ---------------------------------------------------
# Inline Wallet under User (so you can see balance in user profile)
# ---------------------------------------------------
class WalletInline(admin.StackedInline):
    model = Wallet
    can_delete = False
    extra = 0
    fields = ('balance',)
    verbose_name_plural = 'Wallet'


# ---------------------------------------------------
# Extend the default User admin to include Wallet
# ---------------------------------------------------
class UserAdmin(BaseUserAdmin):
    inlines = [WalletInline]
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('username', 'email')
    list_filter = ('is_staff', 'is_superuser', 'is_active')


# Re-register UserAdmin with Wallet inline
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# ---------------------------------------------------
# Wallet Admin
# ---------------------------------------------------
@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')
    search_fields = ('user__username',)
    readonly_fields = ('user',)
    list_per_page = 20


# ---------------------------------------------------
# Price Table Admin (for managing VTU plans and pricing)
# ---------------------------------------------------
@admin.register(PriceTable)
class PriceTableAdmin(admin.ModelAdmin):
    list_display = ('network', 'plan_name', 'vtu_cost', 'my_price')
    list_editable = ('vtu_cost', 'my_price')
    list_filter = ('network',)
    search_fields = ('plan_name',)
    list_per_page = 30


# ---------------------------------------------------
# Transaction Admin (for monitoring user activities)
# ---------------------------------------------------
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'transaction_type', 'status', 'created_at')
    list_filter = ('transaction_type', 'status')
    search_fields = ('user__username', 'transaction_type', 'status')
    list_per_page = 25


# ---------------------------------------------------
# Sell Request Admin (for manual sales or top-up requests)
# ---------------------------------------------------
@admin.register(SellRequest)
class SellRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'network', 'amount', 'status', 'created_at')
    list_filter = ('status', 'network')
    search_fields = ('user__username',)
    list_per_page = 25

admin.site.site_header = "BrightVenturez Admin"
admin.site.site_title = "BrightVenturez Dashboard"
admin.site.index_title = "Welcome to BrightVenturez VTU Panel"
