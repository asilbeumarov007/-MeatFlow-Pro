from rest_framework import serializers
from decimal import Decimal
from .models import Supplier, Product, Stock, Slaughter, Customer, Sale, SaleItem, CustomerLog

class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ['id', 'quantity', 'updated_at']


class ProductSerializer(serializers.ModelSerializer):
    stock = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'price_per_kg', 'is_active', 'image', 'stock', 'deduct_from']

    def get_stock(self, obj):
        if hasattr(obj, 'stock'):
            return float(obj.stock.quantity)
        return 0.0

    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return 'https://cdn-icons-png.flaticon.com/512/1046/1046747.png'


class CustomerSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    credit_score = serializers.SerializerMethodField()
    smart_score = serializers.SerializerMethodField()
    is_barter = serializers.SerializerMethodField()
    supplier_debt = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id', 'first_name', 'last_name', 'name', 'phone', 'custom_id',
            'bonus_points', 'debt_amount', 'debt_limit', 'is_blacklisted',
            'credit_score', 'smart_score', 'is_barter', 'supplier_debt',
            'note', 'image', 'created_at'
        ]

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name or ''}".strip()

    def get_credit_score(self, obj):
        return obj.get_credit_score()

    def get_smart_score(self, obj):
        return obj.calculate_smart_score()

    def get_is_barter(self, obj):
        return hasattr(obj, 'supplier_profile') and obj.supplier_profile is not None

    def get_supplier_debt(self, obj):
        if self.get_is_barter(obj):
            return float(obj.supplier_profile.our_debt)
        return 0.0

    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return 'https://cdn-icons-png.flaticon.com/512/149/149071.png'


class SupplierSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = [
            'id', 'first_name', 'last_name', 'name', 'phone', 'custom_id',
            'our_debt', 'customer', 'note', 'created_at'
        ]

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name or ''}".strip()


class SlaughterSerializer(serializers.ModelSerializer):
    supplier_name = serializers.SerializerMethodField()

    class Meta:
        model = Slaughter
        fields = [
            'id', 'supplier', 'customer', 'supplier_name', 'animal_type',
            'total_weight', 'remaining_weight', 'purchase_price_per_kg',
            'total_cost', 'due_date', 'is_paid', 'status', 'created_at'
        ]

    def get_supplier_name(self, obj):
        if obj.supplier:
            return f"{obj.supplier.first_name} {obj.supplier.last_name or ''}".strip()
        elif obj.customer:
            return f"{obj.customer.first_name} {obj.customer.last_name or ''}".strip()
        return "Noma'lum"


class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')

    class Meta:
        model = SaleItem
        fields = ['id', 'product', 'product_name', 'weight', 'price_at_sale', 'item_total']


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = [
            'id', 'customer', 'customer_name', 'shift', 'total_amount',
            'discount_amount', 'bonus_used', 'debt_added', 'final_paid',
            'payment_method', 'created_at', 'items'
        ]

    def get_customer_name(self, obj):
        if obj.customer:
            return f"{obj.customer.first_name} {obj.customer.last_name or ''}".strip()
        return "Noma'lum"
