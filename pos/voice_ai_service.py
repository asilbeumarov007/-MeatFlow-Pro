import os
import io
import json
import base64
import requests
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count, Q

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
ADMIN_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')

def get_live_store_context():
    """Do'kondagi barcha jonli ko'rsatkichlarni AI uchun yig'uvchi funksiya."""
    from pos.models import Sale, SaleItem, Customer, Stock, Slaughter, CashTransaction, Supplier, CashierShift
    
    local_now = timezone.localtime(timezone.now())
    today = local_now.date()
    yesterday = today - timezone.timedelta(days=1)
    
    # 1. Bugungi savdolar
    today_sales = Sale.objects.filter(created_at__date=today)
    total_sales_count = today_sales.count()
    total_revenue = today_sales.aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
    naqd_total = today_sales.filter(payment_method='naqd').aggregate(s=Sum('final_paid'))['s'] or Decimal('0.00')
    karta_total = today_sales.filter(payment_method='karta').aggregate(s=Sum('final_paid'))['s'] or Decimal('0.00')
    qr_total = today_sales.filter(payment_method='qr').aggregate(s=Sum('final_paid'))['s'] or Decimal('0.00')
    nasiya_total = today_sales.filter(payment_method='nasiya').aggregate(s=Sum('debt_added'))['s'] or Decimal('0.00')
    bonus_used_total = today_sales.aggregate(s=Sum('bonus_used'))['s'] or Decimal('0.00')
    discount_total = today_sales.aggregate(s=Sum('discount_amount'))['s'] or Decimal('0.00')

    # 2. Bugun sotilgan go'shtlar
    sale_items = SaleItem.objects.filter(sale__created_at__date=today)
    total_weight_sold = sale_items.aggregate(w=Sum('weight'))['w'] or Decimal('0.000')
    
    product_stats = sale_items.values('product__name').annotate(
        weight=Sum('weight'),
        total=Sum('item_total')
    ).order_by('-weight')
    
    items_breakdown = ", ".join([f"{p['product__name']}: {p['weight']:.2f} kg ({int(p['total']):,} so'm)" for p in product_stats])

    # 3. Bugun tushgan qarz to'lovlari (Mijozlar to'lagan qarz pullari)
    debt_payments = CashTransaction.objects.filter(created_at__date=today, category='debt_pay')
    total_debt_collected = debt_payments.aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    debt_collected_count = debt_payments.count()

    # 4. Ombordagi zaxiralar
    stocks = Stock.objects.filter(product__is_active=True).select_related('product')
    total_stock_weight = stocks.aggregate(s=Sum('quantity'))['s'] or Decimal('0.000')
    stock_breakdown = ", ".join([f"{s.product.name}: {s.quantity:.2f} kg" for s in stocks])

    # 5. Umumiy qarzdorlik holati
    total_customer_debt = Customer.objects.filter(debt_amount__gt=0).aggregate(s=Sum('debt_amount'))['s'] or Decimal('0.00')
    debtor_count = Customer.objects.filter(debt_amount__gt=0).count()
    top_debtors = Customer.objects.filter(debt_amount__gt=0).order_by('-debt_amount')[:5]
    top_debtors_str = ", ".join([f"{d.first_name}: {int(d.debt_amount):,} so'm" for d in top_debtors])

    # Kassa va G'aladondagi kutilayotgan naqd pul
    shift = CashierShift.objects.filter(is_open=True).order_by('-opened_at').first()
    shift_status = "Ochiq" if shift else "Yopilgan"
    cashier_name = (shift.cashier.get_full_name() or shift.cashier.username) if shift else "Biriktirilmagan"
    opening_cash = shift.opening_cash if shift else Decimal('0.00')

    aralash_naqd = today_sales.filter(payment_method='aralash').aggregate(s=Sum('paid_naqd'))['s'] or Decimal('0.00')
    total_cash_from_sales = naqd_total + aralash_naqd

    today_cash_tx = CashTransaction.objects.filter(created_at__date=today, payment_method='naqd')
    cash_in = today_cash_tx.filter(transaction_type='in').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    cash_out = today_cash_tx.filter(transaction_type='out').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    expected_cash_drawer = opening_cash + total_cash_from_sales + cash_in - cash_out

    # Ta'minotchi va Chorvadorlar ro'yxati
    suppliers_qs = Supplier.objects.all().order_by('-our_debt')
    supp_debt = suppliers_qs.filter(our_debt__gt=0).aggregate(s=Sum('our_debt'))['s'] or Decimal('0.00')
    unpaid_slaughters = Slaughter.objects.filter(is_paid=False).aggregate(s=Sum('total_cost'))['s'] or Decimal('0.00')
    total_supplier_debt = unpaid_slaughters + supp_debt

    suppliers_list_str = []
    for s in suppliers_qs:
        debt_txt = f"{s.our_debt:,.0f} so'm qarzimiz bor" if s.our_debt > 0 else (f"Haqimiz bor: {abs(s.our_debt):,.0f} so'm" if s.our_debt < 0 else "0")
        suppliers_list_str.append(f"• {s.first_name} {s.last_name or ''} ({s.phone}): {debt_txt}")
    suppliers_detailed_summary = "\n       ".join(suppliers_list_str) if suppliers_list_str else "Ta'minotchilar ro'yxati bo'sh"

    # 6. Bugungi so'yimlar
    slaughters = Slaughter.objects.filter(created_at__date=today)
    slaughter_count = slaughters.count()
    slaughter_weight = slaughters.aggregate(w=Sum('total_weight'))['w'] or Decimal('0.000')

    # 7. Kechagi savdo xulosasi (taqqoslash uchun)
    yesterday_sales = Sale.objects.filter(created_at__date=yesterday)
    yesterday_revenue = yesterday_sales.aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
    yesterday_weight = SaleItem.objects.filter(sale__created_at__date=yesterday).aggregate(w=Sum('weight'))['w'] or Decimal('0.000')

    context_text = f"""
    BU VAQTDAGI JONLI DO'KON MA'LUMOTLARI ({local_now.strftime('%d.%m.%Y %H:%M')}):
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    💵 KASSA VA G'ALADONDAGI NAQD PUL:
       - Smena: {shift_status} (Kassir: {cashier_name})
       - Kassa boshlang'ich naqd puli: {int(opening_cash):,} so'm
       - Bugungi naqd tushum: {int(total_cash_from_sales):,} so'm
       - Kassaga qo'shimcha kirim: {int(cash_in):,} so'm
       - Kassadan chiqim (xarajat): {int(cash_out):,} so'm
       - 👉 G'ALADONDA KUTILAYOTGAN JORIY NAQD PUL: {int(expected_cash_drawer):,} so'm

    💰 BUGUNGI JAMI SAVDO: {int(total_revenue):,} so'm ({total_sales_count} ta chek)
       - 💵 Naqd to'lov: {int(naqd_total):,} so'm
       - 💳 Plastik karta: {int(karta_total):,} so'm
       - 📱 QR to'lov: {int(qr_total):,} so'm
       - 📋 Nasiya (Qarzga): {int(nasiya_total):,} so'm
       - 💎 Sarflangan bonus: {int(bonus_used_total):,} so'm
       - 🏷️ Chegirma: {int(discount_total):,} so'm

    🥩 BUGUN SOTILGAN GO'SHT: {total_weight_sold:.2f} kg
       - Mahsulotlar bo'yicha: {items_breakdown or 'Hali savdo qilinmadi'}

    🏢 BIZNING CHORVADORLARGA BO'LGAN QARZIMIZ: {int(total_supplier_debt):,} so'm
       Ta'minotchilar ro'yxati:
       {suppliers_detailed_summary}

    📋 MIJOZLARNING DO'KONGA NASIYA QARZI: {int(total_customer_debt):,} so'm ({debtor_count} ta mijoz bizga pul berishi kerak)
       - Top qarzdor mijozlar: {top_debtors_str or 'Qarz yo`q'}

    📦 OMBOR QOLDIG'I: {total_stock_weight:.2f} kg
       - Go'sht turlari: {stock_breakdown}

    🐂 BUGUNGI SO'YIM: {slaughter_count} ta hayvon ({slaughter_weight:.2f} kg toza go'sht)
    """
    return context_text.strip()


