from django import forms
from .models import Product, ProductImage
from django.forms import inlineformset_factory

# Mahsulot va uning rasmlari orasidagi bog'liqlik formseti
ProductImageFormSet = inlineformset_factory(
    Product,
    ProductImage,
    fields=('image',),
    extra=1, # Yangi rasm qo'shish uchun 1 ta bo'sh joy
    can_delete=True # Rasmlarni o'chirish imkoniyati
)