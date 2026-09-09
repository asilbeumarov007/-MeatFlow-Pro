from django.db import models
from decimal import Decimal
from django.conf import settings

class Supplier(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="Ta'minotchi ismi")
    last_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Familiyasi")
    phone = models.CharField(max_length=20, unique=True, verbose_name="Telefon raqami")
    custom_id = models.CharField(max_length=50, unique=True, verbose_name="Ta'minotchi ID")
    our_debt = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Bizning qarzimiz (so'm)"
    )
    customer = models.OneToOneField(
        'Customer',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='supplier_profile',
        verbose_name="Mijoz profili"
    )
    note = models.TextField(blank=True, null=True, verbose_name="Eslatma/Izoh")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Qo'shilgan vaqti")

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new and not self.customer:
            from .models import Customer
            c_id = f"S-{self.custom_id}"
            cust, created = Customer.objects.get_or_create(
                phone=self.phone,
                defaults={
                    'first_name': self.first_name,
                    'last_name': self.last_name,
                    'custom_id': c_id,
                    'note': f"Ta'minotchi barter profili (ID: {self.custom_id})"
                }
            )
            self.customer = cust
            super().save(update_fields=['customer'])

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''} (ID: {self.custom_id})"


class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name="Mahsulot nomi")
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Chakana narxi (so'm)")
    is_active = models.BooleanField(default=True, db_index=True, verbose_name="Sotuvda bormi?")
    image = models.ImageField(upload_to='products/', null=True, blank=True, verbose_name="Mahsulot rasmi")
    deduct_from = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='child_products',
        verbose_name="Zaxira qaysi mahsulotdan ayriladi?"
    )

    def __str__(self):
        return f"{self.name} - {self.price_per_kg} so'm"


class Stock(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='stock')
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal('0.000'), verbose_name="Zaxira (kg/dona)")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Oxirgi yangilanish")

    def save(self, *args, **kwargs):
        is_low = self.quantity <= Decimal('3.000')
        super().save(*args, **kwargs)
        if is_low and self.product and self.product.is_active:
            try:
                from .telegram_bot import send_message, CHAT_ID
                if CHAT_ID:
                    alert_msg = (
                        f"⚠️ *ZAXIRA KAMAYDI OGOHLANTIRISHI!*\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📦 *Mahsulot:* {self.product.name}\n"
                        f"📉 *Qolgan Zaxira:* `{self.quantity:.3f}` kg/dona\n\n"
                        f"💡 *Tavsiya:* So'yimdan yangi partiya ajratish yoki ta'minotchiga buyurtma berish lozim."
                    )
                    send_message(CHAT_ID, alert_msg)
            except Exception as e:
                print(f"[Stock Low Alert Error]: {e}")

    def __str__(self):
        return f"{self.product.name}: {self.quantity} kg/dona"


