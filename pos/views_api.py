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

from .models import Supplier, Product, Stock, Slaughter, Customer, Sale, SaleItem, CustomerLog, CashTransaction, CustomerSpecialPrice
from .serializers import (
    ProductSerializer, CustomerSerializer, SupplierSerializer,
    SlaughterSerializer, SaleSerializer, StockSerializer
)
from django.contrib.auth.decorators import user_passes_test
from .permissions import staff_required, admin_required, is_staff_or_admin, is_admin
from .views import create_user_for_customer


# Decimal hisob-kitoblar uchun JSON serializator helper
def decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def json_response(data, status=200):
    return JsonResponse(data, safe=False, status=status, json_dumps_params={'default': decimal_serializer})

def send_telegram_notification(text):
    import sys
    if 'test' in sys.argv:
        return True

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
    if not bot_token or not chat_id:
        print("Telegram bot token or chat ID is not set. Skipping notification.")
        return False

    def _do_send():
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"Telegram notification error: {e}")

    import threading
    t = threading.Thread(target=_do_send, daemon=True)
    t.start()
    return True


def send_telegram_location(latitude, longitude):
    """Admin Telegram kanaliga mijoz lokatsiyasini (pin/map) yuborish."""
    import sys
    if 'test' in sys.argv:
        return True

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8898055369:AAFbUW9nLVRXwG-xd0oP1ftQ5vZpTjcL4x8')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '-1004312267841')
    if not bot_token or not chat_id:
        return False

    def _do_send():
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendLocation"
            payload = {
                'chat_id': chat_id,
                'latitude': float(latitude),
                'longitude': float(longitude)
            }
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"Telegram location send error: {e}")

    import threading
    t = threading.Thread(target=_do_send, daemon=True)
    t.start()
    return True