def query_gemini_ai_qassob(user_prompt="", audio_base64=None, mime_type="audio/ogg"):
    """Gemini 3.5/3.7 Flash orqali do'kon egasining ovozli yoki matnli savoliga javob berish."""
    system_instruction = (
        "Siz 'Baxmal Meat' professional go'sht do'konining shaxsiy Ovozli AI Qassobi va Biznes Yordamchisisiz.\n"
        "Do'kon egasining savollariga berilgan jonli ma'lumotlar asosida juda aniq, lo'nda, samimiy va o'zbekchilik hurmati bilan "
        "(masalan: 'Assalomu alaykum, xo'jayin!', 'Bugungi holat bo'yicha...') javob bering.\n"
        "Raqamlarni va so'mlarni aniq, qulay o'qiladigan qilib keltiring. "
        "Ortiqcha cho'zmasdan, savolga to'g'ridan-to'g'ri faktlar bilan javob bering."
    )

    store_data = get_live_store_context()
    
    parts = []
    
    # If audio is provided
    if audio_base64:
        parts.append({
            'inline_data': {
                'mime_type': mime_type,
                'data': audio_base64
            }
        })
        prompt_full = f"{system_instruction}\n\n{store_data}\n\nOvozli xabardagi savolga ushbu jonli do'kon ma'lumotlaridan foydalanib to'liq javob bering:"
        parts.append({'text': prompt_full})
    else:
        prompt_full = f"{system_instruction}\n\n{store_data}\n\nDo'kon egasining savoli: \"{user_prompt}\"\n\nJavobingiz:"
        parts.append({'text': prompt_full})

    from django.conf import settings
    key = os.environ.get('GEMINI_API_KEY', '').strip() or getattr(settings, 'GEMINI_API_KEY', '').strip() or GEMINI_API_KEY
    models_to_try = ['gemini-3.5-flash-lite', 'gemini-3.6-flash', 'gemini-3.1-flash-lite']
    
    for model_name in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            payload = {
                'contents': [{'parts': parts}],
                'generationConfig': {
                    'maxOutputTokens': 500,
                    'temperature': 0.3
                }
            }
            res = requests.post(url, params={'key': key}, json=payload, timeout=12)
            if res.status_code == 200:
                data = res.json()
                reply_text = data['candidates'][0]['content']['parts'][0]['text'].strip()
                return reply_text
            else:
                print(f"[{model_name} Error]: {res.status_code} - {res.text[:100]}")
        except Exception as e:
            print(f"[{model_name} Exception]: {e}")
            continue

    # Fallback if AI connection issues
    return (
        "🥩 *Do'kon Ma'lumotlari:*\n\n" + store_data
    )


def handle_telegram_voice_message(chat_id, voice_file_id, bot_token=None):
    """Telegramdan kelgan ovozli xabarni yuklab olib, AI Qassob orqali tahlil qilish."""
    if not bot_token:
        bot_token = ADMIN_BOT_TOKEN
    
    try:
        # 1. Get file path from Telegram
        get_file_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={voice_file_id}"
        r_file = requests.get(get_file_url, timeout=10)
        if r_file.status_code != 200 or not r_file.json().get('ok'):
            return "❌ Ovozli faylni yuklab olishda xatolik yuz berdi."
        
        file_path = r_file.json()['result']['file_path']
        download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        
        # 2. Download audio binary
        r_audio = requests.get(download_url, timeout=15)
        if r_audio.status_code != 200:
            return "❌ Ovozli faylni o'qib bo'lmadi."
        
        audio_b64 = base64.b64encode(r_audio.content).decode('utf-8')
        
        # 3. Query Gemini Multimodal
        ai_reply = query_gemini_ai_qassob(audio_base64=audio_b64, mime_type="audio/ogg")
        return ai_reply
    except Exception as e:
        print(f"[Voice Handler Error]: {e}")
        return f"⚠️ Ovozli xabarni tahlil qilishda xatolik: {e}"
