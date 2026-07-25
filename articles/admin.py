from django.contrib import admin
from .models import Product, ProductImage

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 2

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]
    list_display = ['name', 'animal_type', 'cut_type', 'price', 'stock_kg', 'date']
    list_filter = ['animal_type', 'date']
    search_fields = ['name', 'cut_type']