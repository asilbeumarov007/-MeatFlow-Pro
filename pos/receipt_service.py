import threading
from decimal import Decimal
from django.utils import timezone
from .models import StoreSetting

def format_e_receipt_text(sale, customer, items_details, bonus_earned=0, bonus_used=0, debt_added=0):
    """Telegram uchun go'zal formatlangan elektron chek matni."""
    store = StoreSetting.objects.filter(is_active=True).first()
    store_name = store.name if store else "🥩 Baxmal Meat Do'koni"
    store_phone = store.phone_number if store else "+998 77 082 4477"
    store_address = store.address if store else "Toshkent shahri"

    date_str = timezone.localtime(sale.created_at).strftime('%d.%m.%Y %H:%M')
    cust_name = f"{customer.first_name} {customer.last_name or ''}".strip()

    items_text = ""
    for idx, it in enumerate(items_details, 1):
        p_name = it.get('product_name', 'Mahsulot')
        w = float(it.get('weight', 0))
        p = float(it.get('price', 0))
        tot = float(it.get('total', 0))
        items_text += f"{idx}. *{p_name}*\n   `{w:.3f} kg` x `{p:,.0f}` = `{tot:,.0f}` so'm\n"

    pay_method_map = {
        'naqd': "💵 Naqd pul",
        'karta': "💳 Plastik Karta (Click / Payme)",
        'qr': "📱 TBC QR Kod",
        'nasiya': "📋 Nasiya (Qarz)"
    }
    pay_display = pay_method_map.get(sale.payment_method, sale.get_payment_method_display())

    bonus_section = ""
    if bonus_used > 0:
        bonus_section += f"💎 *Bonus sarflandi:* `-{bonus_used:,.0f}` so'm\n"
    if bonus_earned > 0:
        bonus_section += f"🎁 *Yig'ilgan Keshbek:* `+{bonus_earned:,.0f}` ball\n"

    debt_section = ""
    if sale.payment_method == 'nasiya' or debt_added > 0:
        debt_section = f"⚠️ *Qarzga yozildi:* `{sale.debt_added:,.0f}` so'm\n📊 *Joriy qarz balansi:* `{customer.debt_amount:,.0f}` so'm\n"

    text = (
        f"🥩 *{store_name.upper()}*\n"
        f"📍 {store_address} · 📞 {store_phone}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🧾 *ELEKTRON CHEK #{sale.id}*\n"
        f"📅 *Vaqti:* `{date_str}`\n"
        f"👤 *Xaridor:* *{cust_name}* (`ID: {customer.custom_id}`)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 *XARID RO'YXATI:*\n"
        f"{items_text}"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *JAMI SUMMA:* `{sale.total_amount:,.0f}` so'm\n"
        f"💳 *To'lov turi:* {pay_display}\n"
        f"{bonus_section}"
        f"{debt_section}"
        f"💎 *Joriy Bonus Balansingiz:* `{customer.bonus_points:,}` ball\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ *Xaridingiz uchun tashakkur!*\n"
        f"Halollik va sifat — bizning bosh maqsadimiz."
    )
    return text


def _async_send_receipt(sale_id, customer_id, items_details, bonus_earned, bonus_used, debt_added):
    """Fon rejimida (background thread) xaridorga Telegram va SMS chek yuborish."""
    try:
        from .models import Sale, Customer, StoreSetting
        sale = Sale.objects.filter(id=sale_id).first()
        customer = Customer.objects.filter(id=customer_id).first()
        if not sale or not customer:
            return

        store = StoreSetting.objects.filter(is_active=True).first()
        sent_tg = False

        # 1. Telegram orqali yuborish (agar mijoz Telegram botga ulangan bo'lsa)
        if customer.telegram_chat_id:
            try:
                from .customer_bot import send_message as send_customer_bot_msg
                text = format_e_receipt_text(sale, customer, items_details, bonus_earned, bonus_used, debt_added)
                
                reply_markup = {
                    'inline_keyboard': [
                        [
                            {'text': '🛒 Yangi Buyurtma Berish', 'callback_data': 'view_catalog'},
                            {'text': '💎 Mening Bonuslarim', 'callback_data': 'my_profile'}
                        ]
                    ]
                }
                res = send_customer_bot_msg(customer.telegram_chat_id, text, reply_markup=reply_markup)
                if res and res.get('ok'):
                    sent_tg = True
            except Exception as e_tg:
                print(f"[Telegram Receipt Error]: {e_tg}")

        # 2. SMS orqali yuborish (agar Telegramga bormagan bo'lsa yoki do'kon SMS yoqilgan bo'lsa)
        should_send_sms = store.send_sms_receipts if store else True
        if should_send_sms and customer.phone and not sent_tg:
            try:
                from .sms_service import send_via_eskiz
                sms_msg = (
                    f"Baxmal Meat: Xaridingiz uchun rahmat! Chek #{sale.id}. "
                    f"Summa: {sale.total_amount:,.0f} so'm. "
                    f"Keshbek: +{bonus_earned} ball. "
                    f"Bonus balansingiz: {customer.bonus_points} ball. Tel: 770824477"
                )
                send_via_eskiz(customer.phone, sms_msg)
            except Exception as e_sms:
                print(f"[SMS Receipt Error]: {e_sms}")

    except Exception as e:
        print(f"[Send Receipt Global Error]: {e}")


def dispatch_customer_sale_receipt(sale, customer, items_details, bonus_earned=0, bonus_used=0, debt_added=0):
    """Kassa terminalini kutdirmasdan chekni asinxron yuborish dispatcher."""
    if not customer:
        return
    t = threading.Thread(
        target=_async_send_receipt,
        args=(sale.id, customer.id, items_details, bonus_earned, bonus_used, debt_added),
        daemon=True
    )
    t.start()
