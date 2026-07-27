from django.contrib import admin
from .models import Supplier, Product, Stock, Slaughter, Customer, Sale, SaleItem, CustomerLog

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('custom_id', 'first_name', 'last_name', 'phone', 'our_debt', 'customer')
    search_fields = ('custom_id', 'first_name', 'last_name', 'phone')
    raw_id_fields = ('customer',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_per_kg', 'is_active', 'deduct_from')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'updated_at')
    search_fields = ('product__name',)

@admin.register(Slaughter)
class SlaughterAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'animal_type', 'total_weight', 'remaining_weight', 'purchase_price_per_kg', 'total_cost', 'due_date', 'is_paid', 'status')
    list_filter = ('animal_type', 'is_paid', 'status', 'due_date')
    search_fields = ('supplier__first_name', 'supplier__last_name')
    raw_id_fields = ('supplier', 'customer')

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('custom_id', 'first_name', 'last_name', 'phone', 'bonus_points', 'debt_amount', 'is_courier', 'courier_status', 'is_blacklisted')
    list_filter = ('is_blacklisted', 'is_courier', 'courier_status')
    search_fields = ('custom_id', 'first_name', 'last_name', 'phone')
    actions = ['approve_courier', 'reject_courier']

    def approve_courier(self, request, queryset):
        queryset.update(is_courier=True, courier_status='approved')
        self.message_user(request, f"{queryset.count()} ta mijoz kuryer sifatida tasdiqlandi!")
    approve_courier.short_description = "🚴‍♂️ Kuryer sifatida tasdiqlash"

    def reject_courier(self, request, queryset):
        queryset.update(is_courier=False, courier_status='rejected')
        self.message_user(request, f"{queryset.count()} ta mijoz kuryerligi rad etildi.")
    reject_courier.short_description = "❌ Kuryerlikni rad etish"

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ('item_total',)

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'total_amount', 'discount_amount', 'bonus_used', 'debt_added', 'final_paid', 'payment_method', 'created_at')
    list_filter = ('payment_method', 'created_at')
    inlines = [SaleItemInline]

@admin.register(CustomerLog)
class CustomerLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'log_type', 'title', 'amount', 'created_at')
    list_filter = ('log_type', 'created_at')
    search_fields = ('customer__first_name', 'customer__last_name', 'title')

from .models import CashTransaction, Notebook, B2BOrder, StockBatch, StoreSetting

@admin.register(StoreSetting)
class StoreSettingAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'address', 'latitude', 'longitude', 'base_delivery_fee', 'fee_per_km', 'is_active')
    list_editable = ('is_active',)

@admin.register(CashTransaction)
class CashTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction_type', 'amount', 'category', 'payment_method', 'customer', 'supplier', 'created_by', 'created_at')
    list_filter = ('transaction_type', 'category', 'payment_method', 'created_at')
    search_fields = ('description', 'customer__first_name', 'customer__last_name', 'supplier__first_name', 'supplier__last_name')
    raw_id_fields = ('customer', 'supplier', 'created_by')

@admin.register(Notebook)
class NotebookAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    search_fields = ('name',)

from django.utils.html import format_html

@admin.register(B2BOrder)
class B2BOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'product', 'requested_weight', 'delivery_fee', 'distance_km', 'assigned_courier', 'status', 'payment_proof_preview', 'created_at')
    list_filter = ('status', 'delivery_type', 'created_at')
    search_fields = ('customer__first_name', 'customer__last_name', 'product__name')
    raw_id_fields = ('customer', 'product', 'assigned_courier')
    readonly_fields = ('payment_proof_preview_large',)

    def payment_proof_preview(self, obj):
        if obj.payment_proof_image:
            return format_html('<a href="{0}" target="_blank"><img src="{0}" style="width: 45px; height: 45px; object-fit: cover; border-radius: 6px; border: 1px solid #ddd;" /></a>', obj.payment_proof_image.url)
        return "—"
    payment_proof_preview.short_description = "To'lov cheki"

    def payment_proof_preview_large(self, obj):
        if obj.payment_proof_image:
            return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-width: 450px; max-height: 450px; border-radius: 8px; border: 1px solid #ddd; box-shadow: 0 4px 12px rgba(0,0,0,0.15);" /></a>', obj.payment_proof_image.url)
        return "Rasm yuklanmagan"
    payment_proof_preview_large.short_description = "To'lov cheki fotosi"

@admin.register(StockBatch)
class StockBatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'initial_quantity', 'current_quantity', 'purchase_price_per_kg', 'decay_rate_per_day', 'created_at')
    list_filter = ('created_at', 'product')
    search_fields = ('product__name',)


from .models import AIChatMessage

@admin.register(AIChatMessage)
class AIChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'sender', 'message_snippet', 'created_at')
    list_filter = ('sender', 'created_at')
    search_fields = ('user__username', 'message')
    raw_id_fields = ('user',)

    def message_snippet(self, obj):
        return obj.message[:50]
    message_snippet.short_description = "Xabar"


from .models import PaymentProof

@admin.register(PaymentProof)
class PaymentProofAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'amount', 'provider', 'is_verified', 'created_at')
    list_filter = ('is_verified', 'provider', 'created_at')
    search_fields = ('customer__first_name', 'customer__last_name', 'customer__custom_id')
    raw_id_fields = ('customer', 'customer_log')


from .models import PaymentSetting

@admin.register(PaymentSetting)
class PaymentSettingAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'card_number', 'card_holder', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'card_number', 'card_holder')
    list_editable = ('is_active',)
    ordering = ('-created_at',)