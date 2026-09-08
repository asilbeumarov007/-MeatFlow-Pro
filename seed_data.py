import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from pos.models import StoreSetting, Product, Stock
from decimal import Decimal

User = get_user_model()

# 1. Superuser
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@baxmalmeat.uz', 'admin12345')
    print('Superuser [admin] yaratildi')

if not User.objects.filter(username='guljahon').exists():
    User.objects.create_superuser('guljahon', 'guljahon@baxmalmeat.uz', 'guljahon2026')
    print('Superuser [guljahon] yaratildi')

# 2. Store Setting
store, created = StoreSetting.objects.get_or_create(
    id=1,
    defaults={
        'name': "Baxmal Meat Do'koni",
        'phone_number': "+998 77 082 4477",
        'address': "Toshkent shahri, Chilonzor tumani",
        'announcement_text': "🔥 Mol va Qo'y go'shtidan buyurtma bering — Toshkent bo'ylab yetkazib berish va halol kafolat!",
        'hero_title': "Sarxil Go'sht & Raqamli MeatFlow Pro Texnologiyasi",
        'hero_subtitle': "Baxmal Meat — Fermadan dasturxongacha laboratoriya nazorati, IoT smart tarozilar, shaffof hisob-kitob va tezkor kuryerlik xizmati.",
        'promo_banner_text': "500,000 so'mdan yuqori buyurtmalar uchun Toshkent shahri bo'ylab yetkazib berish BEPUL!",
        'latitude': 41.2995,
        'longitude': 69.2401,
        'base_delivery_fee': Decimal('10000.00'),
        'fee_per_km': Decimal('3000.00'),
        'min_free_delivery_amount': Decimal('500000.00'),
        'cashback_percent': Decimal('2.00'),
        'is_active': True
    }
)
if created:
    print("StoreSetting yaratildi")

# 3. Clean Products
sample_products = [
    ("Mol Lahm Go'shti (Saralangan)", Decimal("85000.00"), Decimal("50.000")),
    ("Mermer Mol Steak (Ribeye)", Decimal("95000.00"), Decimal("30.000")),
    ("Baxmal Qo'y Qovurg'asi", Decimal("80000.00"), Decimal("40.000")),
    ("Qo'y Lahm Go'shti", Decimal("85000.00"), Decimal("35.000")),
    ("Qiyma Go'sht (Yog'siz)", Decimal("80000.00"), Decimal("25.000")),
    ("Dumg'aza", Decimal("70000.00"), Decimal("20.000")),
    ("Saralangan Jigar & Yurak", Decimal("50000.00"), Decimal("15.000")),
]

for name, price, qty in sample_products:
    p, _ = Product.objects.get_or_create(name=name, defaults={'price_per_kg': price, 'is_active': True})
    s, _ = Stock.objects.get_or_create(product=p, defaults={'quantity': qty})
    s.quantity = qty
    s.save()

print('Initial mahsulotlar va zaxiralar PostgreSQL bazasiga muvaffaqiyatli saqlandi!')