class Slaughter(models.Model):
    ANIMAL_TYPES = [
        ('mol', 'Qora mol'),
        ('qoy', "Qo'y"),
    ]
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='slaughters', verbose_name="Ta'minotchi")
    customer = models.ForeignKey('Customer', on_delete=models.SET_NULL, null=True, blank=True, related_name='slaughters', verbose_name="Mijoz (Ta'minotchi)")
    animal_type = models.CharField(max_length=10, choices=ANIMAL_TYPES, verbose_name="Hayvon turi")
    total_weight = models.DecimalField(max_digits=10, decimal_places=3, verbose_name="Toza go'sht og'irligi (kg)")
    remaining_weight = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal('0.000'), verbose_name="Qolgan vazn (kg)")
    purchase_price_per_kg = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Xarid narxi (so'm/kg)")
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Jami xarid summasi")
    due_date = models.DateField(verbose_name="To'lov muddati (Nasiya)")
    is_paid = models.BooleanField(default=False, db_index=True, verbose_name="To'landimi?")
    status = models.CharField(
        max_length=15,
        choices=[('active', 'Sotilmoqda'), ('completed', 'Sotib tugatildi')],
        default='active',
        db_index=True,
        verbose_name="Status"
    )
    live_weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Tirik og'irlik (kg)")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="So'yilgan vaqti")


    @property
    def yield_percentage(self):
        """Tirik vaznga nisbatan toza go'sht chiquvi (Yield %)"""
        if self.live_weight and self.live_weight > Decimal('0.000'):
            return (self.total_weight / self.live_weight) * Decimal('100.0')
        return None

    def save(self, *args, **kwargs):
        self.total_cost = Decimal(str(self.total_weight)) * Decimal(str(self.purchase_price_per_kg))
        if not self.pk and (self.remaining_weight is None or self.remaining_weight == 0):
            self.remaining_weight = self.total_weight
        super().save(*args, **kwargs)

    def __str__(self):
        return f"So'yim #{self.id} - {self.get_animal_type_display()} ({self.total_weight} kg)"


class Customer(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="Mijoz ismi")
    last_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Familiyasi")
    phone = models.CharField(max_length=20, unique=True, verbose_name="Telefon raqami")
    custom_id = models.CharField(max_length=50, unique=True, verbose_name="Mijoz ID")
    bonus_points = models.IntegerField(default=0, verbose_name="Bonus ballari")
    debt_amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Qarz miqdori (so'm)"
    )
    is_blacklisted = models.BooleanField(default=False, db_index=True, verbose_name="Qora ro'yxatdami?")
    debt_limit = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('1000000.00'), # Defolt limit: 1 mln so'm qarz limiti
        verbose_name="Kredit qarz limiti (so'm)"
    )
    note = models.TextField(blank=True, null=True, verbose_name="Eslatma/Izoh")
    image = models.ImageField(upload_to='customers/', null=True, blank=True, verbose_name="Mijoz rasmi")
    face_descriptor = models.JSONField(null=True, blank=True, verbose_name="AI Face ID Vektor (128d)")
    telegram_chat_id = models.CharField(max_length=50, blank=True, null=True, db_index=True, verbose_name="Telegram Chat ID")
    is_courier = models.BooleanField(default=False, verbose_name="Kuryermi?")
    courier_status = models.CharField(
        max_length=20,
        choices=[
            ('none', 'Mijoz'),
            ('pending', 'Kuryerlikka ariza bergan'),
            ('approved', 'Tasdiqlangan Kuryer'),
            ('rejected', 'Rad etilgan')
        ],
        default='none',
        verbose_name="Kuryerlik statusi"
    )
    courier_vehicle = models.CharField(max_length=100, blank=True, null=True, verbose_name="Transport turi")
    last_reminder_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Oxirgi eslatma yuborilgan vaqt")
    reminder_count = models.PositiveIntegerField(default=0, verbose_name="Eslatmalar soni")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Qo'shilgan vaqti")

    @property
    def debt_amount_abs(self):
        return abs(self.debt_amount)

    def calculate_smart_score(self):
        if self.is_blacklisted:
            return 0
        
        score = 100
        
        # 1. Deduct based on current debt ratio
        if self.debt_limit > 0:
            ratio = float(self.debt_amount / self.debt_limit)
            score -= min(40, int(ratio * 40))
        else:
            if self.debt_amount > 0:
                score -= 40
                
        # 2. Deduct based on payments vs additions history
        logs = self.logs.all()
        debt_adds = logs.filter(log_type='debt_add').count()
        debt_pays = logs.filter(log_type='debt_pay').count()
        
        if debt_adds > 0:
            pay_ratio = debt_pays / debt_adds
            if pay_ratio < 0.4:
                score -= 20
            elif pay_ratio >= 0.8:
                score += 10
                
        # 3. Deduct if they have high debt amount in general
        if self.debt_amount > Decimal('2000000.00'):
            score -= 10
            
        return min(100, max(0, score))

    def get_credit_score(self):
        if self.is_blacklisted:
            return 'D (Qora ro\'yxat)'
        
        if self.debt_amount > self.debt_limit:
            return 'D (Limit oshgan)'
            
        score = self.calculate_smart_score()
        if score >= 80:
            return 'A (Ishonchli)'
        elif score >= 60:
            return 'B (Yaxshi)'
        elif score >= 40:
            return 'C (Tavakkalli)'
        else:
            return 'D (Xavfli)'

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''} (ID: {self.custom_id})"