# =====================================================================
# MAHSULOTLAR API
# =====================================================================
@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
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
@permission_classes([AllowAny])
def api_customers(request):
    """Mijozlarni qidirish (GET) yoki yangi mijoz yaratish (POST)"""
    if request.method == 'GET':
        query = request.GET.get('q', '').strip()
        customers = Customer.objects.all().order_by('-id')
        if query:
            customers = customers.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(phone__icontains=query) |
                Q(custom_id__icontains=query)
            )
            limit = 50
        else:
            limit = 500
        serializer = CustomerSerializer(customers[:limit], many=True)
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
@user_passes_test(is_staff_or_admin)
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
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
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
# GO'SHTNI NIMTALASH VA ZAXIRAGA TAQSIMLASH API
# =====================================================================
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def api_cutting_distribute(request):
    """
    Go'shtni Nimtalash Kalkulyatoridan zaxiraga taqsimlash:
    Tana go'shtini bo'laklarga (lahm, suyakli, charvi, qiyma va h.k.) ajratib,
    har bir mahsulot zaxirasini yangilash va partiyalarini yaratish.
    """
    try:
        from .models import Product, Stock, StockBatch
        data = request.data
        cuts = data.get('cuts', [])
        carcass_weight = Decimal(str(data.get('carcass_weight', 0)))
        total_cost = Decimal(str(data.get('total_cost', 0)))

        if not cuts:
            return Response({'status': 'error', 'message': "Nimtalash qismlari kiritilmadi!"}, status=status.HTTP_400_BAD_REQUEST)

        distributed_items = []
        telegram_lines = []
        total_cut_weight = Decimal('0.000')

        for c in cuts:
            name = str(c.get('product_name', '')).strip()
            weight = Decimal(str(c.get('weight', 0)))
            selling_price = Decimal(str(c.get('selling_price', 0)))
            cost_per_kg = Decimal(str(c.get('cost_per_kg', 0)))

            if not name or weight <= 0:
                continue

            total_cut_weight += weight

            # Get or create product
            product, created = Product.objects.get_or_create(
                name=name,
                defaults={'price_per_kg': selling_price, 'is_active': True}
            )
            if not created and selling_price > 0:
                product.price_per_kg = selling_price
                product.save()

            # Update stock
            stock, _ = Stock.objects.get_or_create(product=product)
            stock.quantity += weight
            stock.save()

            # Create StockBatch for yield decay & freshness tracking
            StockBatch.objects.create(
                product=product,
                initial_quantity=weight,
                current_quantity=weight,
                purchase_price_per_kg=cost_per_kg if cost_per_kg > 0 else Decimal('1000.00')
            )

            distributed_items.append({
                'product_id': product.id,
                'product_name': product.name,
                'weight': float(weight),
                'cost_per_kg': float(cost_per_kg),
                'selling_price': float(selling_price),
                'new_stock': float(stock.quantity)
            })

            telegram_lines.append(f"🥩 <b>{product.name}:</b> {weight:.1f} kg (@{selling_price:,.0f} so'm)")

        # Send Telegram notification
        try:
            from .telegram_bot import send_message, CHAT_ID
            if CHAT_ID:
                expected_revenue = sum(float(c.get('weight', 0)) * float(c.get('selling_price', 0)) for c in cuts)
                profit = expected_revenue - float(total_cost)
                margin = (profit / float(total_cost) * 100) if float(total_cost) > 0 else 0

                msg = (
                    f"🔪 <b>YANGI GO'SHT NIMTALANDI VA ZAXIRAGA QABUL QILINDI!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📦 <b>Tana Go'shti Vazni:</b> {carcass_weight:.1f} kg\n"
                    f"💰 <b>Umumiy Tannarx:</b> {total_cost:,.0f} so'm\n\n"
                    f"<b>Nimtalangan bo'laklar:</b>\n" + "\n".join(telegram_lines) + "\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💵 <b>Kutilayotgan Tushum:</b> {expected_revenue:,.0f} so'm\n"
                    f"📈 <b>Kutilayotgan Sof Foyda:</b> +{profit:,.0f} so'm (+{margin:.1f}%)\n"
                    f"✅ <i>Barcha mahsulotlar zaxirasi avtomatik yangilandi.</i>"
                )
                send_message(CHAT_ID, msg, parse_mode='HTML')
        except Exception as tg_err:
            print(f"[Cutting TG Error]: {tg_err}")

        return Response({
            'status': 'success',
            'message': "Go'sht muvaffaqiyatli nimtalandi va mahsulotlar zaxirasiga taqsimlandi!",
            'distributed_items': distributed_items,
            'total_cut_weight': float(total_cut_weight)
        })
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# =====================================================================
# SAVDO (KASSA SOTUV) API
# =====================================================================
# SAVDO (KASSA SOTUV) API
# =====================================================================
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def api_sales_create(request):
    """Kassadan sotuvni amalga oshirish (Chegirma, Bonus, Nasiya, Aralash/Split)"""
    try:
        body = request.data
        customer_id = body.get('customer_id')
        payment_method = body.get('payment_method', 'naqd') # naqd, karta, qr, nasiya, aralash
        cart_items = body.get('items', []) # [{'product_id': 1, 'weight': 1.5}, ...]
        
        # Moliyaviy taqsimot
        total_amount = Decimal(str(body.get('total_amount', 0))) # asl tortilgan narxi
        discount_amount = Decimal(str(body.get('discount_amount', 0))) # kassir o'tib bergan chegirma
        bonus_used = Decimal(str(body.get('bonus_used', 0))) # bonus hisobidan yechilgan
        debt_added = Decimal(str(body.get('debt_added', 0))) # nasiyaga yozilgan qarz
        final_paid = Decimal(str(body.get('final_paid', 0))) # mijoz to'lagan toza pul

        paid_naqd = Decimal(str(body.get('paid_naqd', 0)))
        paid_karta = Decimal(str(body.get('paid_karta', 0)))
        paid_qr = Decimal(str(body.get('paid_qr', 0)))

        if payment_method == 'aralash':
            final_paid = paid_naqd + paid_karta + paid_qr
            # Hisoblangan qoldiq agar to'liq to'lanmagan bo'lsa qarzga o'tadi
            net_need_pay = max(Decimal('0.00'), total_amount - discount_amount - bonus_used)
            if final_paid < net_need_pay:
                debt_added = net_need_pay - final_paid
        elif payment_method == 'naqd':
            paid_naqd = final_paid
        elif payment_method == 'karta':
            paid_karta = final_paid
        elif payment_method == 'qr':
            paid_qr = final_paid
        elif payment_method == 'nasiya':
            debt_added = max(Decimal('0.00'), total_amount - discount_amount - bonus_used)
            final_paid = Decimal('0.00')

        if not cart_items:
            return Response({'error': "Savat bo'sh!"}, status=status.HTTP_400_BAD_REQUEST)

        if (payment_method == 'nasiya' or debt_added > 0) and not customer_id:
            return Response({'error': "Nasiya yoki qarzli to'lov faqat ro'yxatdan o'tgan mijozlarga ruxsat etiladi!"}, status=status.HTTP_400_BAD_REQUEST)

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
        from .models import CashierShift
        active_shift = CashierShift.objects.filter(is_open=True).order_by('-opened_at').first()

        sale = Sale.objects.create(
            customer=customer,
            shift=active_shift,
            total_amount=total_amount,
            discount_amount=discount_amount,
            bonus_used=bonus_used,
            debt_added=debt_added,
            final_paid=final_paid,
            paid_naqd=paid_naqd,
            paid_karta=paid_karta,
            paid_qr=paid_qr,
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

            # Item custom selling price (choyxona / maxsus / savatda tahrirlangan narx)
            item_price = Decimal(str(item.get('price_per_kg', item.get('price_at_sale', product.price_per_kg))))
            if item_price <= 0:
                item_price = product.price_per_kg

            sale_item = SaleItem.objects.create(
                sale=sale,
                product=product,
                weight=weight,
                price_at_sale=item_price
            )
            from .views import allocate_sale_to_batch
            allocate_sale_to_batch(sale_item, product, weight)

            items_log_details.append({
                'product_name': product.name,
                'weight': float(weight),
                'price': float(item_price),
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

            # Send Telegram electronic receipt to customer
            if customer.telegram_chat_id:
                try:
                    from pos.customer_bot import send_message as send_cust_tg_msg
                    items_summary = "\n".join([f"  • {it['product_name']}: {it['weight']:.2f} kg × {it['price']:,.0f} = {it['total']:,.0f} so'm" for it in items_log_details])
                    chek_text = (
                        f"🧾 *XARIDINGIZ UCHUN RAHMAT!* (Chek #{sale.id})\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"{items_summary}\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"💰 *Jami summa:* `{total_amount:,.0f} so'm`\n"
                        f"💳 *To'lov turi:* {payment_method.upper()} (`{final_paid:,.0f} so'm`)\n"
                    )
                    if debt_added > 0 or payment_method == 'nasiya':
                        chek_text += f"📋 *Nasiya (qarz):* `{customer.debt_amount:,.0f} so'm`\n"
                    if customer.bonus_points > 0:
                        chek_text += f"💎 *Mavjud bonus:* `{customer.bonus_points} ball`\n"
                    chek_text += "\n🥩 *Baxmal Meat jamoasi xaridingizga baraka tilaydi!*"
                    send_cust_tg_msg(customer.telegram_chat_id, chek_text)
                except Exception as tg_e:
                    print(f"[Sale Customer TG Push Error]: {tg_e}")

        # Send Telegram notification to Admin group
        try:
            from pos.telegram_bot import send_message as send_adm_tg_msg, CHAT_ID
            cust_name = f"{customer.first_name} {customer.last_name or ''} ({customer.phone})" if customer else "Noma'lum xaridor"
            adm_sale_text = (
                f"🛒 *YANGI KASSA SOTUVI!* (Chek #{sale.id})\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 *Xaridor:* {cust_name}\n"
                f"💰 *Tushum:* `{final_paid:,.0f} so'm` ({payment_method.upper()})\n"
                f"🥩 *Jami summa:* `{total_amount:,.0f} so'm`\n"
            )
            if debt_added > 0:
                adm_sale_text += f"📋 *Nasiyaga qo'shildi:* `{debt_added:,.0f} so'm`\n"
            send_adm_tg_msg(CHAT_ID, adm_sale_text)
        except Exception as tg_e:
            print(f"[Sale Admin TG Push Error]: {tg_e}")

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
# SAVDONI BEKOR QILISH (VOID / UNDO SALE) API
# =====================================================================
@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def api_sales_last(request):
    """Oxirgi amalga oshirilgan savdo ma'lumotlarini olish"""
    sale = Sale.objects.order_by('-id').prefetch_related('items__product', 'customer').first()
    if not sale:
        return Response({'status': 'error', 'message': "Hali hech qanday savdo amalga oshirilmagan."}, status=status.HTTP_404_NOT_FOUND)

    items_list = []
    total_weight = Decimal('0.000')
    for it in sale.items.all():
        total_weight += it.weight
        items_list.append({
            'product_name': it.product.name,
            'weight': float(it.weight),
            'price': float(it.price_at_sale),
            'total': float(it.item_total)
        })

    cust_name = f"{sale.customer.first_name} {sale.customer.last_name or ''}".strip() if sale.customer else "Mijozsiz (Naqd)"

    return Response({
        'status': 'success',
        'sale_id': sale.id,
        'created_at': sale.created_at.strftime('%d.%m.%Y %H:%M'),
        'customer_name': cust_name,
        'total_amount': float(sale.total_amount),
        'final_paid': float(sale.final_paid),
        'payment_method': sale.payment_method,
        'total_weight': float(total_weight),
        'items': items_list
    })


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def api_sales_void(request, sale_id=None):
    """Xato kiritilgan savdoni bekor qilish (ombor zaxirasi va mijoz hisobini qaytarish)"""
    try:
        body = request.data or {}
        req_id = sale_id or body.get('sale_id')

        if req_id and str(req_id).isdigit():
            sale = Sale.objects.filter(id=int(req_id)).first()
        else:
            sale = Sale.objects.order_by('-id').first()

        if not sale:
            return Response({'error': "Bekor qilish uchun savdo topilmadi!"}, status=status.HTTP_404_NOT_FOUND)

        old_sale_id = sale.id
        old_total = float(sale.total_amount)
        customer = sale.customer

        # 1. Mahsulot zaxirasini omborga qaytarish
        restored_items = []
        for it in sale.items.all():
            target_product = it.product.deduct_from if it.product.deduct_from else it.product
            stock, _ = Stock.objects.get_or_create(product=target_product)
            stock.quantity += it.weight
            stock.save()
            restored_items.append(f"{it.product.name} (+{it.weight:.3f} kg)")

        # 2. Mijoz qarz va bonuslarini qaytarish
        if customer:
            is_barter = hasattr(customer, 'supplier_profile') and customer.supplier_profile is not None
            supplier = customer.supplier_profile if is_barter else None

            if sale.payment_method == 'nasiya':
                nasiya_sum = sale.final_paid if sale.final_paid > 0 else (sale.total_amount - sale.discount_amount)
                if is_barter and supplier:
                    supplier.our_debt += nasiya_sum
                    supplier.save()
                else:
                    customer.debt_amount = max(Decimal('0.00'), customer.debt_amount - nasiya_sum)
            elif sale.debt_added > 0:
                if is_barter and supplier:
                    supplier.our_debt += sale.debt_added
                    supplier.save()
                else:
                    customer.debt_amount = max(Decimal('0.00'), customer.debt_amount - sale.debt_added)

            if sale.bonus_used > 0:
                customer.bonus_points += int(sale.bonus_used)

            # Cashback bonus qaytarib olinadi
            if sale.payment_method != 'nasiya' and sale.final_paid > 0:
                earned_bonus = int(sale.final_paid * Decimal('0.01'))
                if earned_bonus > 0:
                    customer.bonus_points = max(0, customer.bonus_points - earned_bonus)

            customer.save()

            CustomerLog.objects.create(
                customer=customer,
                log_type='sale',
                title=f"❌ Savdo bekor qilindi (Chek #{old_sale_id})",
                details={'sale_id': old_sale_id, 'reason': "Kassir tomonidan bekor qilindi", 'restored_items': restored_items},
                amount=-sale.final_paid
            )

        # 3. Savdoni o'chirish
        sale.delete()

        # 4. Admin telegram xabarnoma
        try:
            from pos.telegram_bot import send_message as send_adm_tg_msg, CHAT_ID
            items_str = ", ".join(restored_items) if restored_items else "Go'sht mahsulotlari"
            send_adm_tg_msg(CHAT_ID, f"⚠️ *SAVDO BEKOR QILINDI!*\nChek: `#{old_sale_id}`\nSumma: `{old_total:,.0f} so'm`\nQaytarilgan: {items_str}\nOmbor zaxirasi va balanslar qaytarildi.")
        except Exception:
            pass

        return Response({
            'status': 'success',
            'message': f"Chek #{old_sale_id} ({old_total:,.0f} so'm) muvaffaqiyatli bekor qilindi! Go'sht zaxirasi omborga qaytarildi.",
            'voided_sale_id': old_sale_id
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def api_sales_detail(request, sale_id):
    """Bitta savdo (chek) to'liq ma'lumotlarini olish"""
    sale = Sale.objects.filter(id=sale_id).prefetch_related('items__product', 'customer').first()
    if not sale:
        return Response({'status': 'error', 'message': f"Chek #{sale_id} topilmadi!"}, status=status.HTTP_404_NOT_FOUND)

    items_list = []
    for it in sale.items.all():
        items_list.append({
            'id': it.id,
            'product_id': it.product.id,
            'product_name': it.product.name,
            'weight': float(it.weight),
            'price': float(it.price_at_sale),
            'total': float(it.item_total)
        })

    products_list = []
    for p in Product.objects.filter(is_active=True):
        products_list.append({
            'id': p.id,
            'name': p.name,
            'price_per_kg': float(p.price_per_kg)
        })

    customers_list = []
    for c in Customer.objects.order_by('-id')[:30]:
        customers_list.append({
            'id': c.id,
            'name': f"{c.first_name} {c.last_name or ''}".strip(),
            'phone': c.phone,
            'custom_id': c.custom_id,
            'debt_amount': float(c.debt_amount)
        })

    return Response({
        'status': 'success',
        'sale': {
            'id': sale.id,
            'created_at': sale.created_at.strftime('%d.%m.%Y %H:%M'),
            'payment_method': sale.payment_method,
            'total_amount': float(sale.total_amount),
            'discount_amount': float(sale.discount_amount),
            'bonus_used': float(sale.bonus_used),
            'debt_added': float(sale.debt_added),
            'final_paid': float(sale.final_paid),
            'paid_naqd': float(sale.paid_naqd),
            'paid_karta': float(sale.paid_karta),
            'paid_qr': float(sale.paid_qr),
            'customer_id': sale.customer.id if sale.customer else None,
            'customer_name': f"{sale.customer.first_name} {sale.customer.last_name or ''}".strip() if sale.customer else None,
            'items': items_list
        },
        'available_products': products_list,
        'available_customers': customers_list
    })


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def api_sales_edit(request, sale_id=None):
    """Savdoni tahrirlash (Vazn, Narx, To'lov turi, Xaridorni o'zgartirish va ombor zaxirasini moslashtirish)"""
    try:
        body = request.data or {}
        req_id = sale_id or body.get('sale_id')
        if not req_id:
            return Response({'error': "Savdo ID kiritilmagan!"}, status=status.HTTP_400_BAD_REQUEST)

        sale = Sale.objects.filter(id=int(req_id)).prefetch_related('items__product', 'customer').first()
        if not sale:
            return Response({'error': f"Chek #{req_id} topilmadi!"}, status=status.HTTP_404_NOT_FOUND)

        old_customer = sale.customer
        old_payment_method = sale.payment_method
        old_final_paid = sale.final_paid
        old_debt_added = sale.debt_added
        old_bonus_used = sale.bonus_used
        old_total = sale.total_amount

        # 1. STEP A: Revert old stock deductions
        for it in sale.items.all():
            target_product = it.product.deduct_from if it.product.deduct_from else it.product
            stock, _ = Stock.objects.get_or_create(product=target_product)
            stock.quantity += it.weight
            stock.save()

        # 2. STEP B: Revert old customer financials
        if old_customer:
            is_barter = hasattr(old_customer, 'supplier_profile') and old_customer.supplier_profile is not None
            old_supplier = old_customer.supplier_profile if is_barter else None

            if old_payment_method == 'nasiya':
                old_nasiya = old_final_paid if old_final_paid > 0 else (old_total - sale.discount_amount)
                if is_barter and old_supplier:
                    old_supplier.our_debt += old_nasiya
                    old_supplier.save()
                else:
                    old_customer.debt_amount = max(Decimal('0.00'), old_customer.debt_amount - old_nasiya)
            elif old_debt_added > 0:
                if is_barter and old_supplier:
                    old_supplier.our_debt += old_debt_added
                    old_supplier.save()
                else:
                    old_customer.debt_amount = max(Decimal('0.00'), old_customer.debt_amount - old_debt_added)

            if old_bonus_used > 0:
                old_customer.bonus_points += int(old_bonus_used)

            if old_payment_method != 'nasiya' and old_final_paid > 0:
                earned = int(old_final_paid * Decimal('0.01'))
                if earned > 0:
                    old_customer.bonus_points = max(0, old_customer.bonus_points - earned)

            old_customer.save()

        # 3. STEP C: Apply new changes
        new_customer_id = body.get('customer_id')
        new_customer = None
        if new_customer_id:
            try:
                new_customer = Customer.objects.get(id=int(new_customer_id))
            except (Customer.DoesNotExist, ValueError):
                pass

        new_payment_method = body.get('payment_method', old_payment_method)
        new_items_data = body.get('items', [])

        if not new_items_data:
            return Response({'error': "Mahsulotlar ro'yxati bo'sh bo'lishi mumkin emas!"}, status=status.HTTP_400_BAD_REQUEST)

        # Delete old items
        sale.items.all().delete()

        new_total_amount = Decimal('0.00')
        new_items_log = []

        for item_data in new_items_data:
            p_id = item_data.get('product_id')
            p_obj = Product.objects.get(id=p_id)
            p_weight = Decimal(str(item_data.get('weight', 0)))
            p_price = Decimal(str(item_data.get('price', p_obj.price_per_kg)))

            if p_weight <= 0:
                continue

            item_tot = (p_weight * p_price).quantize(Decimal('0.01'))
            new_total_amount += item_tot

            # Deduct new stock
            target_product = p_obj.deduct_from if p_obj.deduct_from else p_obj
            stock, _ = Stock.objects.get_or_create(product=target_product)
            stock.quantity -= p_weight
            stock.save()

            sale_item = SaleItem.objects.create(
                sale=sale,
                product=p_obj,
                weight=p_weight,
                price_at_sale=p_price
            )

            new_items_log.append({
                'product_name': p_obj.name,
                'weight': float(p_weight),
                'price': float(p_price),
                'total': float(item_tot)
            })

        # Calculate final paid, paid breakdown and debt
        new_paid_naqd = Decimal('0.00')
        new_paid_karta = Decimal('0.00')
        new_paid_qr = Decimal('0.00')

        if new_payment_method == 'aralash':
            new_paid_naqd = Decimal(str(body.get('paid_naqd', 0)))
            new_paid_karta = Decimal(str(body.get('paid_karta', 0)))
            new_paid_qr = Decimal(str(body.get('paid_qr', 0)))
            new_final_paid = new_paid_naqd + new_paid_karta + new_paid_qr
            unpaid = max(Decimal('0.00'), new_total_amount - new_final_paid)
            new_debt_added = unpaid
            new_discount = Decimal('0.00')
        elif new_payment_method == 'nasiya':
            new_final_paid = Decimal('0.00')
            new_debt_added = new_total_amount
            new_discount = Decimal('0.00')
        else:
            raw_final_paid = body.get('final_paid')
            new_final_paid = Decimal(str(raw_final_paid)) if raw_final_paid is not None else new_total_amount
            new_discount = max(Decimal('0.00'), new_total_amount - new_final_paid)
            new_debt_added = Decimal('0.00')
            if new_payment_method == 'naqd':
                new_paid_naqd = new_final_paid
            elif new_payment_method == 'karta':
                new_paid_karta = new_final_paid
            elif new_payment_method == 'qr':
                new_paid_qr = new_final_paid

        # Update Sale model
        sale.customer = new_customer
        sale.payment_method = new_payment_method
        sale.total_amount = new_total_amount
        sale.discount_amount = new_discount
        sale.final_paid = new_final_paid
        sale.paid_naqd = new_paid_naqd
        sale.paid_karta = new_paid_karta
        sale.paid_qr = new_paid_qr
        sale.debt_added = new_debt_added
        sale.bonus_used = Decimal('0.00')
        sale.save()

        # 4. STEP D: Apply new customer financials
        if new_customer:
            is_barter = hasattr(new_customer, 'supplier_profile') and new_customer.supplier_profile is not None
            new_supplier = new_customer.supplier_profile if is_barter else None

            if new_payment_method == 'nasiya':
                nasiya_val = new_total_amount
                if is_barter and new_supplier:
                    new_supplier.our_debt -= nasiya_val
                    new_supplier.save()
                else:
                    new_customer.debt_amount += nasiya_val
            elif new_debt_added > 0:
                if is_barter and new_supplier:
                    new_supplier.our_debt -= new_debt_added
                    new_supplier.save()
                else:
                    new_customer.debt_amount += new_debt_added

            # Cashback bonus
            if new_payment_method != 'nasiya' and sale.final_paid > 0:
                earned = int(sale.final_paid * Decimal('0.01'))
                if earned > 0:
                    new_customer.bonus_points += earned

            new_customer.save()

            CustomerLog.objects.create(
                customer=new_customer,
                log_type='sale',
                title=f"✏️ Savdo tahrirlandi (Chek #{sale.id})",
                details={'sale_id': sale.id, 'new_total': float(new_total_amount), 'items': new_items_log},
                amount=sale.final_paid
            )

        # 5. Telegram notification
        try:
            from pos.telegram_bot import send_message as send_adm_tg_msg, CHAT_ID
            c_name = f"{new_customer.first_name} {new_customer.last_name or ''}" if new_customer else "Mijozsiz (Naqd)"
            send_adm_tg_msg(CHAT_ID, f"✏️ *SAVDO TAHRIRLANDI!*\nChek: `#{sale.id}`\nXaridor: {c_name}\nYangi summa: `{new_total_amount:,.0f} so'm` ({new_payment_method.upper()})\nOmbor zaxirasi avtomatik qayta muvofiqlashtirildi.")
        except Exception:
            pass

        return Response({
            'status': 'success',
            'message': f"Chek #{sale.id} muvaffaqiyatli tahrirlandi va zaxira qayta hisoblandi!",
            'sale': {
                'id': sale.id,
                'total_amount': float(sale.total_amount),
                'final_paid': float(sale.final_paid),
                'payment_method': sale.payment_method,
                'customer_name': f"{new_customer.first_name} {new_customer.last_name or ''}".strip() if new_customer else "Mijozsiz (Naqd)"
            }
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# =====================================================================
# KASSA SMENASI (CASHIER SHIFT & Z-REPORT) API
# =====================================================================
@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def api_shift_current(request):
    """Joriy faol smena holati va jonli hisob-kitoblarini olish"""
    from .models import CashierShift, CashTransaction
    shift = CashierShift.objects.filter(is_open=True).order_by('-opened_at').first()
    if not shift:
        return Response({'is_open': False})

    sales = Sale.objects.filter(shift=shift)
    
    # Pure & Split calculations
    naqd_pure = sales.filter(payment_method='naqd').aggregate(s=Sum('final_paid'))['s'] or Decimal('0.00')
    karta_pure = sales.filter(payment_method='karta').aggregate(s=Sum('final_paid'))['s'] or Decimal('0.00')
    qr_pure = sales.filter(payment_method='qr').aggregate(s=Sum('final_paid'))['s'] or Decimal('0.00')
    nasiya_pure = sales.filter(payment_method='nasiya').aggregate(s=Sum('debt_added'))['s'] or Decimal('0.00')

    aralash_naqd = sales.filter(payment_method='aralash').aggregate(s=Sum('paid_naqd'))['s'] or Decimal('0.00')
    aralash_karta = sales.filter(payment_method='aralash').aggregate(s=Sum('paid_karta'))['s'] or Decimal('0.00')
    aralash_qr = sales.filter(payment_method='aralash').aggregate(s=Sum('paid_qr'))['s'] or Decimal('0.00')
    aralash_nasiya = sales.filter(payment_method='aralash').aggregate(s=Sum('debt_added'))['s'] or Decimal('0.00')

    cash_sales = naqd_pure + aralash_naqd
    card_sales = karta_pure + aralash_karta
    qr_sales = qr_pure + aralash_qr
    debt_sales = nasiya_pure + aralash_nasiya

    # Cash Transactions during shift
    tx_query = CashTransaction.objects.filter(created_at__gte=shift.opened_at, payment_method='naqd')
    cash_in = tx_query.filter(transaction_type='in').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    cash_out = tx_query.filter(transaction_type='out').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

    expected_cash = shift.opening_cash + cash_sales + cash_in - cash_out
    total_sales_sum = cash_sales + card_sales + qr_sales

    return Response({
        'is_open': True,
        'shift_id': shift.id,
        'cashier_name': shift.cashier.get_full_name() or shift.cashier.username,
        'opened_at': timezone.localtime(shift.opened_at).strftime('%d.%m.%Y %H:%M'),
        'opening_cash': float(shift.opening_cash),
        'cash_sales': float(cash_sales),
        'card_sales': float(card_sales),
        'qr_sales': float(qr_sales),
        'debt_sales': float(debt_sales),
        'cash_in': float(cash_in),
        'cash_out': float(cash_out),
        'expected_cash': float(expected_cash),
        'total_sales_sum': float(total_sales_sum),
        'sales_count': sales.count()
    })


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def api_shift_open(request):
    """Yangi kassa smenasini ochish"""
    try:
        from .models import CashierShift
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Check active shift
        existing = CashierShift.objects.filter(is_open=True).first()
        if existing:
            return Response({'error': f"Smena #{existing.id} allaqachon ochiq! Yangi smena ochishdan oldin amaldagini yoping."}, status=status.HTTP_400_BAD_REQUEST)

        body = request.data or {}
        opening_cash = Decimal(str(body.get('opening_cash', 0)))
        notes = body.get('notes', '').strip()

        cashier_user = request.user if (request.user and request.user.is_authenticated) else User.objects.filter(is_superuser=True).first() or User.objects.first()

        shift = CashierShift.objects.create(
            cashier=cashier_user,
            opening_cash=opening_cash,
            notes=notes,
            is_open=True
        )

        try:
            from pos.telegram_bot import send_message as send_adm_tg_msg, CHAT_ID
            send_adm_tg_msg(
                CHAT_ID,
                f"🔓 *YANGI KASSA SMENASI OCHILDI* (#{shift.id})\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"👤 *Kassir:* {cashier_user.username}\n"
                f"💰 *Boshlang'ich kassa:* `{opening_cash:,.0f} so'm`\n"
                f"📅 *Vaqt:* {timezone.localtime(shift.opened_at).strftime('%d.%m.%Y %H:%M')}"
            )
        except Exception:
            pass

        return Response({
            'status': 'success',
            'message': f"Smena #{shift.id} muvaffaqiyatli ochildi!",
            'shift_id': shift.id,
            'opened_at': timezone.localtime(shift.opened_at).strftime('%d.%m.%Y %H:%M')
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def api_shift_close(request):
    """Kassa smenasini yopish va Z-Hisobot generatsiya qilish"""
    try:
        from .models import CashierShift, CashTransaction
        shift = CashierShift.objects.filter(is_open=True).order_by('-opened_at').first()
        if not shift:
            return Response({'error': "Hozirda faol ochiq smena topilmadi!"}, status=status.HTTP_404_NOT_FOUND)

        body = request.data or {}
        actual_cash = Decimal(str(body.get('closed_cash_actual', 0)))
        notes = body.get('notes', '').strip()

        sales = Sale.objects.filter(shift=shift)

        # Sales totals
        naqd_pure = sales.filter(payment_method='naqd').aggregate(s=Sum('final_paid'))['s'] or Decimal('0.00')
        karta_pure = sales.filter(payment_method='karta').aggregate(s=Sum('final_paid'))['s'] or Decimal('0.00')
        qr_pure = sales.filter(payment_method='qr').aggregate(s=Sum('final_paid'))['s'] or Decimal('0.00')
        nasiya_pure = sales.filter(payment_method='nasiya').aggregate(s=Sum('debt_added'))['s'] or Decimal('0.00')

        aralash_naqd = sales.filter(payment_method='aralash').aggregate(s=Sum('paid_naqd'))['s'] or Decimal('0.00')
        aralash_karta = sales.filter(payment_method='aralash').aggregate(s=Sum('paid_karta'))['s'] or Decimal('0.00')
        aralash_qr = sales.filter(payment_method='aralash').aggregate(s=Sum('paid_qr'))['s'] or Decimal('0.00')
        aralash_nasiya = sales.filter(payment_method='aralash').aggregate(s=Sum('debt_added'))['s'] or Decimal('0.00')

        cash_sales = naqd_pure + aralash_naqd
        card_sales = karta_pure + aralash_karta
        qr_sales = qr_pure + aralash_qr
        debt_sales = nasiya_pure + aralash_nasiya

        # Transactions
        tx_query = CashTransaction.objects.filter(created_at__gte=shift.opened_at, payment_method='naqd')
        cash_in = tx_query.filter(transaction_type='in').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        cash_out = tx_query.filter(transaction_type='out').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

        expected_cash = shift.opening_cash + cash_sales + cash_in - cash_out
        difference = actual_cash - expected_cash

        shift.closed_cash_expected = expected_cash
        shift.closed_cash_actual = actual_cash
        shift.closed_card_expected = card_sales
        shift.closed_debt_expected = debt_sales
        shift.cash_difference = difference
        shift.notes = notes
        shift.is_open = False
        shift.closed_at = timezone.now()
        shift.save()

        # Send Z-Report to Admin Telegram
        try:
            from pos.telegram_bot import send_message as send_adm_tg_msg, CHAT_ID
            diff_text = f"✅ `{difference:,.0f} so'm` (To'liq)" if difference == 0 else f"⚠️ `{difference:,.0f} so'm` ({'Ortiqcha' if difference > 0 else 'Kamomad'})"
            z_report_text = (
                f"📊 *KASSA Z-HISOBOTI (SMENA YOPILDI)*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"📋 *Smena:* `#{shift.id}`\n"
                f"👤 *Kassir:* {shift.cashier.username}\n"
                f"⏱ *Davomiylik:* {timezone.localtime(shift.opened_at).strftime('%d.%m %H:%M')} — {timezone.localtime(shift.closed_at).strftime('%H:%M')}\n"
                f"🧾 *Cheklar soni:* `{sales.count()} ta`\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"💰 *Boshlang'ich kassa:* `{shift.opening_cash:,.0f} so'm`\n"
                f"💵 *Naqd tushum:* `{cash_sales:,.0f} so'm`\n"
                f"💳 *Karta tushum:* `{card_sales:,.0f} so'm`\n"
                f"📱 *QR tushum:* `{qr_sales:,.0f} so'm`\n"
                f"📋 *Nasiya (qarz):* `{debt_sales:,.0f} so'm`\n"
                f"📥 *Kassa kirim/chiqim:* `+{cash_in:,.0f} / -{cash_out:,.0f} so'm`\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 *Kutilgan naqd:* `{expected_cash:,.0f} so'm`\n"
                f"💵 *Faktik naqd:* `{actual_cash:,.0f} so'm`\n"
                f"⚖️ *Farq:* {diff_text}\n"
            )
            if notes:
                z_report_text += f"📝 *Izoh:* {notes}\n"
            send_adm_tg_msg(CHAT_ID, z_report_text)
        except Exception:
            pass

        return Response({
            'status': 'success',
            'message': f"Smena #{shift.id} muvaffaqiyatli yopildi!",
            'z_report': {
                'shift_id': shift.id,
                'cashier_name': shift.cashier.username,
                'opened_at': timezone.localtime(shift.opened_at).strftime('%d.%m.%Y %H:%M'),
                'closed_at': timezone.localtime(shift.closed_at).strftime('%d.%m.%Y %H:%M'),
                'opening_cash': float(shift.opening_cash),
                'cash_sales': float(cash_sales),
                'card_sales': float(card_sales),
                'qr_sales': float(qr_sales),
                'debt_sales': float(debt_sales),
                'cash_in': float(cash_in),
                'cash_out': float(cash_out),
                'expected_cash': float(expected_cash),
                'actual_cash': float(actual_cash),
                'difference': float(difference),
                'sales_count': sales.count(),
                'notes': notes
            }
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# =====================================================================
# ESKI QARZLARNI TEZKOR KO'CHIRISH API
# =====================================================================
@csrf_exempt
@transaction.atomic
@user_passes_test(is_staff_or_admin)
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
@user_passes_test(is_staff_or_admin)
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
@user_passes_test(is_staff_or_admin)
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
@user_passes_test(is_staff_or_admin)
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
@user_passes_test(is_staff_or_admin)
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

    # Umumiy qarzlar (To'g'ri ajratilgan: Mijozlar qarzi vs Ta'minotchi qarzimiz)
    from .models import Slaughter
    total_customer_debts = Customer.objects.filter(debt_amount__gt=0).aggregate(Sum('debt_amount'))['debt_amount__sum'] or Decimal('0.00')
    
    unpaid_slaughters = Slaughter.objects.filter(is_paid=False).aggregate(Sum('total_cost'))['total_cost__sum'] or Decimal('0.00')
    supplier_model_debts = Supplier.objects.aggregate(Sum('our_debt'))['our_debt__sum'] or Decimal('0.00')
    customer_suppliers_debt = abs(Customer.objects.filter(debt_amount__lt=0).aggregate(Sum('debt_amount'))['debt_amount__sum'] or Decimal('0.00'))
    total_supplier_debts = max(unpaid_slaughters + supplier_model_debts, customer_suppliers_debt)

    # Oxirgi savdolar (Bugungi)
    today_sales = Sale.objects.filter(created_at__date=today)
    total_revenue = today_sales.aggregate(Sum('final_paid'))['final_paid__sum'] or Decimal('0.00')
    total_debt_added = today_sales.aggregate(Sum('debt_added'))['debt_added__sum'] or Decimal('0.00')
    total_discounts = today_sales.aggregate(Sum('discount_amount'))['discount_amount__sum'] or Decimal('0.00')

    # Eng katta qarzdor xaridorlar (Bizga pul berishi kerak bo'lganlar)
    debtors = Customer.objects.filter(debt_amount__gt=0).order_by('-debt_amount')[:3]
    debtors_summary = ", ".join([f"{d.first_name} ({d.phone}): {d.debt_amount:,.0f} so'm" for d in debtors]) or "Mijozlardan nasiya qarzlar yo'q"

    # Eng katta ta'minotchilar (Biz pul to'lashimiz kerak bo'lgan chorvadorlar)
    unpaid_slaughters_qs = Slaughter.objects.filter(is_paid=False).select_related('supplier', 'customer')[:3]
    suppliers_summary = ", ".join([f"{s.customer.first_name if s.customer else (s.supplier.name if s.supplier else 'Chorvador')}: {s.total_cost:,.0f} so'm" for s in unpaid_slaughters_qs]) or "Chorvadorlar ro'yxati toza"

    # Prompt yaratish
    prompt = f"""
    Siz "Baxmal Meat" go'sht do'konining aqlli sun'iy intellekt biznes maslahatchisisiz. Qassob va do'kon egasi (Islom aka)ga do'kondagi hozirgi moliyaviy va ombor holati bo'yicha o'zbek tilida (oddiy, tushunarli, samimiy va do'konchilik uslubida) hisobotlar, tahlil va maslahatlar bering.
    
    Hozirgi do'konning haqiqiy ko'rsatkichlari:
    1. Ombordagi go'sht qoldiqlari: {stock_summary}
    2. Mijozlarimizning do'kondan olgan nasiya qarzi (Bizga qaytishi kerak bo'lgan pul): {total_customer_debts:,.0f} so'm.
       Asosiy qarzdor mijozlar: {debtors_summary}
    3. Bizning (do'konning) chorvador va ta'minotchilarga bo'lgan qarzimiz (Biz to'lashimiz kerak bo'lgan go'sht/so'yim haqqi): {total_supplier_debts:,.0f} so'm.
       Asosiy ta'minotchilarimiz: {suppliers_summary}
    4. Bugungi kassa tushumi (naqd/karta): {total_revenue:,.0f} so'm.
    5. Bugun yangi berilgan nasiya: {total_debt_added:,.0f} so'm.
    6. Bugun chegirmalarga ketgan summa: {total_discounts:,.0f} so'm.
    
    DIQQAT MUHIM FARQLAR:
    - Mijozlar qarzi ({total_customer_debts:,.0f} so'm) — bu xaridorlar go'sht olib ketib bizga to'lashi kerak bo'lgan summa (Biz undirib olishimiz kerak).
    - Ta'minotchi/chorvadorlar qarzi ({total_supplier_debts:,.0f} so'm) — bu biz tirik mol yoki go'sht olib, chorvadorga to'lashimiz kerak bo'lgan qarz (Biz to'lashimiz kerak).
    
    Islom akaga do'kondagi aylanmani yaxshilash, chorvador oldidagi qarzni uzish va mijozlardan nasiyani undirish bo'yicha aniq, amaliy tavsiyalar bering.
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

    # Smart Local AI Analysis fallback function
    def get_smart_local_ai_advice(q_text):
        q_lower = (q_text or "").lower()
        if "savdo" in q_lower or "oshirish" in q_lower or "z-report" in q_lower or "tushum" in q_lower or "marja" in q_lower:
            return f"""💡 <strong>MeatFlow Pro AI Savdo Tahlili:</strong>

1. 📊 <strong>Bugungi Kassa Tushumi:</strong> {total_revenue:,.0f} so'm tushum va {total_debt_added:,.0f} so'm yangi nasiya berildi. Bugun chegirmalarga {total_discounts:,.0f} so'm kechildi.
2. 🥩 <strong>Zaxira Holati:</strong> Omborda {stock_summary}. Saralangan premium go'sht turlari aylanmasi yuqori.
3. 📈 <strong>Tavsiya:</strong> Aylanmani oshirish uchun sovuqxonadagi saqlash muddati 3 kundan oshgan partiyalarga 5-10% chegirma e'lon qiling. Yirik B2B mijozlarga to'liq naqd/plastik to'lov evaziga bepul yetkazib berish xizmatini taklif qiling."""

        elif "zaxira" in q_lower or "ombor" in q_lower or "go'sht" in q_lower or "partiya" in q_lower:
            return f"""🥩 <strong>MeatFlow Pro AI Ombor & Zaxira Tahlili:</strong>

1. 📦 <strong>Hozirgi Zaxira Balansi:</strong> {stock_summary}.
2. ⚠️ <strong>Xavf va Zarar Nazorati (Yield Decay):</strong> Zaxirasi 20 kg dan kamaygan go'sht turlari uchun darhol yangi so'yim buyurtma berish lozim.
3. 💡 <strong>Tavsiya:</strong> So'yim chiqimini (Yield %) 78% dan yuqori ushlash uchun suyak va yog' ajratishni standartlashtiring va so'yim sexida ma'lumotlarni o'z vaqtida kiriting."""

        elif "qarz" in q_lower or "nasiya" in q_lower or "qarzdor" in q_lower:
            return f"""💸 <strong>MeatFlow Pro AI Nasiya & Qarz Risk Tahlili:</strong>

1. 🔴 <strong>Mijozlar Nasiyasi (Bizga berishi kerak bo'lgan pul):</strong> <strong>{total_customer_debts:,.0f} so'm</strong>.
2. 🏢 <strong>Chorvadorlar Oldidagi Qarzimiz (Biz to'lashimiz kerak bo'lgan pul):</strong> <strong>{total_supplier_debts:,.0f} so'm</strong>.
3. 🚨 <strong>Top Qarzdor Mijozlar:</strong> {debtors_summary or "Mavjud emas"}.
4. 💡 <strong>Amaliy Tavsiya:</strong> Chorvadorlar oldidagi qarzni uzish uchun avval mijozlardan nasiyalarni undirib olish va yangi nasiyalarni qat'iy cheklash lozim."""

        else:
            return f"""🤖 <strong>MeatFlow Pro AI Tizim Tahlili:</strong>

Assalomu alaykum! Do'koningizning joriy ko'rsatkichlari:
• 📊 <strong>Bugungi Tushum:</strong> {total_revenue:,.0f} so'm
• 🥩 <strong>Ombor Zaxiralari:</strong> {stock_summary}
• 💸 <strong>Mijozlar Nasiya Qarzi:</strong> {total_customer_debts:,.0f} so'm
• 🏢 <strong>Chorvadorlarga Qarzimiz:</strong> {total_supplier_debts:,.0f} so'm
• 🔴 <strong>Top Qarzdor Mijozlar:</strong> {debtors_summary or "Yo'q"}

Sizga savdoni oshirish, zaxiralarni to'ldirish yoki nasiya qarzlarini undirish bo'yicha batafsil tavsiyalar berishim mumkin."""

    # Gemini API ga ulanishga urinamiz
    from django.conf import settings
    api_key = os.environ.get('GEMINI_API_KEY', '').strip() or getattr(settings, 'GEMINI_API_KEY', '').strip()
    
    if api_key and len(api_key) > 10:
        models_to_try = [
            "gemini-3.6-flash",
            "gemini-3.7-flash",
            "gemini-3.5-flash",
        ]
        
        for model_name in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                headers = {'Content-Type': 'application/json'}
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}]
                }
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    result = response.json()
                    raw_advice = result['candidates'][0]['content']['parts'][0]['text']
                    
                    # Convert markdown formatting to HTML for clean display
                    formatted_advice = raw_advice.replace('\n', '<br>')
                    formatted_advice = formatted_advice.replace('**', '<strong>').replace('**', '</strong>')
                    formatted_advice = f"<span class='badge bg-success mb-2' style='font-size: 10px;'>✨ Live Google Gemini ({model_name})</span><br>" + formatted_advice
                    
                    AIChatMessage.objects.create(
                        user=request.user,
                        sender='bot',
                        message=formatted_advice
                    )
                    return json_response({'advice': formatted_advice})
            except Exception:
                continue

    # Fallback to Smart Local AI Engine
    advice = f"<span class='badge bg-warning text-dark mb-2' style='font-size: 10px;'>⚡ MeatFlow Local AI Engine</span><br>" + get_smart_local_ai_advice(user_question)
    AIChatMessage.objects.create(
        user=request.user,
        sender='bot',
        message=advice
    )
    return json_response({'advice': advice})


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def api_yield_decay_report(request):
    """Ombordagi go'sht partiyalarini va kunlik qurish zararini (Yield Decay) hisoblash"""
    from .models import StockBatch
    batches = StockBatch.objects.filter(current_quantity__gt=Decimal('0.05')).select_related('product').order_by('created_at')
    
    results = []
    total_loss_kg = Decimal('0.000')
    total_loss_cost = Decimal('0.00')

    for b in batches:
        days = b.get_days_passed()
        decayed_weight = b.get_decayed_weight()
        loss_kg = b.get_decay_loss()
        real_cost = b.get_real_cost_per_kg()
        ai_rec = b.get_ai_recommendation()
        
        loss_cost = loss_kg * b.purchase_price_per_kg
        
        total_loss_kg += loss_kg
        total_loss_cost += loss_cost

        status_tag = 'critical' if days >= 3 else ('warning' if days >= 2 else 'fresh')
        status_label = f"🔴 {days} kun (Qurish xavfi)" if days >= 3 else (f"🟡 {days} kun (Namlik yo'qotish)" if days >= 2 else "🟢 Yangi (0-1 kun)")

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
            'status_tag': status_tag,
            'status_label': status_label,
            'ai_recommendation': ai_rec['message'] if ai_rec else None,
            'decay_rate_per_day': float(b.decay_rate_per_day),
            'loss_cost': float(loss_cost),
            'created_at': b.created_at.strftime('%d.%m.%Y %H:%M')
        })

    return Response({
        'batches': results,
        'summary': {
            'total_loss_kg': float(total_loss_kg),
            'total_loss_cost': float(total_loss_cost),
            'active_batches_count': len(results),
            'critical_count': len([r for r in results if r['status_tag'] == 'critical']),
            'warning_count': len([r for r in results if r['status_tag'] == 'warning'])
        }
    })

@csrf_exempt
@user_passes_test(is_staff_or_admin)
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

    # 4. Aging Meat Batches (2+ days in showcase) — AI Decay Advice
    from .models import StockBatch
    aging_batches = StockBatch.objects.filter(current_quantity__gt=Decimal('0.05')).select_related('product')
    for b in aging_batches:
        ai_rec = b.get_ai_recommendation()
        if ai_rec:
            alerts.append({
                'type': 'aging_meat_decay',
                'icon': '🥩',
                'title': f"AI Tavsiya: {b.product.name} ({ai_rec['days']} kun vitrinada)",
                'body': ai_rec['message'],
                'action_suggestion': ai_rec['action_suggestion']
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
        from .views import resolve_customer_for_request
        customer = resolve_customer_for_request(request)
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
        from .views import resolve_customer_for_request
        from .models import B2BOrder
        customer = resolve_customer_for_request(request)
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
        from .views import resolve_customer_for_request
        from .models import B2BOrder
        customer = resolve_customer_for_request(request)
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

        # Telegram Push Notifications
        try:
            from .customer_bot import send_message as send_cust_msg
            from .telegram_bot import send_message as send_admin_msg, CHAT_ID

            if order.customer.telegram_chat_id:
                cust_text = (
                    f"🚴‍♂️ *KURYER YO'LDA!*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📦 *Buyurtma:* #{order.id}\n"
                    f"🥩 *Mahsulot:* {order.product.name} ({order.requested_weight:.2f} kg)\n"
                    f"🛵 *Kuryer:* {customer.first_name}\n"
                    f"📞 *Kuryer Tel:* `{customer.phone}`\n\n"
                    f"⏳ Tez orada eshigingiz oldiga yetib boradi!"
                )
                send_cust_msg(order.customer.telegram_chat_id, cust_text)

            if CHAT_ID:
                nav_link = f"https://yandex.com/maps/?pt={order.longitude},{order.latitude}&z=16" if (order.latitude and order.longitude) else ""
                nav_str = f"\n🗺 [Yandex Mapsda Ko'rish]({nav_link})" if nav_link else ""
                admin_text = (
                    f"🚴‍♂️ *KURYER BUYURTMANI OLDI*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🆔 *Buyurtma:* #{order.id}\n"
                    f"👤 *Mijoz:* {order.customer.first_name} ({order.customer.phone})\n"
                    f"🛵 *Kuryer:* {customer.first_name} ({customer.phone})\n"
                    f"📍 *Manzil:* {order.delivery_address or 'Nomalum'}{nav_str}"
                )
                send_admin_msg(CHAT_ID, admin_text)
        except Exception as tg_err:
            print(f"[Courier Accept TG Error]: {tg_err}")

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
        from .views import resolve_customer_for_request
        from .models import B2BOrder
        customer = resolve_customer_for_request(request)
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

        # Telegram Push Notifications for completion
        try:
            from .customer_bot import send_message as send_cust_msg
            from .telegram_bot import send_message as send_admin_msg, CHAT_ID

            if order.customer.telegram_chat_id:
                cust_done_text = (
                    f"✅ *BUYURTMA YETKAZIB BERILDI!*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📦 *Buyurtma:* #{order.id}\n"
                    f"🥩 *Mahsulot:* {order.product.name}\n\n"
                    f"❤️ Baxmal Meat do'konini tanlaganingiz uchun rahmat! Oshingiz halol bo'lsin."
                )
                send_cust_msg(order.customer.telegram_chat_id, cust_done_text)

            if CHAT_ID:
                admin_done_text = (
                    f"✅ *BUYURTMA MUVAFFAQIYATLI YETKAZILDI*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🆔 *Buyurtma:* #{order.id}\n"
                    f"👤 *Mijoz:* {order.customer.first_name}\n"
                    f"🛵 *Kuryer:* {customer.first_name}\n"
                    f"💵 *Kuryerlik haqi:* `{order.delivery_fee:,.0f}` so'm"
                )
                send_admin_msg(CHAT_ID, admin_done_text)
        except Exception as tg_err:
            print(f"[Courier Complete TG Error]: {tg_err}")

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
        return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@user_passes_test(is_staff_or_admin)
def api_send_daily_digest(request):
    """Admin yoki Cron orqali Telegramga Kechki Z-Hisobotni jo'natish."""
    try:
        from .telegram_bot import send_daily_executive_digest
        res = send_daily_executive_digest()
        if res:
            return JsonResponse({'status': 'success', 'message': "Kechki Z-Hisobot Telegramga muvaffaqiyatli yuborildi!"})
        else:
            return JsonResponse({'status': 'error', 'message': "Hisobot yuborilmadi. Telegram bot sozlamalarini tekshiring."}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# =====================================================================
# MIJOZ MAXSUS NARXLARI (CHOYXONA / SHARTNOMA) API
# =====================================================================
@csrf_exempt
@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([AllowAny])
def api_customer_special_prices(request, customer_id, price_id=None):
    """Mijozning shaxsiy narxlarini boshqarish (CRUD)"""
    try:
        from .models import Customer, Product, CustomerSpecialPrice
        customer = Customer.objects.get(id=customer_id)

        if request.method == 'GET':
            prices = customer.special_prices.select_related('product').all()
            data = [
                {
                    'id': p.id,
                    'product_id': p.product_id,
                    'product_name': p.product.name,
                    'special_price': float(p.special_price),
                    'standard_price': float(p.product.price_per_kg),
                    'difference': float(p.special_price - p.product.price_per_kg),
                    'notes': p.notes or ''
                }
                for p in prices
            ]
            return Response({'status': 'success', 'special_prices': data})

        elif request.method == 'POST':
            body = request.data
            product_id = body.get('product_id')
            special_price = Decimal(str(body.get('special_price', 0)))
            notes = body.get('notes', 'Choyxona / Maxsus narx')

            if not product_id or special_price <= 0:
                return Response({'status': 'error', 'message': "Mahsulot va maxsus narx kiritilishi shart!"}, status=status.HTTP_400_BAD_REQUEST)

            product = Product.objects.get(id=product_id)
            obj, created = CustomerSpecialPrice.objects.update_or_create(
                customer=customer,
                product=product,
                defaults={'special_price': special_price, 'notes': notes}
            )

            return Response({
                'status': 'success',
                'message': f"{product.name} uchun {special_price:,.0f} so'm maxsus narx biriktirildi!",
                'id': obj.id
            })

        elif request.method == 'DELETE':
            target_id = price_id or request.data.get('price_id')
            if target_id:
                CustomerSpecialPrice.objects.filter(id=target_id, customer=customer).delete()
            return Response({'status': 'success', 'message': "Maxsus narx o'chirildi va standart narxga qaytarildi."})

    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# =====================================================================
# AI KELISHUV MASLAHATCHISI (DEAL MARGIN & PROFIT GUARD)
# =====================================================================
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def api_ai_deal_advisor(request):
    """
    AI Kelishuv Maslahatchisi (Deal Profitability & Margin Guard):
    Kassir to'y-maraka yoki choyxona uchun kelishilgan narx va vaznlarni kiritganda,
    tizimdagi haqiqiy tannarx (StockBatch) bilan solishtirib, qoplaydimi yoki yo'qmi,
    qancha sof foyda qoladi, qanday marja bo'lishini hisoblab maslahat beradi.
    """
    try:
        from .models import Product, StockBatch
        data = request.data
        items = data.get('items', []) # [{'product_id': 1, 'product_name': 'Lahm', 'weight': 25.0, 'offered_price': 140000}]
        
        if not items:
            return Response({'status': 'error', 'message': "Tahlil uchun mahsulotlar kiritilmadi!"}, status=status.HTTP_400_BAD_REQUEST)

        evaluated_items = []
        total_revenue = Decimal('0.00')
        total_cost = Decimal('0.00')
        total_weight = Decimal('0.000')

        for it in items:
            p_id = it.get('product_id')
            p_name = str(it.get('product_name', '')).strip()
            weight = Decimal(str(it.get('weight', 0)))
            offered_price = Decimal(str(it.get('offered_price', it.get('price_per_kg', 0))))

            if weight <= 0 or offered_price <= 0:
                continue

            product = None
            if p_id:
                product = Product.objects.filter(id=p_id).first()
            elif p_name:
                product = Product.objects.filter(name__icontains=p_name).first()

            name = product.name if product else p_name
            std_price = product.price_per_kg if product else offered_price

            # Find active batch cost
            cost_per_kg = Decimal('0.00')
            if product:
                latest_batch = StockBatch.objects.filter(product=product, current_quantity__gt=0).order_by('-created_at').first()
                if not latest_batch:
                    latest_batch = StockBatch.objects.filter(product=product).order_by('-created_at').first()
                
                if latest_batch and latest_batch.purchase_price_per_kg > 0:
                    cost_per_kg = latest_batch.purchase_price_per_kg
                else:
                    # Fallback estimate: 70% of standard price
                    cost_per_kg = (std_price * Decimal('0.70')).quantize(Decimal('100'))
            else:
                cost_per_kg = (offered_price * Decimal('0.75')).quantize(Decimal('100'))

            item_revenue = weight * offered_price
            item_cost = weight * cost_per_kg
            item_profit = item_revenue - item_cost
            item_margin = (item_profit / item_cost * 100) if item_cost > 0 else Decimal('0.0')

            total_revenue += item_revenue
            total_cost += item_cost
            total_weight += weight

            status_tag = 'safe'
            if offered_price < cost_per_kg:
                status_tag = 'danger'
            elif item_margin < 12:
                status_tag = 'warning'

            evaluated_items.append({
                'product_name': name,
                'weight': float(weight),
                'offered_price': float(offered_price),
                'standard_price': float(std_price),
                'cost_per_kg': float(cost_per_kg),
                'revenue': float(item_revenue),
                'cost': float(item_cost),
                'profit': float(item_profit),
                'profit_per_kg': float(offered_price - cost_per_kg),
                'margin_pct': round(float(item_margin), 1),
                'status_tag': status_tag
            })

        net_profit = total_revenue - total_cost
        overall_margin = (net_profit / total_cost * 100) if total_cost > 0 else Decimal('0.0')

        # AI Verdict & Advice
        if overall_margin >= 18:
            verdict_status = 'profitable'
            verdict_badge = '🟢 FOYDALI KELISHUV (Qoplaydi)'
            ai_advice = (
                f"✅ Kelishuv juda yaxshi! Jami {total_weight:.1f} kg go'shtdan "
                f"sizga <b>+{net_profit:,.0f} so'm sof foyda</b> qoladi (+{overall_margin:.1f}% rentabellik). "
                f"Katta hajm hisobiga do'kon uchun juda manfaatli savdo."
            )
        elif overall_margin >= 7:
            verdict_status = 'warning'
            verdict_badge = '🟡 DIQQAT: Minimal marja (Chegara)'
            ai_advice = (
                f"⚠️ Narx tannarxni qoplaydi, lekin sof foyda kamroq (+{overall_margin:.1f}%). "
                f"Jami sof foyda: +{net_profit:,.0f} so'm. "
                f"Mijozga har bir kg uchun yana 3 000 – 5 000 so'm qo'shishni taklif qilishni maslahat beraman."
            )
        else:
            verdict_status = 'danger'
            verdict_badge = '⛔ ZARAR! (Qoplamaydi)'
            ai_advice = (
                f"❌ Diqqat! Bu narxlarda sotish do'konni zararga kiritadi yoki marja 0% ga tushadi! "
                f"Jami tannarx: {total_cost:,.0f} so'm, taklif: {total_revenue:,.0f} so'm. "
                f"Zarar / kamomad: {net_profit:,.0f} so'm. Kamida tannarxdan yuqori narx belgilang!"
            )

        return Response({
            'status': 'success',
            'verdict_status': verdict_status,
            'verdict_badge': verdict_badge,
            'ai_advice': ai_advice,
            'total_weight': float(total_weight),
            'total_revenue': float(total_revenue),
            'total_cost': float(total_cost),
            'net_profit': float(net_profit),
            'overall_margin_pct': round(float(overall_margin), 1),
            'items': evaluated_items
        })
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_customer_debt_history(request, customer_id):
    """
    Returns full chronological breakdown of all debts taken and payments made by a customer:
    - Date & time
    - Source/Type (Daftar / POS Nasiya / Payment / Void)
    - Note / Products / Details
    - Amount (+debt / -payment)
    - Balance
    """
    try:
        customer = Customer.objects.filter(id=customer_id).first()
        if not customer:
            return Response({'status': 'error', 'message': "Mijoz topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        timeline = []
        total_debt_taken = Decimal('0.00')
        total_debt_paid = Decimal('0.00')

        import re
        handled_sale_ids = set()

        # 1. Customer Logs (Debt migrations, manual adjustments, debt payments)
        logs = customer.logs.all().order_by('created_at')
        for log in logs:
            text_combo = f"{log.title or ''} {log.message or ''}"
            sale_match = re.search(r'#(\d+)', text_combo) or re.search(r'Chek\s*#?(\d+)', text_combo, re.IGNORECASE)
            
            matched_sale = None
            if sale_match:
                try:
                    s_id = int(sale_match.group(1))
                    matched_sale = customer.sales.filter(id=s_id).prefetch_related('items__product').first()
                    if matched_sale:
                        handled_sale_ids.add(matched_sale.id)
                except (ValueError, TypeError):
                    matched_sale = None

            if log.log_type == 'debt_add':
                total_debt_taken += log.amount
                if matched_sale:
                    items_desc = []
                    for it in matched_sale.items.all():
                        pname = it.product.name if it.product else "Go'sht mahsuloti"
                        items_desc.append(f"{pname} ({it.weight:.3f} kg)")
                    items_text = ", ".join(items_desc) if items_desc else "Nasiya go'sht xaridi"
                    
                    timeline.append({
                        'id': f"sale-{matched_sale.id}",
                        'type': 'debt_add',
                        'badge': '🥩 Kassa Nasiya Savdosi',
                        'title': f"Nasiya savdo (#{matched_sale.id})",
                        'note': f"Chek #{matched_sale.id} · {items_text}",
                        'amount': float(log.amount),
                        'created_at': timezone.localtime(log.created_at).strftime('%d.%m.%Y %H:%M'),
                        'raw_date': log.created_at.isoformat()
                    })
                else:
                    source_badge = '📋 Daftardan ko\'chirilgan' if ('daftar' in (log.title or '').lower() or 'daftar' in (log.message or '').lower()) else '➕ Qarz kiritildi'
                    timeline.append({
                        'id': f"log-{log.id}",
                        'type': 'debt_add',
                        'badge': source_badge,
                        'title': log.title or "Qarz yozildi",
                        'note': log.message or "Qarz kiritildi",
                        'amount': float(log.amount),
                        'created_at': timezone.localtime(log.created_at).strftime('%d.%m.%Y %H:%M'),
                        'raw_date': log.created_at.isoformat()
                    })
            elif log.log_type == 'debt_pay':
                total_debt_paid += log.amount
                timeline.append({
                    'id': f"log-{log.id}",
                    'type': 'debt_pay',
                    'badge': '💵 Qarz to\'lovi',
                    'title': log.title or "To'lov qabul qilindi",
                    'note': log.message or "Qarz to'landi",
                    'amount': float(-abs(log.amount)),
                    'created_at': timezone.localtime(log.created_at).strftime('%d.%m.%Y %H:%M'),
                    'raw_date': log.created_at.isoformat()
                })

        # 2. Sales with debt_added > 0 (that were NOT already logged)
        sales = customer.sales.filter(debt_added__gt=0).exclude(id__in=handled_sale_ids).prefetch_related('items__product').order_by('created_at')
        for sale in sales:
            items_desc = []
            for it in sale.items.all():
                pname = it.product.name if it.product else "Go'sht mahsuloti"
                items_desc.append(f"{pname} ({it.weight:.3f} kg)")
            items_text = ", ".join(items_desc) if items_desc else "Nasiya go'sht xaridi"
            note_str = f"Chek #{sale.id} · {items_text}"

            total_debt_taken += sale.debt_added
            timeline.append({
                'id': f"sale-{sale.id}",
                'type': 'debt_add',
                'badge': '🥩 Kassa Nasiya Savdosi',
                'title': f"Nasiya savdo (#{sale.id})",
                'note': note_str,
                'amount': float(sale.debt_added),
                'created_at': timezone.localtime(sale.created_at).strftime('%d.%m.%Y %H:%M'),
                'raw_date': sale.created_at.isoformat()
            })

        # Track already handled payment signatures to avoid double-counting CashTransaction
        handled_pay_sigs = set()
        for log in logs:
            if log.log_type == 'debt_pay':
                handled_pay_sigs.add((timezone.localtime(log.created_at).strftime('%Y-%m-%d %H:%M'), float(log.amount)))

        # 3. Cash Transactions (Direct debt payments via cash register that do not have a CustomerLog)
        cash_txs = CashTransaction.objects.filter(customer=customer, category='debt_pay').order_by('created_at')
        for tx in cash_txs:
            tx_sig = (timezone.localtime(tx.created_at).strftime('%Y-%m-%d %H:%M'), float(tx.amount))
            if tx_sig not in handled_pay_sigs:
                total_debt_paid += tx.amount
                handled_pay_sigs.add(tx_sig)
                timeline.append({
                    'id': f"tx-{tx.id}",
                    'type': 'debt_pay',
                    'badge': f"💵 To'lov ({tx.get_payment_method_display()})",
                    'title': "Kassaga qarz to'landi",
                    'note': tx.description or f"Kassa orqali {tx.amount:,.0f} so'm qarz so'ndirildi",
                    'amount': float(-abs(tx.amount)),
                    'created_at': timezone.localtime(tx.created_at).strftime('%d.%m.%Y %H:%M'),
                    'raw_date': tx.created_at.isoformat()
                })

        # If no detailed logs exist yet (initial legacy balance), show initial record
        if not timeline and customer.debt_amount > 0:
            timeline.append({
                'id': f"init-{customer.id}",
                'type': 'debt_add',
                'badge': '📋 Boshlang\'ich qarz',
                'title': 'Daftardan ko\'chirilgan qarz',
                'note': customer.note or 'Boshlang\'ich qoldiq',
                'amount': float(customer.debt_amount),
                'created_at': timezone.localtime(customer.created_at).strftime('%d.%m.%Y %H:%M'),
                'raw_date': customer.created_at.isoformat()
            })
            total_debt_taken = customer.debt_amount

        # Mathematical sanity check to guarantee perfect reconciliation
        if total_debt_taken < (customer.debt_amount + total_debt_paid):
            total_debt_taken = customer.debt_amount + total_debt_paid

        # Sort timeline chronologically (latest first)
        timeline.sort(key=lambda x: x.get('raw_date', ''), reverse=True)

        return Response({
            'status': 'success',
            'customer': {
                'id': customer.id,
                'name': f"{customer.first_name} {customer.last_name or ''}".strip(),
                'custom_id': customer.custom_id,
                'phone': customer.phone,
                'debt_amount': float(customer.debt_amount),
                'debt_limit': float(customer.debt_limit)
            },
            'summary': {
                'total_debt_taken': float(total_debt_taken),
                'total_debt_paid': float(total_debt_paid),
                'current_balance': float(customer.debt_amount)
            },
            'timeline': timeline
        })
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ── AI FACE RECOGNITION & VOICE GREETING APIS ──
@api_view(['POST'])
@permission_classes([AllowAny])
def api_face_recognize(request):
    """
    Kamera kadrini qabul qilib, bazadagi mijozlar rasmlari bilan solishtiradi.
    Mijoz topilsa uning ma'lumotlari va shaxsiylashtirilgan ovozli salomlashish matnini qaytaradi.
    Topilmasa ham kelgan har qanday insonga xushmuomalalik bilan ovozli salom beradi.
    """
    try:
        import base64
        import io
        import random
        from PIL import Image
        from .models import Customer

        image_data = request.data.get('image', '').strip()
        if not image_data:
            return Response({'status': 'error', 'message': "Kamera kadri (image) yuborilmadi"}, status=status.HTTP_400_BAD_REQUEST)

        # Strip Data URL header if present
        if 'base64,' in image_data:
            image_data = image_data.split('base64,')[1]

        try:
            img_bytes = base64.b64decode(image_data)
            raw_img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
            # Center-focused square crop to focus on the human face
            w, h = raw_img.size
            min_dim = min(w, h)
            left = (w - min_dim) // 2
            top = (h - min_dim) // 2
            cropped_img = raw_img.crop((left, top, left + min_dim, top + min_dim))
            captured_img = cropped_img.convert('L').resize((32, 32))
        except Exception as img_err:
            return Response({'status': 'error', 'message': f"Tasvirni o'qishda xato: {img_err}"}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate Difference Hash (dhash) and Average Hash (ahash)
        def calc_hashes(image):
            pixels = list(image.getdata())
            width, height = image.size
            # 1. dhash
            dhash = []
            for row in range(height):
                for col in range(width - 1):
                    pixel_left = pixels[row * width + col]
                    pixel_right = pixels[row * width + col + 1]
                    dhash.append(pixel_left > pixel_right)
            # 2. ahash
            avg = sum(pixels) / len(pixels) if pixels else 128
            ahash = [p > avg for p in pixels]
            return dhash, ahash

        captured_dhash, captured_ahash = calc_hashes(captured_img)

        # Compare against customers who have profile images
        customers_with_images = Customer.objects.exclude(image='').exclude(image__isnull=True)
        
        best_match = None
        best_similarity = 0.0

        for cust in customers_with_images:
            try:
                if cust.image and cust.image.storage.exists(cust.image.name):
                    with cust.image.open('rb') as f:
                        raw_c = Image.open(f).convert('RGB')
                        cw, ch = raw_c.size
                        c_min = min(cw, ch)
                        c_left = (cw - c_min) // 2
                        c_top = (ch - c_min) // 2
                        c_crop = raw_c.crop((c_left, c_top, c_left + c_min, c_top + c_min))
                        c_img = c_crop.convert('L').resize((32, 32))
                        
                        c_dhash, c_ahash = calc_hashes(c_img)
                        
                        # Combined Similarity
                        d_matches = sum(1 for a, b in zip(captured_dhash, c_dhash) if a == b)
                        a_matches = sum(1 for a, b in zip(captured_ahash, c_ahash) if a == b)
                        sim = ((d_matches / len(captured_dhash)) * 0.6 + (a_matches / len(captured_ahash)) * 0.4) * 100.0
                        
                        if sim > best_similarity:
                            best_similarity = sim
                            best_match = cust
            except Exception:
                continue

        # Match threshold: 64.0%
        is_matched = best_match is not None and best_similarity >= 64.0

        visitor_greetings = [
            "Assalomu alaykum! Baxmal Meat sarxil go'shtlar do'koniga xush kelibsiz! Bugungi yangi so'yilgan sarxil go'shtlarimizdan marhamat tanlang!",
            "Xush kelibsiz! Bugun do'konimizda yangi mol va qo'y go'shtlari keltirildi. Qaysi biridan tortib beraylik?",
            "Assalomu alaykum, aziz xaridor! Sog'lom va halol go'shtlarimiz siz uchun tayyor, marhamat!",
            "Xush kelibsiz! Mayin lahm, qovurg'a, suyakli go'shtlarimiz yangi keldi, marhamat!"
        ]

        if is_matched:
            c = best_match
            first_name = c.first_name or "Mijoz"
            last_name = c.last_name or ""
            full_name = f"{first_name} {last_name}".strip()

            if c.bonus_points >= 2000:
                greeting = f"Assalomu alaykum, hurmatli VIP mijozimiz {first_name}! Baxmal Meat sarxil go'shtlar do'koniga xush kelibsiz! Sizda {c.bonus_points} ta bonus mavjud."
            elif float(c.debt_amount) > 0:
                greeting = f"Assalomu alaykum, {first_name}! Do'konimizga xush kelibsiz! Bugun qanday sarxil go'sht tortib beraylik?"
            else:
                greeting = f"Assalomu alaykum, {first_name}! Baxmal Meat do'koniga xush kelibsiz! Bugungi yangi so'yilgan sarxil go'shtlarimizdan tanlashingiz mumkin."

            return Response({
                'status': 'success',
                'matched': True,
                'confidence': round(best_similarity, 1),
                'customer': {
                    'id': c.id,
                    'first_name': c.first_name,
                    'last_name': c.last_name or '',
                    'name': full_name,
                    'phone': c.phone,
                    'custom_id': c.custom_id,
                    'debt_amount': float(c.debt_amount),
                    'debt_limit': float(c.debt_limit),
                    'bonus_points': c.bonus_points,
                    'credit_score': getattr(c, 'credit_score', 'A (Ishonchli)'),
                    'image': c.image.url if c.image else ''
                },
                'greeting_text': greeting
            })
        else:
            return Response({
                'status': 'success',
                'matched': False,
                'confidence': round(best_similarity, 1) if best_match else 0.0,
                'customer': None,
                'greeting_text': random.choice(visitor_greetings)
            })

    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def api_save_customer_face(request):
    """
    Kameradan olingan fotosurat va 128 o'lchamli biometrik deskriptorni mijoz profiliga Face ID sifatida biriktirish API.
    """
    try:
        import base64
        import time
        from django.core.files.base import ContentFile
        from .models import Customer

        customer_id = request.data.get('customer_id')
        image_data = request.data.get('image', '').strip()
        descriptor = request.data.get('descriptor', None)

        if not customer_id:
            return Response({'status': 'error', 'message': "Mijoz ID yuborilmadi"}, status=status.HTTP_400_BAD_REQUEST)

        customer = Customer.objects.filter(id=customer_id).first()
        if not customer:
            return Response({'status': 'error', 'message': "Mijoz topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        # Save descriptor if provided
        if descriptor and isinstance(descriptor, list) and len(descriptor) >= 64:
            customer.face_descriptor = [float(x) for x in descriptor]

        if image_data:
            if 'base64,' in image_data:
                image_data = image_data.split('base64,')[1]
            img_bytes = base64.b64decode(image_data)
            file_name = f"face_cust_{customer.id}_{int(time.time())}.jpg"
            customer.image.save(file_name, ContentFile(img_bytes), save=False)

        customer.save()

        return Response({
            'status': 'success',
            'message': f"{customer.first_name} uchun Face ID biometrik ma'lumotlari muvaffaqiyatli saqlandi!",
            'image_url': customer.image.url if customer.image else '',
            'has_descriptor': bool(customer.face_descriptor)
        })
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_get_customer_face_descriptors(request):
    """
    POS Terminalda tezkor mijozni tanish (FaceMatcher) uchun barcha Face ID vektorlarini qaytaradi.
    """
    try:
        from .models import Customer
        customers = Customer.objects.filter(face_descriptor__isnull=False)
        data = []
        for c in customers:
            if c.face_descriptor and isinstance(c.face_descriptor, list) and len(c.face_descriptor) >= 64:
                first_name = c.first_name or "Mijoz"
                last_name = c.last_name or ""
                full_name = f"{first_name} {last_name}".strip()
                data.append({
                    'id': c.id,
                    'name': full_name,
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone': c.phone,
                    'custom_id': c.custom_id,
                    'debt_amount': float(c.debt_amount),
                    'debt_limit': float(c.debt_limit),
                    'bonus_points': c.bonus_points,
                    'credit_score': getattr(c, 'get_credit_score', lambda: 'A (Ishonchli)')(),
                    'image': c.image.url if c.image else '',
                    'face_descriptor': c.face_descriptor
                })
        return Response({'status': 'success', 'customers': data})
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def api_create_customer_with_face(request):
    """
    Kamera suratidan to'g'ridan-to'g'ri yangi mijoz yaratish va unga Face ID (128d vektor + rasm) biriktirish API.
    """
    try:
        import base64
        import time
        from decimal import Decimal
        from django.core.files.base import ContentFile
        from .models import Customer

        name = str(request.data.get('name', '')).strip()
        phone = str(request.data.get('phone', '')).strip()
        debt_limit_raw = request.data.get('debt_limit', '1000000')
        image_data = request.data.get('image', '').strip()
        descriptor = request.data.get('descriptor', None)

        if not name:
            return Response({'status': 'error', 'message': "Mijoz ismi kiritilishi shart!"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not phone:
            return Response({'status': 'error', 'message': "Telefon raqami kiritilishi shart!"}, status=status.HTTP_400_BAD_REQUEST)

        # Standardize name
        parts = name.split(maxsplit=1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''

        # Parse debt limit
        try:
            debt_limit = Decimal(str(debt_limit_raw or '1000000'))
        except Exception:
            debt_limit = Decimal('1000000.00')

        # Check existing phone
        existing = Customer.objects.filter(phone=phone).first()
        if existing:
            customer = existing
            customer.first_name = first_name
            if last_name:
                customer.last_name = last_name
            customer.debt_limit = debt_limit
        else:
            custom_id = f"CUST-{int(time.time()) % 100000:05d}"
            customer = Customer(
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                custom_id=custom_id,
                debt_limit=debt_limit
            )

        if descriptor and isinstance(descriptor, list) and len(descriptor) >= 64:
            customer.face_descriptor = [float(x) for x in descriptor]

        if image_data:
            if 'base64,' in image_data:
                image_data = image_data.split('base64,')[1]
            img_bytes = base64.b64decode(image_data)
            file_name = f"face_cust_{int(time.time())}.jpg"
            customer.image.save(file_name, ContentFile(img_bytes), save=False)

        customer.save()

        full_name = f"{customer.first_name} {customer.last_name or ''}".strip()
        return Response({
            'status': 'success',
            'message': f"Yangi mijoz '{full_name}' muvaffaqiyatli saqlandi va Face ID biriktirildi!",
            'customer': {
                'id': customer.id,
                'name': full_name,
                'first_name': customer.first_name,
                'last_name': customer.last_name or '',
                'phone': customer.phone,
                'custom_id': customer.custom_id,
                'debt_amount': float(customer.debt_amount),
                'debt_limit': float(customer.debt_limit),
                'bonus_points': customer.bonus_points,
                'credit_score': getattr(customer, 'get_credit_score', lambda: 'A (Ishonchli)')(),
                'image': customer.image.url if customer.image else '',
                'face_descriptor': customer.face_descriptor
            }
        })
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# =====================================================================
# GO'SHT TRANSFORMASIYASI (LAHM -> QIYMA / KOLBASA) API
# =====================================================================
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def api_stock_transform(request):
    """
    Eski/turib qolgan go'sht partiyasidan ma'lum miqdorni yangi mahsulotga (masalan: Qiymaga)
    bitta tugma bilan xatosiz transformatsiya qilish.
    """
    try:
        from .models import Product, Stock, StockBatch
        data = request.data
        source_batch_id = data.get('source_batch_id')
        target_product_id = data.get('target_product_id')
        weight_str = data.get('weight')

        if not source_batch_id or not target_product_id or not weight_str:
            return Response({'status': 'error', 'message': "Barcha maydonlar (partiya, maqsadli mahsulot, vazn) to'ldirilishi shart!"}, status=status.HTTP_400_BAD_REQUEST)

        weight = Decimal(str(weight_str))
        if weight <= Decimal('0.001'):
            return Response({'status': 'error', 'message': "Transformatsiya vazni 0 dan katta bo'lishi kerak!"}, status=status.HTTP_400_BAD_REQUEST)

        source_batch = get_object_or_404(StockBatch, id=source_batch_id)
        if source_batch.current_quantity < weight:
            return Response({'status': 'error', 'message': f"Partiyada yetarli go'sht yo'q! Mavjud: {source_batch.current_quantity} kg, so'ralgan: {weight} kg"}, status=status.HTTP_400_BAD_REQUEST)

        target_product = get_object_or_404(Product, id=target_product_id)

        # 1. Manba partiyasidan vaznni ayirish
        source_batch.current_quantity -= weight
        source_batch.save()

        # Manba mahsulotining umumiy Stock zaxirasidan ham ayirish
        source_stock, _ = Stock.objects.get_or_create(product=source_batch.product)
        source_stock.quantity = max(Decimal('0.000'), source_stock.quantity - weight)
        source_stock.save()

        # 2. Maqsadli mahsulot zaxirasiga qo'shish
        target_stock, _ = Stock.objects.get_or_create(product=target_product)
        target_stock.quantity += weight
        target_stock.save()

        # 3. Maqsadli mahsulot uchun yangi partiya ochish
        new_batch = StockBatch.objects.create(
            product=target_product,
            initial_quantity=weight,
            current_quantity=weight,
            purchase_price_per_kg=source_batch.purchase_price_per_kg,
            decay_rate_per_day=Decimal('0.50')
        )

        desc = f"🔄 Transformatsiya: {source_batch.product.name} (Partiya #{source_batch.id}) dan {weight:.2f} kg -> {target_product.name} (Yangi Partiya #{new_batch.id}) ga o'tkazildi."
        
        # Telegramga xabar berish
        send_telegram_notification(f"🔄 *Go'sht Transformatsiyasi:*\n{desc}")

        return Response({
            'status': 'success',
            'message': desc,
            'source_batch': {
                'id': source_batch.id,
                'remaining_quantity': float(source_batch.current_quantity)
            },
            'target_product': {
                'id': target_product.id,
                'name': target_product.name,
                'new_stock': float(target_stock.quantity),
                'new_batch_id': new_batch.id
            }
        })
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)






