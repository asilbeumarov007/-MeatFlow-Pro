from django.http import JsonResponse
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Sum, Q
from decimal import Decimal
import json
import requests
import os
import random

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import Supplier, Product, Stock, Slaughter, Customer, Sale, SaleItem, CustomerLog
from .serializers import (
    ProductSerializer, CustomerSerializer, SupplierSerializer,
    SlaughterSerializer, SaleSerializer, StockSerializer
)
from django.contrib.auth.decorators import user_passes_test
from .views import create_user_for_customer

# Decimal hisob-kitoblar uchun JSON serializator helper
def decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def json_response(data, status=200):
    return JsonResponse(data, safe=False, status=status, json_dumps_params={'default': decimal_serializer})

def send_telegram_notification(text):
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8898055369:AAFbUW9nLVRXwG-xd0oP1ftQ5vZpTjcL4x8')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '-1004312267841')
    if not bot_token or not chat_id:
        print("Telegram bot token or chat ID is not set. Skipping notification.")
        return False
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram notification error: {e}")
        return False


def send_telegram_location(latitude, longitude):
    """Admin Telegram kanaliga mijoz lokatsiyasini (pin/map) yuborish."""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8898055369:AAFbUW9nLVRXwG-xd0oP1ftQ5vZpTjcL4x8')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '-1004312267841')
    if not bot_token or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendLocation"
        payload = {
            'chat_id': chat_id,
            'latitude': float(latitude),
            'longitude': float(longitude)
        }
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram location send error: {e}")
        return False

# =====================================================================
# MAHSULOTLAR API
# =====================================================================
@api_view(['GET'])
@permission_classes([IsAdminUser])
def api_products(request):
    """Barcha faol mahsulotlar va ularning zaxira (Stock) qoldig'i"""
    products = Product.objects.filter(is_active=True).select_related('stock')
    for p in products:
        if not hasattr(p, 'stock'):
            Stock.objects.create(product=p, quantity=Decimal('0.000'))
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


# =====================================================================
# MIJOZLAR (XARIDORLAR) API
# =====================================================================
@csrf_exempt
@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def api_customers(request):
    """Mijozlarni qidirish (GET) yoki yangi mijoz yaratish (POST)"""
    if request.method == 'GET':
        query = request.GET.get('q', '').strip()
        customers = Customer.objects.all()
        if query:
            customers = customers.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(phone__icontains=query) |
                Q(custom_id__icontains=query)
            )
        serializer = CustomerSerializer(customers[:20], many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        try:
            image_file = None
            debt_limit = Decimal('1000000.00')
            first_name = request.data.get('first_name', '').strip()
            last_name = request.data.get('last_name', '').strip()
            phone = request.data.get('phone', '').strip()
            note = request.data.get('note', '').strip()
            custom_id = request.data.get('custom_id', '').strip()
            raw_limit = request.data.get('debt_limit')
            if raw_limit:
                try:
                    debt_limit = Decimal(str(raw_limit))
                except Exception:
                    pass
            if 'image' in request.FILES:
                image_file = request.FILES['image']

            if not first_name or not phone:
                return Response({'error': "Ism va telefon raqam majburiy!"}, status=status.HTTP_400_BAD_REQUEST)

            if Customer.objects.filter(phone=phone).exists():
                return Response({'error': f"Ushbu telefon raqami ({phone}) bilan mijoz mavjud!"}, status=status.HTTP_400_BAD_REQUEST)

            if not custom_id:
                digits = ''.join(filter(str.isdigit, phone))
                custom_id = f"M-{digits[-4:] or random.randint(1000, 9999)}"
                while Customer.objects.filter(custom_id=custom_id).exists():
                    custom_id = f"M-{random.randint(10000, 99999)}"

            customer = Customer.objects.create(
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                custom_id=custom_id,
                note=note,
                debt_limit=debt_limit
            )

            if image_file:
                customer.image = image_file
                customer.save()

            CustomerLog.objects.create(
                customer=customer,
                log_type='bonus',
                title="Tizimga qo'shildi",
                details={'message': "Mijoz muvaffaqiyatli ro'yxatdan o'tdi."},
                amount=Decimal('0.00')
            )
            create_user_for_customer(customer)

            serializer = CustomerSerializer(customer)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# =====================================================================
# TA'MINOTCHILAR API
# =====================================================================
@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def api_suppliers(request):
    """Ta'minotchilar va Mijozlarni yagona Customer modeli orqali qidirish va qo'shish"""
    if request.method == 'GET':
        query = request.GET.get('q', '').strip()
        
        # Faqat Customer modelidan qidiramiz
        customers = Customer.objects.all()
        if query:
            customers = customers.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(phone__icontains=query) |
                Q(custom_id__icontains=query)
            )
        else:
            # Dastlabki 30 ta yozuv (Ta'minotchilarni birinchi ko'rsatamiz)
            customers = sorted(
                Customer.objects.all(),
                key=lambda x: not (hasattr(x, 'supplier_profile') or x.custom_id.startswith('T-') or x.custom_id.startswith('S-'))
            )[:30]
            
        data = []
        for c in customers:
            is_barter = hasattr(c, 'supplier_profile') and c.supplier_profile is not None
            supplier_debt = float(c.supplier_profile.our_debt) if is_barter else 0.0
            
            if is_barter or c.custom_id.startswith('T-') or c.custom_id.startswith('S-'):
                label = f"♻️ Barter (Ta'minotchi): {c.first_name} {c.last_name or ''}".strip()
            else:
                label = f"👤 Mijoz: {c.first_name} {c.last_name or ''}".strip()
                
            data.append({
                'id': f"customer_{c.id}",
                'name': label,
                'phone': c.phone,
                'custom_id': c.custom_id,
                'is_barter': is_barter,
                'supplier_debt': supplier_debt,
                'our_debt': float(supplier_debt) if is_barter else float(-c.debt_amount)
            })
            
        return json_response(data)

    elif request.method == 'POST':
        try:
            if request.content_type and 'multipart/form-data' in request.content_type:
                body = request.POST
                image = request.FILES.get('image')
            else:
                body = json.loads(request.body)
                image = None

            first_name = body.get('first_name', '').strip()
            last_name = body.get('last_name', '').strip()
            phone = body.get('phone', '').strip()
            custom_id = body.get('custom_id', '').strip()

            if not first_name or not phone:
                return json_response({'error': "Ism va telefon raqam majburiy!"}, status=400)

            # Telefon raqam orqali mavjudligini tekshiramiz
            if Customer.objects.filter(phone=phone).exists():
                customer = Customer.objects.get(phone=phone)
            else:
                if not custom_id:
                    digits = ''.join(filter(str.isdigit, phone))
                    custom_id = f"T-{digits[-4:] or random.randint(1000, 9999)}"
                    while Customer.objects.filter(custom_id=custom_id).exists():
                        custom_id = f"T-{random.randint(10000, 99999)}"

                customer = Customer.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    custom_id=custom_id,
                    image=image,
                    note="Taminotchi/Mijoz (T- prefiksli)"
                )
                create_user_for_customer(customer)

            label = f"Ta'minotchi: {customer.first_name} {customer.last_name or ''}".strip() if customer.custom_id.startswith('T-') else f"Mijoz: {customer.first_name} {customer.last_name or ''}".strip()

            return json_response({
                'id': f"customer_{customer.id}",
                'name': label,
                'custom_id': customer.custom_id,
                'phone': customer.phone,
                'our_debt': float(-customer.debt_amount)
            })
        except Exception as e:
            return json_response({'error': str(e)}, status=400)