class CustomerSpecialPrice(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='special_prices', verbose_name="Mijoz")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='customer_special_prices', verbose_name="Mahsulot")
    special_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Kelishilgan maxsus narx (so'm)")
    notes = models.CharField(max_length=150, blank=True, null=True, verbose_name="Eslatma (masalan: Choyxona narxi)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")

    class Meta:
        unique_together = ('customer', 'product')
        verbose_name = "Mijoz maxsus narxi"
        verbose_name_plural = "Mijozlar maxsus narxlari"

    def __str__(self):
        return f"{self.customer.first_name} - {self.product.name}: {self.special_price:,.0f} so'm"


class Sale(models.Model):
    PAYMENT_METHODS = [
        ('naqd', 'Naqd'),
        ('karta', 'Plastik Karta'),
        ('qr', 'TBC QR'),
        ('nasiya', 'Nasiya (Qarz)'),
        ('aralash', 'Aralash (Split)'),
    ]
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales', verbose_name="Xaridor")
    shift = models.ForeignKey('CashierShift', on_delete=models.SET_NULL, null=True, blank=True, related_name='sales', verbose_name="Kassa shifti")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Asl hisoblangan summa")
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="O'tib berilgan chegirma")
    bonus_used = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Bonusdan yechilgan summa")
    debt_added = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Qarzga yozilgan summa")
    final_paid = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Amalda to'langan summa")
    paid_naqd = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Naqd to'langan")
    paid_karta = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Karta to'langan")
    paid_qr = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="QR to'langan")
    payment_method = models.CharField(max_length=15, choices=PAYMENT_METHODS, default='naqd', db_index=True, verbose_name="To'lov turi")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Savdo vaqti")

    def __str__(self):
        return f"Sotuv #{self.id} - {self.created_at.strftime('%d.%m.%Y %H:%M')} ({self.get_payment_method_display()})"


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name="Mahsulot")
    weight = models.DecimalField(max_digits=10, decimal_places=3, verbose_name="Vazni/Soni")
    price_at_sale = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Sotilgan vaqtdagi narxi")
    item_total = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Oraliq summa")
    slaughter = models.ForeignKey(
        'Slaughter',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='items_sold',
        verbose_name="So'yim partiyasi"
    )
    stock_batch = models.ForeignKey(
        'StockBatch',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='items_sold',
        verbose_name="Tayyor go'sht partiyasi"
    )

    def save(self, *args, **kwargs):
        self.item_total = Decimal(str(self.weight)) * Decimal(str(self.price_at_sale))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} ({self.weight} kg/dona)"


class CustomerLog(models.Model):
    LOG_TYPES = [
        ('sale', 'Xarid'),
        ('debt_add', "Qarz ko'payishi"),
        ('debt_pay', "Qarz to'lashi"),
        ('bonus', "Bonus o'zgarishi"),
        ('reminder', "Qarz eslatmasi yuborildi"),
    ]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='logs', verbose_name="Mijoz")
    log_type = models.CharField(max_length=20, choices=LOG_TYPES, db_index=True, verbose_name="Amal turi")
    title = models.CharField(max_length=255, verbose_name="Amal sarlavhasi")
    message = models.TextField(default='', verbose_name="Batafsil matn (Chat xabari)")
    details = models.JSONField(null=True, blank=True, verbose_name="Tizimli batafsil ma'lumotlar (JSON)")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Amal summasi")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Vaqti")

    def __str__(self):
        return f"{self.customer.first_name} - {self.get_log_type_display()} - {self.created_at.strftime('%d.%m %H:%M')}"


