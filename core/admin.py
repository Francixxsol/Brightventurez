from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import (
    Airtime,
    DataPlan,
    Wallet,
    Transaction,
    SellRequest,
    PriceTable,
    Provider,
    ProviderPlan,
    VirtualPlan,
    DataTransaction
)

# ------------------------
# Airtime Admin
# ------------------------
@admin.register(Airtime)
class AirtimeAdmin(admin.ModelAdmin):
    list_display = ('network', 'amount')
    list_editable = ('amount',)
    search_fields = ('network',)
    list_filter = ('network',)

# ------------------------
# Data Plan Admin
# ------------------------
@admin.register(DataPlan)
class DataPlanAdmin(admin.ModelAdmin):
    list_display = ('category', 'size', 'duration', 'selling_price')
    list_editable = ('size', 'duration', 'selling_price')
    list_filter = ('category',)
    search_fields = ('category__name', 'size', 'api_code')

# ------------------------
# Wallet Admin
# ------------------------
@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')
    list_editable = ('balance',)
    search_fields = ('user__username', 'user__email')

# ------------------------
# Transaction Admin
# ------------------------
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'amount', 'description', 'created_at')
    list_editable = ('amount',)
    list_filter = ('type',)
    search_fields = ('user__username', 'description')

# ------------------------
# Sell Request Admin
# ------------------------
@admin.register(SellRequest)
class SellRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'data_type', 'size_mb', 'amount', 'approved', 'created_at')
    list_editable = ('approved',)
    list_filter = ('approved', 'data_type')
    search_fields = ('user__username',)
    actions = ['approve_requests']

    def approve_requests(self, request, queryset):
        for sell_req in queryset.filter(approved=False):
            sell_req.approved = True
            sell_req.save()
            wallet, _ = Wallet.objects.get_or_create(user=sell_req.user)
            wallet.balance += sell_req.amount
            wallet.save()
            Transaction.objects.create(
                user=sell_req.user,
                amount=sell_req.amount,
                type='credit',
                description=f'Approved sell request #{sell_req.id}'
            )
        self.message_user(request, 'Selected requests approved and wallets credited.')

    approve_requests.short_description = 'Approve selected sell requests'

# ------------------------
# Price Table Admin
# ------------------------
@admin.register(PriceTable)
class PriceTableAdmin(admin.ModelAdmin):
    list_display = ('network', 'plan_name', 'vtu_cost', 'my_price')
    list_editable = ('vtu_cost', 'my_price')
    list_filter = ('network',)
    search_fields = ('plan_name',)

# ------------------------
# Provider Plan Inline
# ------------------------
class ProviderPlanInline(admin.TabularInline):
    model = ProviderPlan
    extra = 1
    fields = ('network', 'plan_name', 'size', 'provider_price', 'selling_price')
    show_change_link = True

# ------------------------
# Virtual Plan Inline
# ------------------------
class VirtualPlanInline(admin.TabularInline):
    model = VirtualPlan
    extra = 1
    fields = ('network', 'plan_name', 'size', 'price')
    show_change_link = True

# ------------------------
# Provider Admin
# ------------------------
@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'api_base_url')
    list_editable = ('api_base_url',)
    inlines = [ProviderPlanInline, VirtualPlanInline]
    search_fields = ('name',)

# ------------------------
# Provider Plan Admin
# ------------------------
@admin.register(ProviderPlan)
class ProviderPlanAdmin(admin.ModelAdmin):
    list_display = ('network', 'plan_name', 'size', 'selling_price', 'provider_price')
    list_editable = ('plan_name', 'size', 'selling_price', 'provider_price')
    list_filter = ('network',)
    search_fields = ('plan_name', 'size')

# ------------------------
# Virtual Plan Admin
# ------------------------
@admin.register(VirtualPlan)
class VirtualPlanAdmin(admin.ModelAdmin):
    list_display = ('network', 'plan_name', 'size', 'price')
    list_editable = ('plan_name', 'size', 'price')
    list_filter = ('network',)
    search_fields = ('plan_name', 'size')

# ------------------------
# Data Transaction Admin
# ------------------------
@admin.register(DataTransaction)
class DataTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'network', 'phone_number', 'plan_name', 'amount', 'status', 'created_at', 'view_details')
    list_editable = ('amount', 'status')
    list_filter = ('status', 'network')
    search_fields = ('user__username', 'phone_number', 'plan_name')
    readonly_fields = ('created_at',)

    def view_details(self, obj):
        if obj.id:
            return format_html('<a href="{}">View</a>', f'/admin/core/datatransaction/{obj.id}/change/')
        return "-"
    view_details.short_description = "Action"

# ------------------------
# Inline Admins for User Profile
# ------------------------
class WalletInline(admin.StackedInline):
    model = Wallet
    can_delete = False
    extra = 0
    fields = ('balance',)
    verbose_name_plural = 'Wallet'

class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    fields = ('type', 'amount', 'description', 'created_at')
    readonly_fields = ('created_at',)

class SellRequestInline(admin.TabularInline):
    model = SellRequest
    extra = 0
    fields = ('data_type', 'size_mb', 'amount', 'approved', 'created_at')

class DataTransactionInline(admin.TabularInline):
    model = DataTransaction
    extra = 0
    fields = ('network', 'plan_name', 'phone_number', 'amount', 'status', 'created_at', 'view_details')
    readonly_fields = ('created_at', 'view_details')
    verbose_name_plural = 'Data Purchases'

    def view_details(self, obj):
        if obj.id:
            return format_html('<a href="{}">View</a>', f'/admin/core/datatransaction/{obj.id}/change/')
        return "-"
    view_details.short_description = "Action"

# ------------------------
# Extend User Admin
# ------------------------
class UserAdmin(BaseUserAdmin):
    inlines = [WalletInline, TransactionInline, SellRequestInline, DataTransactionInline]

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