# =====================================================================
# SO'YIM (CHORVA XARIDI) API
# =====================================================================
@api_view(['POST'])
@permission_classes([IsAdminUser])
@transaction.atomic
def api_slaughters_create(request):
    """Tezkor so'yim kiritish va omborga go'sht qo'shish"""
    try:
        body = request.data
        supplier_id = body.get('supplier_id')
        animal_type = body.get('animal_type')  # 'mol' yoki 'qoy'
        total_weight = Decimal(str(body.get('total_weight', 0)))
        purchase_price = Decimal(str(body.get('purchase_price', 0)))
        due_days = int(body.get('due_days', 21)) # defolt: 3 hafta (21 kun) Nasiya

        if not animal_type or total_weight <= 0 or purchase_price <= 0:
            return Response({'error': "Ma'lumotlar to'liq kiritilmadi!"}, status=status.HTTP_400_BAD_REQUEST)

        supplier = None
        customer = None
        if supplier_id:
            if str(supplier_id).startswith('customer_'):
                cust_id = int(str(supplier_id).replace('customer_', ''))
                customer = Customer.objects.get(id=cust_id)
            elif str(supplier_id).startswith('supplier_'):
                sup_id = int(str(supplier_id).replace('supplier_', ''))
                supplier = Supplier.objects.get(id=sup_id)
            else:
                try:
                    supplier = Supplier.objects.get(id=int(supplier_id))
                except (ValueError, Supplier.DoesNotExist):
                    pass

        # Slaughter yaratish
        due_date = timezone.now().date() + timezone.timedelta(days=due_days)
        slaughter = Slaughter.objects.create(
            supplier=supplier,
            customer=customer,
            animal_type=animal_type,
            total_weight=total_weight,
            purchase_price_per_kg=purchase_price,
            due_date=due_date
        )

        # Ta'minotchiga qarzimizni yozamiz / Mijoz qarzini kamaytiramiz
        if supplier:
            supplier.our_debt += slaughter.total_cost
            supplier.save()
        elif customer:
            customer.debt_amount -= slaughter.total_cost
            customer.save()
            
            # Log transaction to customer logs
            CustomerLog.objects.create(
                customer=customer,
                log_type='debt_pay',
                title="Go'sht sotib olindi (So'yim)",
                details={'message': f"So'yim #{slaughter.id} orqali mijozdan {total_weight} kg toza go'sht sotib olindi. Summa: {slaughter.total_cost:,} so'm."},
                amount=slaughter.total_cost
            )

        # Tegishli Product zaxirasini yangilash
        prod_name = "Mol go'shti" if animal_type == 'mol' else "Qo'y go'shti"
        product, created = Product.objects.get_or_create(
            name=prod_name,
            defaults={'price_per_kg': purchase_price + Decimal('15000.00')} # defolt sotuv narxi ustiga 15k
        )

        # Create StockBatch for yield decay tracking
        from .models import StockBatch
        StockBatch.objects.create(
            product=product,
            initial_quantity=total_weight,
            current_quantity=total_weight,
            purchase_price_per_kg=purchase_price
        )

        stock, created = Stock.objects.get_or_create(product=product)
        stock.quantity += total_weight
        stock.save()

        return Response({
            'status': 'success',
            'slaughter_id': slaughter.id,
            'total_cost': float(slaughter.total_cost),
            'due_date': slaughter.due_date.strftime('%d.%m.%Y'),
            'stock_new_quantity': float(stock.quantity)
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# =====================================================================
# SAVDO (KASSA SOTUV) API
# =====================================================================
# SAVDO (KASSA SOTUV) API
# =====================================================================
@api_view(['POST'])
@permission_classes([IsAdminUser])
@transaction.atomic
def api_sales_create(request):
    """Kassadan sotuvni amalga oshirish (Chegirma, Bonus, Nasiya)"""
    try:
        body = request.data
        customer_id = body.get('customer_id')
        payment_method = body.get('payment_method', 'naqd') # naqd, karta, qr, nasiya
        cart_items = body.get('items', []) # [{'product_id': 1, 'weight': 1.5}, ...]
        
        # Moliyaviy taqsimot
        total_amount = Decimal(str(body.get('total_amount', 0))) # asl tortilgan narxi
        discount_amount = Decimal(str(body.get('discount_amount', 0))) # kassir o'tib bergan chegirma
        bonus_used = Decimal(str(body.get('bonus_used', 0))) # bonus hisobidan yechilgan
        debt_added = Decimal(str(body.get('debt_added', 0))) # nasiyaga yozilgan qarz
        final_paid = Decimal(str(body.get('final_paid', 0))) # mijoz to'lagan toza pul

        if not cart_items:
            return Response({'error': "Savat bo'sh!"}, status=status.HTTP_400_BAD_REQUEST)

        if payment_method == 'nasiya' and not customer_id:
            return Response({'error': "Nasiya faqat ro'yxatdan o'tgan mijozlarga ruxsat etiladi!"}, status=status.HTTP_400_BAD_REQUEST)

        customer = None
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
            except Customer.DoesNotExist:
                return Response({'error': f"Tanlangan mijoz (ID: {customer_id}) ma'lumotlar bazasida topilmadi. U o'chirilgan bo'lishi mumkin!"}, status=status.HTTP_400_BAD_REQUEST)
            
            if bonus_used > 0 and bonus_used > customer.bonus_points:
                return Response({
                    'error': f"Mijozning bonus ballari yetarli emas! Mavjud bonus: {customer.bonus_points} ball, ishlatilmoqchi: {bonus_used} ball."
                }, status=status.HTTP_400_BAD_REQUEST)

            is_barter = hasattr(customer, 'supplier_profile') and customer.supplier_profile is not None
            if (payment_method == 'nasiya' or debt_added > 0) and not is_barter:
                if customer.is_blacklisted:
                    return Response({'error': "Ushbu mijoz qora ro'yxatga olingan! Nasiyaga sotish taqiqlanadi!"}, status=status.HTTP_400_BAD_REQUEST)
                new_total_debt = customer.debt_amount + debt_added
                if new_total_debt > customer.debt_limit:
                    return Response({
                        'error': f"Mijozning kredit limiti oshib ketdi! Joriy qarz: {customer.debt_amount.quantize(Decimal('1'))} so'm, Limiti: {customer.debt_limit.quantize(Decimal('1'))} so'm. Maksimal nasiya: {max(Decimal('0.00'), customer.debt_limit - customer.debt_amount).quantize(Decimal('1'))} so'm."
                    }, status=status.HTTP_400_BAD_REQUEST)

        # 1. Sotuv hujjatini yaratish
        sale = Sale.objects.create(
            customer=customer,
            total_amount=total_amount,
            discount_amount=discount_amount,
            bonus_used=bonus_used,
            debt_added=debt_added,
            final_paid=final_paid,
            payment_method=payment_method
        )

        # 2. Savatchadagi mahsulotlarni yaratish, zaxirani kamaytirish va batch FIFO
        items_log_details = []
        for item in cart_items:
            product = Product.objects.get(id=item.get('product_id'))
            weight = Decimal(str(item.get('weight', 0)))
            
            # Update Stock (deduct from parent product if defined)
            target_product = product.deduct_from if product.deduct_from else product
            stock, created = Stock.objects.get_or_create(product=target_product)
            stock.quantity -= weight
            stock.save()

            # Kam zaxira ogohlantirishini tekshirish
            try:
                from .telegram_bot import check_low_stock_alert
                check_low_stock_alert(target_product.name, float(stock.quantity))
            except Exception:
                pass  # Telegram xatoligi savdoni to'xtatmasligi kerak

            sale_item = SaleItem.objects.create(
                sale=sale,
                product=product,
                weight=weight,
                price_at_sale=product.price_per_kg
            )
            from .views import allocate_sale_to_batch
            allocate_sale_to_batch(sale_item, product, weight)

            items_log_details.append({
                'product_name': product.name,
                'weight': float(weight),
                'price': float(product.price_per_kg),
                'total': float(sale_item.item_total)
            })

        # 3. Mijoz balansini yangilash
        if customer:
            # Bonusni yechish
            if bonus_used > 0:
                customer.bonus_points -= int(bonus_used)
                CustomerLog.objects.create(
                    customer=customer,
                    log_type='bonus',
                    title=f"💎 Bonus ishlatildi (Chek #{sale.id})",
                    details={'sale_id': sale.id, 'description': "Sotuv yaxlitlashi yoki chegirma uchun yechildi"},
                    amount=bonus_used
                )

            is_barter = hasattr(customer, 'supplier_profile') and customer.supplier_profile is not None
            supplier = customer.supplier_profile if is_barter else None

            # Nasiya yozish
            if payment_method == 'nasiya':
                nasiya_sum = final_paid if final_paid > 0 else total_amount - discount_amount
                if is_barter:
                    supplier.our_debt -= nasiya_sum
                    supplier.save()
                    CustomerLog.objects.create(
                        customer=customer,
                        log_type='debt_pay',
                        title=f"🤝 Barter xarid (Chek #{sale.id})",
                        details={'sale_id': sale.id, 'description': "Bizning qarzimizdan chegirildi"},
                        amount=nasiya_sum
                    )
                    msg = f"🤝 *Baxmal Meat — Yangi Barter Sotuv*\n\n👤 *Chorvador:* {customer.first_name} {customer.last_name or ''}\n🆔 *Mijoz ID:* `{customer.custom_id}`\n\n💵 *Barter summasi:* {nasiya_sum.quantize(Decimal('1')):,} so'm\n📉 *Qolgan qarzimiz:* {supplier.our_debt.quantize(Decimal('1')):,} so'm"
                    send_telegram_notification(msg)
                else:
                    customer.debt_amount += nasiya_sum
                    customer.save()
                    CustomerLog.objects.create(
                        customer=customer,
                        log_type='debt_add',
                        title=f"📝 Nasiya xarid (Chek #{sale.id})",
                        details={'sale_id': sale.id, 'description': "Nasiyaga olingan go'sht mahsulotlari"},
                        amount=nasiya_sum
                    )
                    msg = f"📝 *Baxmal Meat — Yangi Nasiya Sotuv*\n\n👤 *Mijoz:* {customer.first_name} {customer.last_name or ''}\n🆔 *Mijoz ID:* `{customer.custom_id}`\n\n💵 *Qarz summasi:* {nasiya_sum.quantize(Decimal('1')):,} so'm\n📊 *Jami qarzi:* {customer.debt_amount.quantize(Decimal('1')):,} so'm"
                    send_telegram_notification(msg)
            elif debt_added > 0:
                if is_barter:
                    supplier.our_debt -= debt_added
                    supplier.save()
                    CustomerLog.objects.create(
                        customer=customer,
                        log_type='debt_pay',
                        title=f"🤝 Barter xarid (Chek #{sale.id})",
                        details={'sale_id': sale.id, 'description': "Qarzimizdan chegirildi"},
                        amount=debt_added
                    )
                else:
                    customer.debt_amount += debt_added
                    customer.save()
                    CustomerLog.objects.create(
                        customer=customer,
                        log_type='debt_add',
                        title=f"📝 Qismoniy nasiya (Chek #{sale.id})",
                        details={'sale_id': sale.id, 'description': "Qarzga yozilgan qism"},
                        amount=debt_added
                    )

            # 1% Cashback bonus yig'ish (faqat nasiya bo'lmagan to'lovlardan)
            if payment_method != 'nasiya' and final_paid > 0:
                earned_bonus = int(final_paid * Decimal('0.01'))
                if earned_bonus > 0:
                    customer.bonus_points += earned_bonus
                    CustomerLog.objects.create(
                        customer=customer,
                        log_type='bonus',
                        title=f"💎 Bonus yig'ildi (+{earned_bonus})",
                        details={'sale_id': sale.id, 'earned': earned_bonus},
                        amount=Decimal(str(earned_bonus))
                    )

            customer.save()

        # 4. Sotuv logini yozish (Elektron Chek JSON ko'rinishida)
        if customer:
            CustomerLog.objects.create(
                customer=customer,
                log_type='sale',
                title=f"🛒 Xarid (Chek #{sale.id})",
                details={
                    'sale_id': sale.id,
                    'items': items_log_details,
                    'total': float(total_amount),
                    'discount': float(discount_amount),
                    'bonus_used': float(bonus_used),
                    'debt_added': float(debt_added),
                    'final_paid': float(final_paid),
                    'payment_method': payment_method
                },
                amount=final_paid
            )

        return Response({
            'status': 'success',
            'sale_id': sale.id,
            'total_amount': float(total_amount),
            'final_paid': float(final_paid),
            'bonus_points': customer.bonus_points if customer else 0,
            'debt_amount': float(customer.debt_amount) if customer else 0.0
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# =====================================================================
# ESKI QARZLARNI TEZKOR KO'CHIRISH API
# =====================================================================
@csrf_exempt
@transaction.atomic
@user_passes_test(lambda u: u.is_superuser)
def api_debts_migrate(request):
    """Daftardagi eski mijoz/ta'minotchi qarzlarini ommaviy ko'chirish"""
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            entries = body.get('entries', []) # [{'name': '...', 'phone': '...', 'amount': 150000, 'direction': 'client/supplier'}]
            
            migrated_count = 0
            for item in entries:
                name = item.get('name', '').strip()
                phone = item.get('phone', '').strip()
                amount = Decimal(str(item.get('amount', 0)))
                direction = item.get('direction') # 'client' yoki 'supplier'

                if not name or amount <= 0:
                    continue

                if not phone:
                    phone = f"No-Phone-{random.randint(100000, 999999)}"

                if direction == 'client':
                    # Xaridor qarzini yaratish/yangilash
                    customer, created = Customer.objects.get_or_create(
                        phone=phone,
                        defaults={
                            'first_name': name,
                            'custom_id': f"M-{random.randint(1000, 9999)}",
                            'debt_amount': amount
                        }
                    )
                    if created:
                        create_user_for_customer(customer)
                    else:
                        customer.debt_amount += amount
                        customer.save()

                    CustomerLog.objects.create(
                        customer=customer,
                        log_type='debt_add',
                        title="📋 Daftardan ko'chirilgan qarz",
                        details={'comment': "Eski daftardan qarz ko'chirildi", 'migration_date': timezone.now().strftime('%d.%m.%Y')},
                        amount=amount
                    )
                    migrated_count += 1

                elif direction == 'supplier':
                    # Ta'minotchi qarzini yaratish/yangilash
                    supplier, created = Supplier.objects.get_or_create(
                        phone=phone,
                        defaults={
                            'first_name': name,
                            'custom_id': f"T-{random.randint(1000, 9999)}",
                            'our_debt': amount
                        }
                    )
                    if not created:
                        supplier.our_debt += amount
                        supplier.save()
                    migrated_count += 1

            return json_response({
                'status': 'success',
                'migrated_count': migrated_count
            })
        except Exception as e:
            return json_response({'error': str(e)}, status=400)

    return json_response({'error': "Faqat POST so'rovlar qabul qilinadi"}, status=405)


# =====================================================================
# QARZ TO'LOVINI QABUL QILISH API
# =====================================================================
@csrf_exempt
@transaction.atomic
@user_passes_test(lambda u: u.is_superuser)
def api_debts_pay(request):
    """Mijoz qarzini to'laganda (qabul qilish) yoki Ta'minotchiga qarzimizni to'laganda"""
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            pay_type = body.get('type') # 'client' yoki 'supplier'
            target_id = body.get('id')
            amount = Decimal(str(body.get('amount', 0)))

            if amount <= 0 or not target_id or not pay_type:
                return json_response({'error': "Noto'g'ri ma'lumotlar!"}, status=400)

            if pay_type == 'client':
                customer = Customer.objects.get(id=target_id)
                customer.debt_amount -= amount
                if customer.debt_amount < 0:
                    customer.debt_amount = Decimal('0.00')
                customer.save()

                CustomerLog.objects.create(
                    customer=customer,
                    log_type='debt_pay',
                    title="💸 Qarz to'landi (Kassa)",
                    details={'message': f"{amount} so'm qarz muvaffaqiyatli to'landi."},
                    amount=amount
                )
                return json_response({'status': 'success', 'new_debt': customer.debt_amount})

            elif pay_type == 'supplier':
                supplier = Supplier.objects.get(id=target_id)
                supplier.our_debt -= amount
                if supplier.our_debt < 0:
                    supplier.our_debt = Decimal('0.00')
                supplier.save()

                return json_response({'status': 'success', 'new_debt': supplier.our_debt})

        except Exception as e:
            return json_response({'error': str(e)}, status=400)

    return json_response({'error': "Faqat POST so'rovlar qabul qilinadi"}, status=405)


# =====================================================================
# KUNLIK HESOBOT (Z-REPORT) API
# =====================================================================
@user_passes_test(lambda u: u.is_superuser)
def api_reports_daily(request):
    """Z-Report: Kunlik savdo tahlili"""
    today = timezone.localtime(timezone.now()).date()
    sales = Sale.objects.filter(created_at__date=today)

    naqd = sales.filter(payment_method='naqd').aggregate(Sum('final_paid'))['final_paid__sum'] or Decimal('0.00')
    karta = sales.filter(payment_method='karta').aggregate(Sum('final_paid'))['final_paid__sum'] or Decimal('0.00')
    qr = sales.filter(payment_method='qr').aggregate(Sum('final_paid'))['final_paid__sum'] or Decimal('0.00')
    nasiya = sales.filter(payment_method='nasiya').aggregate(Sum('final_paid'))['final_paid__sum'] or Decimal('0.00') # agar nasiyada qisman to'lansa
    
    # Nasiyaga o'tgan jami qarz
    total_debt_added = sales.aggregate(Sum('debt_added'))['debt_added__sum'] or Decimal('0.00')
    # O'tib berilgan chegirmalar
    total_discounts = sales.aggregate(Sum('discount_amount'))['discount_amount__sum'] or Decimal('0.00')
    # Yechilgan bonuslar
    total_bonus_used = sales.aggregate(Sum('bonus_used'))['bonus_used__sum'] or Decimal('0.00')

    # Top sotilgan go'shtlar
    items = SaleItem.objects.filter(sale__created_at__date=today).values('product__name').annotate(
        total_weight=Sum('weight'),
        total_sales=Sum('item_total')
    ).order_by('-total_weight')

    # Kun davomida qilingan so'yimlar
    slaughters = Slaughter.objects.filter(created_at__date=today).aggregate(
        total_qty=Sum('total_weight'),
        total_cost=Sum('total_cost')
    )

    data = {
        'date': today.strftime('%d.%m.%Y'),
        'payment_methods': {
            'naqd': naqd,
            'karta': karta,
            'qr': qr,
            'nasiya': total_debt_added
        },
        'total_revenue': naqd + karta + qr,
        'total_discounts': total_discounts,
        'total_bonus_used': total_bonus_used,
        'slaughters': {
            'total_qty': slaughters['total_qty'] or 0.000,
            'total_cost': slaughters['total_cost'] or 0.00
        },
        'products_sold': list(items)
    }
    return json_response(data)


# =====================================================================
# QARZLARNI MUDDAT BO'YICHA TAHLILI (AGING DEBT) API
# =====================================================================
@user_passes_test(lambda u: u.is_superuser)
def api_reports_debt_aging(request):
    """Nasiya qarzlarining yoshi bo'yicha tahlil"""
    customers = Customer.objects.filter(debt_amount__gt=0).order_by('-debt_amount')
    data = []
    
    now = timezone.now()
    for c in customers:
        # Mijozning oxirgi qarz olgan vaqtini topamiz
        last_debt_log = CustomerLog.objects.filter(
            customer=c, 
            log_type='debt_add'
        ).order_by('-created_at').first()

        days_old = 0
        if last_debt_log:
            days_old = (now - last_debt_log.created_at).days

        # Qora ro'yxatni tekshirish va avtomat yangilash (30 kundan oshsa)
        if days_old > 30 and not c.is_blacklisted:
            c.is_blacklisted = True
            c.save()

        data.append({
            'id': c.id,
            'name': f"{c.first_name} {c.last_name or ''}".strip(),
            'phone': c.phone,
            'debt': c.debt_amount,
            'days_old': days_old,
            'is_blacklisted': c.is_blacklisted
        })

    return json_response(data)
# =====================================================================
# AI COPILOT / QASSOB AI YORDAMCHI (FREE GEMINI API)
# =====================================================================
@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def api_ai_copilot(request):
    """Free Gemini API yordamida do'kon hisobotlarini ovozli/matnli tahlil qilish"""
    if request.method != 'POST':
        return json_response({'error': "Faqat POST so'rovlar qabul qilinadi"}, status=405)

    user_question = ""
    if request.body:
        try:
            body = json.loads(request.body)
            user_question = body.get('question', '').strip()
        except Exception:
            pass

    # 1. Bazadan barcha kerakli statistikani jamlaymiz
    today = timezone.localtime(timezone.now()).date()
    
    # Mahsulot qoldiqlari
    stocks = Stock.objects.all().select_related('product')
    stock_summary = ", ".join([f"{s.product.name}: {s.quantity} kg" for s in stocks])

    # Umumiy qarzlar
    total_customer_debts = Customer.objects.aggregate(Sum('debt_amount'))['debt_amount__sum'] or Decimal('0.00')
    total_supplier_debts = Supplier.objects.aggregate(Sum('our_debt'))['our_debt__sum'] or Decimal('0.00')

    # Oxirgi savdolar (Bugungi)
    today_sales = Sale.objects.filter(created_at__date=today)
    total_revenue = today_sales.aggregate(Sum('final_paid'))['final_paid__sum'] or Decimal('0.00')
    total_debt_added = today_sales.aggregate(Sum('debt_added'))['debt_added__sum'] or Decimal('0.00')
    total_discounts = today_sales.aggregate(Sum('discount_amount'))['discount_amount__sum'] or Decimal('0.00')

    # Eski qarzga botgan eng xavfli 3 ta xaridor
    debtors = Customer.objects.filter(debt_amount__gt=0).order_by('-debt_amount')[:3]
    debtors_summary = ", ".join([f"{d.first_name} ({d.phone}): {d.debt_amount} so'm" for d in debtors])

    # Prompt yaratish
    prompt = f"""
    Siz "Baxmal Meat" go'sht do'konining aqlli sun'iy intellekt yordamchisisiz. Qassob va do'kon egasi (Islom aka)ga do'kondagi hozirgi holat bo'yicha o'zbek tilida (oddiy, tushunarli, samimiy va do'konchilik uslubida) hisobotlar, tahlil va maslahatlar bering.
    
    Hozirgi do'kon ko'rsatkichlari:
    1. Ombordagi qoldiqlar: {stock_summary}
    2. Mijozlarimizning bizdan jami qarzi (Nasiya debet): {total_customer_debts} so'm.
    3. Bizning chorvadorlarga (ta'minotchilarga) bo'lgan jami qarzimiz (Kredit): {total_supplier_debts} so'm.
    4. Bugungi naqd tushum: {total_revenue} so'm.
    5. Bugun berilgan yangi nasiya: {total_debt_added} so'm.
    6. Bugun chegirmalarga ketgan summa: {total_discounts} so'm.
    7. Eng katta qarzdor mijozlar: {debtors_summary}
    
    Sizdan Islom aka do'konni bu qarzlar botqog'idan qutqarish uchun strategiyalar so'ramoqda. Tahlilingizda albatta quyidagilarga to'xtaling:
    * Go'sht zaxirasining etarliligi.
    * Nasiya qarzlar xavfi: Xaridorlardan qarzni undirish bo'yicha amaliy tavsiyalar.
    * Chorvadorlar oldidagi katta qarzlarni kamaytirish bo'yicha strategiya (masalan, chorvadorlarning shaxsiy ehtiyojlari uchun go'sht mahsulotlarini bizdan barter/kontra-hisob orqali olib ketishlarini rag'batlantirish, to'lovlarni partiya sotilishiga qarab bo'lib-bo'lib yopish).
    * Limitlarni nazorat qilish bo'yicha maslahatlar.
    """

    from pos.models import AIChatMessage

    if user_question:
        prompt += f"\nFoydalanuvchi savoli: \"{user_question}\"\nIltimos, ushbu savolga do'kon ko'rsatkichlaridan foydalanib qisqa, tushunarli va aniq javob bering."
        AIChatMessage.objects.create(
            user=request.user,
            sender='user',
            message=user_question
        )
    else:
        prompt += "\nIltimos, do'konning umumiy joriy holati bo'yicha qisqacha tahlil va tavsiyalar bering."
        AIChatMessage.objects.create(
            user=request.user,
            sender='user',
            message="📊 Bugungi tahlil va maslahatlarni olish"
        )

    # Gemini API ga ulanishga urinamiz
    api_key = os.environ.get('GEMINI_API_KEY', '') # Agar muhitdan topilmasa
    if not api_key:
        if user_question:
            q_lower = user_question.lower()
            if "zaxira" in q_lower or "go'sht" in q_lower or "kam" in q_lower:
                fallback_advice = f"🥩 Ombordagi joriy zaxiralarimiz: {stock_summary}. Zaxirani doimiy nazorat qiling."
            elif "qarz" in q_lower or "qarzdor" in q_lower:
                fallback_advice = f"💸 Xaridorlarning jami qarzi: {total_customer_debts:,} so'm. Eng ko'p qarzdorlar: {debtors_summary}."
            else:
                fallback_advice = f"Sizning savolingiz: \"{user_question}\". AI maslahatchini faollashtirish uchun GEMINI_API_KEY o'rnatilishi lozim. Hozirgi umumiy holat: Bugun {total_revenue:,} so'mlik savdo bo'ldi, zaxiralar: {stock_summary}."
        else:
            fallback_advice = f"""Assalomu alaykum, Islom aka! Men "Baxmal Meat" AI maslahatchisiman.

Bugungi hisobotlarimizga ko'ra:
1. 🥩 **Zaxiralar:** Omborda go'sht zaxiralari normal holatda: {stock_summary}.
2. 💸 **Qarz xavfi:** Xaridorlarning bizdan jami qarzi **{total_customer_debts:,} so'm**ga yetdi. Eng ko'p qarzdor bo'lgan mijozlar: {debtors_summary}.
3. 📉 **Yo'qotishlar:** Bugun chegirmalar hisobiga **{total_discounts:,} so'm** foydadan kechildi.

Haqiqiy real-vaqtdagi AI maslahatlarini faollashtirish uchun tizim sozlamalariga Gemini API kalitini kiriting!"""
        AIChatMessage.objects.create(
            user=request.user,
            sender='bot',
            message=fallback_advice
        )
        return json_response({'advice': fallback_advice})

    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
        headers = {
            'Content-Type': 'application/json',
            'x-goog-api-key': api_key
        }
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            advice = result['candidates'][0]['content']['parts'][0]['text']
            AIChatMessage.objects.create(
                user=request.user,
                sender='bot',
                message=advice
            )
            return json_response({'advice': advice})
        else:
            err_msg = f"Gemini API xatosi: {response.text}"
            AIChatMessage.objects.create(
                user=request.user,
                sender='bot',
                message=f"❌ Xatolik yuz berdi: {err_msg}"
            )
            return json_response({'error': err_msg}, status=500)
    except Exception as e:
        err_msg = str(e)
        AIChatMessage.objects.create(
            user=request.user,
            sender='bot',
            message=f"❌ Tizim xatoligi: {err_msg}"
        )
        return json_response({'error': err_msg}, status=500)


@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def api_yield_decay_report(request):
    """Ombordagi go'sht partiyalarini va kunlik qurish zararini (Yield Decay) hisoblash"""
    from .models import StockBatch
    batches = StockBatch.objects.filter(current_quantity__gt=0).order_by('created_at')
    
    results = []
    total_loss_kg = Decimal('0.000')
    total_loss_cost = Decimal('0.00')

    for b in batches:
        days = b.get_days_passed()
        decayed_weight = b.get_decayed_weight()
        loss_kg = b.get_decay_loss()
        real_cost = b.get_real_cost_per_kg()
        
        loss_cost = loss_kg * b.purchase_price_per_kg
        
        total_loss_kg += loss_kg
        total_loss_cost += loss_cost

        results.append({
            'id': b.id,
            'product_name': b.product.name,
            'initial_quantity': float(b.initial_quantity),
            'current_quantity': float(b.current_quantity),
            'decayed_quantity': float(decayed_weight),
            'loss_kg': float(loss_kg),
            'purchase_price_per_kg': float(b.purchase_price_per_kg),
            'real_cost_per_kg': float(real_cost),
            'days_passed': days,
            'decay_rate_per_day': float(b.decay_rate_per_day),
            'loss_cost': float(loss_cost),
            'created_at': b.created_at.strftime('%d.%m.%Y %H:%M')
        })

    return json_response({
        'batches': results,
        'summary': {
            'total_loss_kg': float(total_loss_kg),
            'total_loss_cost': float(total_loss_cost),
            'active_batches_count': len(results)
        }
    })

@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def api_notifications(request):
    alerts = []
    
    # 1. Low stock
    from .models import Stock
    low_stocks = Stock.objects.filter(quantity__lt=5.000).select_related('product')
    for s in low_stocks:
        alerts.append({
            'type': 'low_stock',
            'icon': '⚠️',
            'title': "Zaxira kam qoldi",
            'body': f"{s.product.name} zaxirasi atigi {s.quantity:.3f} kg qoldi. Zaxirani to'ldirish tavsiya etiladi.",
        })
        
    # 2. High debtor
    from .models import Customer
    high_debtors = Customer.objects.filter(debt_amount__gt=1000000.00).order_by('-debt_amount')[:5]
    for c in high_debtors:
        alerts.append({
            'type': 'high_debt',
            'icon': '🚨',
            'title': "Mijoz qarzi ko'paydi",
            'body': f"{c.first_name} {c.last_name or ''} ning joriy qarzi {int(c.debt_amount):,} so'mga yetdi.",
        })
        
    # 3. Pending B2B Orders
    from .models import B2BOrder
    pending_b2b = B2BOrder.objects.filter(status='pending').count()
    if pending_b2b > 0:
        alerts.append({
            'type': 'pending_b2b',
            'icon': '📦',
            'title': "Yangi B2B buyurtma",
            'body': f"Restoranlardan {pending_b2b} ta yangi buyurtma kutilmoqda. Chat sahifasidan tasdiqlang.",
        })
        
    return json_response({
        'alerts': alerts,
        'count': len(alerts),
        'pending_b2b': pending_b2b
    })


@csrf_exempt
def customer_bot_webhook(request):
    """Foydalanuvchilar boti uchun Telegram Webhook qabul qiluvchi view"""
    if request.method == 'POST':
        try:
            update = json.loads(request.body)
            from .customer_bot import handle_customer_update
            handle_customer_update(update)
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)


@api_view(['POST'])
@permission_classes([AllowAny])
def api_b2b_create_with_proof(request):
    """Veb Saytdan chek rasmi bilan buyurtma berish API point."""
    try:
        customer_id = request.data.get('customer_id')
        product_id = request.data.get('product_id')
        weight = Decimal(str(request.data.get('requested_weight', '1')))
        delivery_type = request.data.get('delivery_type', 'delivery')
        delivery_address = request.data.get('delivery_address', '')
        proof_image = request.FILES.get('proof_image')

        from .models import Customer, Product, B2BOrder
        customer = Customer.objects.get(id=customer_id)
        product = Product.objects.get(id=product_id)

        order = B2BOrder.objects.create(
            customer=customer,
            product=product,
            requested_weight=weight,
            delivery_type=delivery_type,
            delivery_address=delivery_address,
            payment_proof_image=proof_image,
            status='payment_uploaded' if proof_image else 'pending',
            notes="Sayt orqali buyurtma berildi"
        )

        total_price = weight * product.price_per_kg

        # Notify Admin via Telegram Bot
        from .telegram_bot import send_message as send_admin_msg, CHAT_ID as ADMIN_CHAT_ID
        admin_text = (
            f"🛒 *YANGI SAYT BUYURTMASI!* (Buyurtma #{order.id})\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Mijoz:* {customer.first_name} {customer.last_name or ''}\n"
            f"🆔 *ID:* `{customer.custom_id}` | 📞 `{customer.phone}`\n\n"
            f"🥩 *Mahsulot:* {product.name} ({weight} kg)\n"
            f"💵 *Jami Summa:* `{total_price:,.0f}` so'm\n"
            f"🚗 *Yetkazish:* {order.get_delivery_type_display()} ({delivery_address})"
        )
        if ADMIN_CHAT_ID:
            send_admin_msg(ADMIN_CHAT_ID, admin_text)

        return Response({
            'status': 'ok',
            'order_id': order.id,
            'message': 'Buyurtmangiz muvaffaqiyatli qabul qilindi!'
        })
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_b2b_live_tracking(request, customer_id):
    """Mijozning aktiv buyurtmalari va real vaqt statusini olish."""
    try:
        from .models import B2BOrder
        orders = B2BOrder.objects.filter(customer_id=customer_id).order_by('-created_at')[:5]
        result = []
        for o in orders:
            result.append({
                'id': o.id,
                'product_name': o.product.name,
                'weight': float(o.requested_weight),
                'total_price': float(o.requested_weight * o.product.price_per_kg),
                'status': o.status,
                'status_display': o.get_status_display(),
                'delivery_type': o.get_delivery_type_display(),
                'delivery_address': o.delivery_address,
                'payment_proof_url': o.payment_proof_image.url if o.payment_proof_image else None,
                'created_at': o.created_at.strftime('%d.%m.%Y %H:%M')
            })
        return Response({'orders': result})
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_payment_settings(request):
    """Admin kiritgan to'lov rekvizitlari va QR kodlar ro'yxati API point."""
    try:
        from .models import PaymentSetting
        settings = PaymentSetting.objects.filter(is_active=True)
        data = []
        for s in settings:
            data.append({
                'id': s.id,
                'title': s.title,
                'card_number': s.card_number,
                'card_holder': s.card_holder,
                'qr_code_url': s.qr_code.url if s.qr_code else None,
                'instructions': s.instructions
            })
        return Response({'settings': data})
    except Exception as e:
        return Response({'error': str(e)}, status=400)


# =====================================================================
# AI MASOFA VA KURYERLIK KALKULYATORI & MARKETPLACE API
# =====================================================================
import math

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth radius in kilometers
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def api_calculate_delivery(request):
    """Do'kon va mijoz koordinatasi oralig'ida masofa (km) va kuryerlik haqini hisoblash API."""
    try:
        if request.method == 'POST':
            lat = request.data.get('latitude')
            lng = request.data.get('longitude')
            total_sum = Decimal(str(request.data.get('total_sum', 0)))
        else:
            lat = request.GET.get('lat') or request.GET.get('latitude')
            lng = request.GET.get('lng') or request.GET.get('longitude')
            total_sum = Decimal(str(request.GET.get('total_sum', 0)))

        if not lat or not lng:
            return Response({'error': "Lokatsiya koordinatalari berilmadi!"}, status=400)

        cust_lat = float(lat)
        cust_lng = float(lng)

        from .models import StoreSetting
        store = StoreSetting.objects.filter(is_active=True).first()
        if not store:
            store = StoreSetting.objects.create(
                name="Baxmal Meat Do'koni",
                latitude=41.2995,
                longitude=69.2401,
                base_delivery_fee=Decimal('10000.00'),
                fee_per_km=Decimal('3000.00'),
                min_free_delivery_amount=Decimal('500000.00')
            )

        distance = calculate_haversine_distance(store.latitude, store.longitude, cust_lat, cust_lng)
        
        # Check if free delivery applies
        if total_sum >= store.min_free_delivery_amount and total_sum > 0:
            fee = Decimal('0.00')
            is_free = True
        else:
            fee = store.base_delivery_fee + (Decimal(str(distance)) * store.fee_per_km)
            fee = fee.quantize(Decimal('1000.00')) # Round to nearest 1000 so'm
            is_free = False

        return Response({
            'status': 'success',
            'store_name': store.name,
            'store_address': store.address,
            'distance_km': distance,
            'delivery_fee': float(fee),
            'formatted_fee': f"{fee:,.0f} so'm" if not is_free else "Bepul (Aksiya)",
            'is_free': is_free
        })
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])
def api_courier_apply(request):
    """Mijozning kuryerlikka ariza berishi API."""
    try:
        user_ident = request.user.email if request.user.email else request.user.username
        from .models import Customer
        customer = Customer.objects.filter(Q(phone__iexact=user_ident) | Q(custom_id__iexact=user_ident)).first()
        if not customer:
            return Response({'error': "Mijoz profili topilmadi!"}, status=404)

        vehicle = request.data.get('vehicle', 'Moped/Skuter').strip()

        customer.courier_status = 'pending'
        customer.courier_vehicle = vehicle
        customer.save()

        # Send Telegram Admin alert
        from .telegram_bot import send_message as send_admin_msg, CHAT_ID as ADMIN_CHAT_ID
        admin_text = (
            f"🚴‍♂️ *YANGI KURYERLIK ARIZASI!*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Mijoz:* {customer.first_name} {customer.last_name or ''}\n"
            f"📞 *Tel:* `{customer.phone}` (ID: `{customer.custom_id}`)\n"
            f"🛵 *Transport:* {vehicle}\n\n"
            f"⏳ _Admin panelidan tasdiqlashingiz kutilmoqda._"
        )
        if ADMIN_CHAT_ID:
            send_admin_msg(ADMIN_CHAT_ID, admin_text)

        return Response({
            'status': 'success',
            'message': 'Arizangiz muvaffaqiyatli qabul qilindi! Admin tasdiqlashi bilan kuryerlik paneli ochiladi.'
        })
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_courier_orders(request):
    """Tasdiqlangan kuryer uchun ochiq buyurtmalar ro'yxati API."""
    try:
        user_ident = request.user.email if request.user.email else request.user.username
        from .models import Customer, B2BOrder
        customer = Customer.objects.filter(Q(phone__iexact=user_ident) | Q(custom_id__iexact=user_ident)).first()
        if not customer or not customer.is_courier:
            return Response({'error': "Ruxsat berilmadi! Siz kuryer sifatida tasdiqlanmagansiz."}, status=403)

        # Pending or approved delivery orders needing courier
        available_orders = B2BOrder.objects.filter(
            delivery_type='delivery',
            assigned_courier__isnull=True,
            status__in=['approved', 'preparing', 'payment_uploaded']
        ).order_by('-created_at')[:10]

        # Orders claimed by this courier
        my_deliveries = B2BOrder.objects.filter(
            assigned_courier=customer,
            status__in=['shipping', 'preparing', 'approved']
        ).order_by('-created_at')[:10]

        def serialize_order(o):
            return {
                'id': o.id,
                'customer_name': f"{o.customer.first_name} {o.customer.last_name or ''}".strip(),
                'customer_phone': o.customer.phone,
                'product_name': o.product.name,
                'weight': float(o.requested_weight),
                'total_price': float(o.requested_weight * o.product.price_per_kg),
                'delivery_address': o.delivery_address,
                'delivery_fee': float(o.delivery_fee),
                'distance_km': o.distance_km,
                'latitude': o.latitude,
                'longitude': o.longitude,
                'status': o.status,
                'status_display': o.get_status_display(),
                'created_at': o.created_at.strftime('%d.%m.%Y %H:%M')
            }

        return Response({
            'status': 'success',
            'available_orders': [serialize_order(o) for o in available_orders],
            'my_deliveries': [serialize_order(o) for o in my_deliveries]
        })
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])
def api_courier_accept_order(request):
    """Kuryer buyurtmani o'ziga biriktirib yetkazishni boshlashi API."""
    try:
        user_ident = request.user.email if request.user.email else request.user.username
        from .models import Customer, B2BOrder
        customer = Customer.objects.filter(Q(phone__iexact=user_ident) | Q(custom_id__iexact=user_ident)).first()
        if not customer or not customer.is_courier:
            return Response({'error': "Siz tasdiqlangan kuryer emassiz!"}, status=403)

        order_id = request.data.get('order_id')
        order = B2BOrder.objects.get(id=order_id)
        if order.assigned_courier and order.assigned_courier != customer:
            return Response({'error': "Ushbu buyurtma boshqa kuryer tomonidan olingan!"}, status=400)

        order.assigned_courier = customer
        order.status = 'shipping'
        order.save()

        # Send CustomerLog notification to customer
        from .models import CustomerLog
        CustomerLog.objects.create(
            customer=order.customer,
            log_type='bonus',
            title="Do'kon xabari",
            message=f"🚴‍♂️ <b>KURYER YO'LDA!</b><br>Buyurtmangiz #{order.id} kuryer ({customer.first_name}, tel: {customer.phone}) tomonidan olindi va yetkazilmoqda!",
            amount=Decimal('0.00')
        )

        return Response({
            'status': 'success',
            'message': f"Buyurtma #{order.id} o'zingizga biriktirildi! Omadli yetkazib berish tilaymiz!"
        })
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])
def api_courier_complete_order(request):
    """Kuryer buyurtmani yetkazib berib yakunlashi API."""
    try:
        user_ident = request.user.email if request.user.email else request.user.username
        from .models import Customer, B2BOrder
        customer = Customer.objects.filter(Q(phone__iexact=user_ident) | Q(custom_id__iexact=user_ident)).first()
        if not customer or not customer.is_courier:
            return Response({'error': "Ruxsat berilmadi!"}, status=403)

        order_id = request.data.get('order_id')
        order = B2BOrder.objects.get(id=order_id, assigned_courier=customer)

        order.status = 'completed'
        order.save()

        # Send CustomerLog notification
        from .models import CustomerLog
        CustomerLog.objects.create(
            customer=order.customer,
            log_type='bonus',
            title="Do'kon xabari",
            message=f"✅ <b>BUYURTMA YETKAZILDI!</b><br>Buyurtmangiz #{order.id} muvaffaqiyatli yetkazib berildi. Oshingiz halol bo'lsin!",
            amount=Decimal('0.00')
        )

        return Response({
            'status': 'success',
            'message': f"Buyurtma #{order.id} muvaffaqiyatli yetkazildi!"
        })
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@csrf_exempt
@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def api_trigger_stock_decay(request):
    """Sovuqxonadagi mahsulot partiyalarining kunlik qurish zararini (decay loss) hisoblash va kassa chiqimini shakllantirish."""
    try:
        from .models import StockBatch, CashTransaction
        active_batches = StockBatch.objects.filter(current_quantity__gt=0)
        
        total_loss_amount = Decimal("0.00")
        total_loss_weight = Decimal("0.000")
        updated_batches = []

        for batch in active_batches:
            days = batch.get_days_passed()
            if days <= 0:
                continue

            factor_yesterday = Decimal(str((1 - float(batch.decay_rate_per_day)/100.0) ** (days - 1)))
            weight_yesterday = (batch.current_quantity * factor_yesterday).quantize(Decimal('0.001'))

            weight_today = batch.get_decayed_weight()
            day_loss = (weight_yesterday - weight_today).quantize(Decimal('0.001'))

            if day_loss > 0:
                loss_cost = (day_loss * batch.purchase_price_per_kg).quantize(Decimal('0.01'))
                
                CashTransaction.objects.create(
                    transaction_type='out',
                    amount=loss_cost,
                    category='expense',
                    payment_method='naqd',
                    description=f"Zaxira qurish zarari: {batch.product.name} (Partiya #{batch.id}) - {day_loss} kg"
                )

                total_loss_amount += loss_cost
                total_loss_weight += day_loss
                
                # Update actual batch quantity
                batch.current_quantity = weight_today
                batch.save()

                updated_batches.append({
                    'batch_id': batch.id,
                    'product_name': batch.product.name,
                    'loss_kg': float(day_loss),
                    'loss_cost': float(loss_cost),
                    'new_cost_per_kg': float(batch.get_real_cost_per_kg())
                })

        return Response({
            'status': 'success',
            'message': f"Zaxira qurish zarari qayta hisoblandi. Jami yo'qotish: {total_loss_weight} kg ({total_loss_amount:,.0f} so'm)",
            'total_loss_weight': float(total_loss_weight),
            'total_loss_amount': float(total_loss_amount),
            'updated_batches': updated_batches
        })
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=400)