class Notebook(models.Model):
    name = models.CharField(max_length=100, verbose_name="Daftar nomi")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class StockBatch(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='batches', verbose_name="Mahsulot")
    initial_quantity = models.DecimalField(max_digits=12, decimal_places=3, verbose_name="Dastlabki og'irligi (kg)")
    current_quantity = models.DecimalField(max_digits=12, decimal_places=3, verbose_name="Joriy og'irligi (kg)")
    purchase_price_per_kg = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Xarid narxi (so'm/kg)")
    decay_rate_per_day = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('1.00'), verbose_name="Kunlik qurish zarari (%)")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Kiritilgan vaqti")
    updated_at = models.DateTimeField(auto_now=True)

    def get_days_passed(self):
        from django.utils import timezone
        delta = timezone.now() - self.created_at
        return max(0, delta.days)

    def get_decayed_weight(self):
        days = self.get_days_passed()
        if days <= 0:
            return self.current_quantity
        factor = Decimal(str((1 - float(self.decay_rate_per_day)/100.0) ** days))
        return (self.current_quantity * factor).quantize(Decimal('0.001'))

    def get_decay_loss(self):
        return (self.current_quantity - self.get_decayed_weight()).quantize(Decimal('0.001'))

    def get_real_cost_per_kg(self):
        decayed = self.get_decayed_weight()
        if decayed <= 0:
            return self.purchase_price_per_kg
        total_cost = self.initial_quantity * self.purchase_price_per_kg
        return (total_cost / decayed).quantize(Decimal('0.01'))

    def get_ai_recommendation(self):
        """Vitrinada 2 kundan ortiq turgan partiyalar uchun AI tavsiya va ogohlantirish."""
        days = self.get_days_passed()
        qty = float(self.current_quantity)
        if qty <= 0.05:
            return None
        if days >= 2:
            decay_loss = float(self.get_decay_loss())
            decay_sum = decay_loss * float(self.purchase_price_per_kg)
            return {
                'batch_id': self.id,
                'product_name': self.product.name,
                'days': days,
                'quantity': qty,
                'decay_loss_kg': decay_loss,
                'decay_loss_sum': decay_sum,
                'urgency': 'high' if days >= 3 else 'medium',
                'title': f"⚠️ Vitrinada {days} kundan beri turibdi!",
                'message': f"Partiya #{self.id} ({self.product.name}) vitrinada {days} kundan beri turibdi ({qty:.2f} kg qolgan). Qurish talofatini kamaytirish uchun ushbu partiyani tezroq qiymaga aylantirish yoki tezroq sotish tavsiya etiladi!",
                'action_suggestion': "Ushbu partiyani qiymaga aylantirish yoki tezroq sotish tavsiya etiladi"
            }
        return None

    def __str__(self):
        return f"{self.product.name} Partiya #{self.id} ({self.current_quantity} kg)"


class CashTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('in', 'Kirim (Cash In)'),
        ('out', 'Chiqim (Cash Out)'),
    ]
    CATEGORIES = [
        ('kassa_float', 'Kassa boshlang\'ich qoldig\'i'),
        ('expense', 'Xarajat / Chiqim'),
        ('supplier_pay', 'Ta\'minotchiga to\'lov'),
        ('salary', 'Ish haqi to\'lovi'),
        ('debt_pay', 'Qarz to\'lovi (Mijoz)'),
        ('other', 'Boshqa'),
    ]
    PAYMENT_METHODS = [
        ('naqd', 'Naqd'),
        ('karta', 'Plastik karta'),
    ]
    transaction_type = models.CharField(max_length=5, choices=TRANSACTION_TYPES, db_index=True, verbose_name="Turi")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Summa")
    category = models.CharField(max_length=20, choices=CATEGORIES, default='other', db_index=True, verbose_name="Kategoriya")
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default='naqd', verbose_name="To'lov turi")
    description = models.TextField(blank=True, null=True, verbose_name="Izoh / Maqsad")
    voice_raw_text = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ovozli xom matn")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Vaqti")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Mas'ul")
    customer = models.ForeignKey('Customer', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Mijoz (Xaridor)")
    supplier = models.ForeignKey('Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='cash_transactions', verbose_name="Ta'minotchi")

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount:,} so'm ({self.get_category_display()})"


class B2BOrder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda (Chek kutilmoqda)'),
        ('payment_uploaded', 'To\'lov cheki yuklandi'),
        ('approved', 'Tasdiqlandi'),
        ('preparing', 'Go\'sht tortilmoqda/Qadoqlanmoqda'),
        ('shipping', 'Kuryer yo\'lda'),
        ('completed', 'Muvaffaqiyatli yetkazildi'),
        ('rejected', 'Rad etildi'),
    ]
    DELIVERY_CHOICES = [
        ('delivery', 'Dostavka (Yetkazib berish)'),
        ('pickup', 'Samovivoz (Do\'kondan olib ketish)'),
    ]
    PAYMENT_CHOICES = [
        ('karta', 'Karta (Click / Payme)'),
        ('naqd', 'Naqd (Qabul qilganda)'),
        ('nasiya', 'Nasiya'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='b2b_orders', verbose_name="Mijoz")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='b2b_orders', verbose_name="Mahsulot")
    requested_weight = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Kutilayotgan og'irlik (kg)")
    delivery_type = models.CharField(max_length=20, choices=DELIVERY_CHOICES, default='delivery', db_index=True, verbose_name="Yetkazib berish turi")
    delivery_address = models.TextField(blank=True, null=True, verbose_name="Yetkazish manzili")
    latitude = models.FloatField(blank=True, null=True, verbose_name="GPS Latitude")
    longitude = models.FloatField(blank=True, null=True, verbose_name="GPS Longitude")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='karta', verbose_name="To'lov turi")
    payment_proof_image = models.ImageField(upload_to='payment_proofs/', blank=True, null=True, verbose_name="To'lov cheki fotosi")
    notes = models.TextField(blank=True, null=True, verbose_name="Maxsus eslatmalar")
    assigned_courier = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries', verbose_name="Biriktirilgan Kuryer")
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="Kuryerlik (Dostavka) haqsi")
    distance_km = models.FloatField(default=0.0, verbose_name="Masofa (km)")
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending', db_index=True, verbose_name="Status")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Yaratilgan vaqti")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Tahrirlangan vaqti")

    def __str__(self):
        return f"Buyurtma #{self.id}: {self.customer.first_name} - {self.product.name} ({self.requested_weight} kg) - {self.get_status_display()}"


class StoreSetting(models.Model):
    name = models.CharField(max_length=100, default="Baxmal Meat Do'koni", verbose_name="Do'kon nomi")
    address = models.CharField(max_length=255, default="Jizzax viloyati, Baxmal tumani, Sangzor Guzari", verbose_name="Do'kon manzili")
    phone_number = models.CharField(max_length=30, default="+998 77 082 4477", verbose_name="Telefon raqam")
    announcement_text = models.CharField(max_length=255, default="🔥 Mol va Qo'y go'shtidan buyurtma bering — Halol va sarxil go'sht kafolati!", verbose_name="Yuqori e'lon matni")
    hero_title = models.CharField(max_length=255, default="Sarxil Go'sht & Raqamli MeatFlow Pro Texnologiyasi", verbose_name="Bosh sahifa sarlavhasi (Hero Title)")
    hero_subtitle = models.TextField(default="Baxmal Meat — Fermadan dasturxongacha laboratoriya nazorati, IoT smart tarozilar, shaffof hisob-kitob va tezkor xizmat.", verbose_name="Bosh sahifa ta'rifi (Hero Subtitle)")
    promo_banner_text = models.CharField(max_length=255, default="Baxmal tumani bo'ylab buyurtmalarni tezkor yetkazib beramiz!", verbose_name="Aksiya banneri matni")
    promo_badge_text = models.CharField(max_length=100, default="🔥 KATTA AKSIYA", verbose_name="Aksiya Nishoni (Badge)")
    promo_image = models.ImageField(upload_to="promos/", null=True, blank=True, verbose_name="Aksiya 3D Rasmi/Banneri")
    promo_active = models.BooleanField(default=True, verbose_name="Aksiya Banneri Faolmi?")
    latitude = models.FloatField(default=41.2995, verbose_name="Do'kon GPS Latitude")
    longitude = models.FloatField(default=69.2401, verbose_name="Do'kon GPS Longitude")
    base_delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('10000.00'), verbose_name="Boshlang'ich kuryer narxi (so'm)")
    fee_per_km = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('3000.00'), verbose_name="Har bir km uchun (so'm)")
    min_free_delivery_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('500000.00'), verbose_name="Bepul yetkazish minimal summasi (so'm)")
    cashback_percent = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('2.00'), verbose_name="Mijoz Keshbek foizi (%)")
    send_sms_receipts = models.BooleanField(default=True, verbose_name="SMS Chek yuborish faolmi?")
    is_active = models.BooleanField(default=True, verbose_name="Faolmi?")
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        verbose_name = "Do'kon Sozlamasi & Lokatsiyasi"
        verbose_name_plural = "Do'kon Sozlamalari & Lokatsiyasi"

    def __str__(self):
        return f"{self.name} (Lat: {self.latitude}, Lng: {self.longitude})"


class AIChatMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_chat_messages')
    sender = models.CharField(max_length=10, choices=[('user', 'User'), ('bot', 'AI')])
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.sender}: {self.message[:30]}"


class PaymentProof(models.Model):
    """Mijoz karta orqali to'laganda yuklagan chek rasmi."""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='payment_proofs', verbose_name="Mijoz")
    customer_log = models.ForeignKey(CustomerLog, on_delete=models.SET_NULL, null=True, blank=True, related_name='proof', verbose_name="Bog'liq log")
    image = models.ImageField(upload_to='payment_proofs/', verbose_name="Chek rasmi")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="To'lov summasi")
    provider = models.CharField(max_length=20, default='karta', verbose_name="To'lov tizimi")
    note = models.TextField(blank=True, null=True, verbose_name="Izoh")
    is_verified = models.BooleanField(default=False, verbose_name="Admin tasdiqladi?")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yuklangan vaqt")

    def __str__(self):
        return f"{self.customer.first_name} - {self.amount:,} so'm cheki ({self.created_at.strftime('%d.%m.%Y')})"


class CashierShift(models.Model):
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Kassir")
    opened_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Shift ochilgan vaqt")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="Shift yopilgan vaqt")
    is_open = models.BooleanField(default=True, db_index=True, verbose_name="Faolmi")

    
    # Opening values
    opening_cash = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Boshlang'ich naqd pul (so'm)")
    
    # Closed values (calculated at shift close)
    closed_cash_expected = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Kutilayotgan naqd pul (so'm)")
    closed_cash_actual = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Faktik naqd pul (so'm)")
    closed_card_expected = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Kutilayotgan karta (so'm)")
    closed_debt_expected = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Kutilayotgan nasiya (so'm)")
    
    # Difference (closed_cash_actual - closed_cash_expected)
    cash_difference = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Farq (so'm)")
    notes = models.TextField(blank=True, null=True, verbose_name="Shift izohi")
    
    def __str__(self):
        status = "Ochiq" if self.is_open else "Yopilgan"
        return f"Shift #{self.id} - {self.cashier.username} ({status})"


class PaymentSetting(models.Model):
    """Admin panel orqali boshqariladigan to'lov usullari (Karta va QR kod)."""
    title = models.CharField(max_length=100, default="Click / Payme / Karta", verbose_name="To'lov tizimi nomi")
    card_number = models.CharField(max_length=30, blank=True, null=True, verbose_name="Karta raqami (masalan: 8600 1234 5678 9012)")
    card_holder = models.CharField(max_length=100, blank=True, null=True, verbose_name="Karta egasi F.I.SH")
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True, verbose_name="QR kod fotosi")
    instructions = models.TextField(blank=True, null=True, default="To'lovni amalga oshirgach, to'lov cheki fotosini ushbu chatga yuboring.", verbose_name="Mijozga yo'riqnoma")
    is_active = models.BooleanField(default=True, verbose_name="Faolmi?")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "To'lov Rekviziti (Karta/QR)"
        verbose_name_plural = "To'lov Rekvizitlari (Karta/QR)"

    def __str__(self):
        return f"{self.title} - {self.card_number or 'QR Kod'}"


# ── SIGNALS FOR AUTO-SYNC ──
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Customer)
def auto_create_supplier_for_barter_customer(sender, instance, created, **kwargs):
    if created:
        if instance.custom_id.startswith('T-') or instance.custom_id.startswith('S-'):
            from .models import Supplier
            sup_custom_id = instance.custom_id[2:] if len(instance.custom_id) > 2 else instance.custom_id
            
            # Check if supplier already exists
            if not Supplier.objects.filter(models.Q(phone=instance.phone) | models.Q(custom_id=sup_custom_id) | models.Q(customer=instance)).exists():
                Supplier.objects.create(
                    first_name=instance.first_name,
                    last_name=instance.last_name,
                    phone=instance.phone,
                    custom_id=sup_custom_id,
                    customer=instance,
                    note=f"Avtomatik yaratilgan ta'minotchi (Mijoz ID: {instance.custom_id})"
                )


@receiver(post_save, sender=Customer)
def auto_backup_customer_to_telegram(sender, instance, created, **kwargs):
    if created:
        import sys
        if 'test' in sys.argv:
            return
        import threading
        def run_backup():
            try:
                from .telegram_bot import send_customer_excel_backup
                send_customer_excel_backup()
            except Exception as e:
                print("Failed inside customer backup thread:", e)
        threading.Thread(target=run_backup).start()