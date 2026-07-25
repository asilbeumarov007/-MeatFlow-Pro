"""
Baxmal Meat Kassa — Telegram Bot Engine
========================================
Barcha buyruqlar va inline tugmalar uchun handler funksiyalari.
"""
import os
import requests
from decimal import Decimal
from datetime import date, timedelta, datetime
from django.utils import timezone
from django.db.models import Sum, Count, Q, F

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ══════════════════════════════════════════════════════════
# TELEGRAM API HELPERS
# ══════════════════════════════════════════════════════════

def send_message(chat_id, text, reply_markup=None, parse_mode='Markdown'):
    """Telegramga xabar yuborish."""
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode,
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        r = requests.post(f"{API_URL}/sendMessage", json=payload, timeout=10)
        return r.json()
    except Exception as e:
        print(f"[TG Bot] Xabar yuborishda xato: {e}")
        return None


def send_document(chat_id, file_path, caption=""):
    """Telegramga hujjat (fayl) yuborish."""
    url = f"{API_URL}/sendDocument"
    try:
        with open(file_path, 'rb') as f:
            files = {'document': f}
            payload = {'chat_id': chat_id, 'caption': caption}
            r = requests.post(url, data=payload, files=files, timeout=20)
            return r.json()
    except Exception as e:
        print(f"[TG Bot] Hujjat yuborishda xato: {e}")
        return None


def answer_callback(callback_query_id, text=""):
    """Callback query ga javob berish (tugma bosilganda loading o'chirish)."""
    try:
        requests.post(f"{API_URL}/answerCallbackQuery", json={
            'callback_query_id': callback_query_id,
            'text': text,
        }, timeout=5)
    except:
        pass


def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode='Markdown'):
    """Mavjud xabarni tahrirlash (tugma bosilganda)."""
    payload = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': parse_mode,
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        r = requests.post(f"{API_URL}/editMessageText", json=payload, timeout=10)
        return r.json()
    except Exception as e:
        print(f"[TG Bot] Xabar tahrirlashda xato: {e}")
        return None


# ══════════════════════════════════════════════════════════
# INLINE KEYBOARD BUILDERS
# ══════════════════════════════════════════════════════════

def main_menu_keyboard():
    """Asosiy menyu tugmalari."""
    return {
        'inline_keyboard': [
            [
                {'text': '📊 Bugungi Hisobot', 'callback_data': 'cmd_hisobot'},
                {'text': '💰 Qarzdorlar', 'callback_data': 'cmd_qarz'},
            ],
            [
                {'text': '📦 Zaxira (Ombor)', 'callback_data': 'cmd_zaxira'},
                {'text': '🚜 Ta\'minotchilar', 'callback_data': 'cmd_taminotchi'},
            ],
            [
                {'text': '🏪 Shift Holati', 'callback_data': 'cmd_shift'},
                {'text': '💎 Bonus Liderlar', 'callback_data': 'cmd_bonus'},
            ],
            [
                {'text': '📅 Kechagi Hisobot', 'callback_data': 'cmd_kecha'},
            ],
        ]
    }


def main_menu_reply_keyboard():
    """Klaviatura o'rnidagi doimiy tugmalar (Reply Keyboard)."""
    return {
        'keyboard': [
            [{'text': '📊 Bugungi Hisobot'}, {'text': '💰 Qarzdorlar'}],
            [{'text': '📦 Zaxira (Ombor)'}, {'text': '🚜 Ta\'minotchilar'}],
            [{'text': '🏪 Shift Holati'}, {'text': '💎 Bonus Liderlar'}],
            [{'text': '👥 Mijozlar Ro\'yxati'}, {'text': '📑 Oxirgi Savdolar'}],
            [{'text': '📅 Kechagi Hisobot'}, {'text': '🐮 Oxirgi So\'yimlar'}],
            [{'text': '❓ Yordam'}]
        ],
        'resize_keyboard': True,
        'one_time_keyboard': False
    }


def send_customer_excel_backup(chat_id=None):
    """Barcha mijozlarni Excelga yozadi va Telegramga jo'natadi."""
    if not chat_id:
        chat_id = CHAT_ID
        
    from pos.models import Customer
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    
    try:
        # Create Workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Mijozlar"
        ws.views.sheetView[0].showGridLines = True
        
        # Style variables (Green & Gold theme)
        header_fill = PatternFill(start_color='1B6B4A', end_color='1B6B4A', fill_type='solid')
        header_font = Font(name='Segoe UI', size=11, bold=True, color='FFFFFF')
        header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
        
        thin_border = Border(
            left=Side(style='thin', color='E2E8F0'),
            right=Side(style='thin', color='E2E8F0'),
            top=Side(style='thin', color='E2E8F0'),
            bottom=Side(style='thin', color='E2E8F0')
        )
        row_alt_fill = PatternFill(start_color='F3F8F5', end_color='F3F8F5', fill_type='solid')
        
        headers = ["ID", "F.I.Sh", "Telefon", "Qarz (so'm)", "Kredit Limiti", "Bonus ballari", "Ro'yxatdan o'tgan sana", "Qora ro'yxat", "Izoh"]
        ws.row_dimensions[1].height = 28
        
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_align
            cell.border = thin_border
            
        customers = Customer.objects.all().order_by('id')
        for row_idx, c in enumerate(customers, 2):
            ws.row_dimensions[row_idx].height = 20
            fullname = f"{c.first_name} {c.last_name or ''}".strip()
            created_str = c.created_at.strftime('%d.%m.%Y %H:%M') if c.created_at else ''
            blacklist_str = "Ha" if c.is_blacklisted else "Yo'q"
            
            row_data = [
                c.custom_id or f"CUST-{c.id}",
                fullname,
                c.phone or '',
                float(c.debt_amount),
                float(c.debt_limit),
                int(c.bonus_points),
                created_str,
                blacklist_str,
                c.note or ''
            ]
            
            is_alt = (row_idx % 2 == 1)
            for col_idx, val in enumerate(row_data, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.border = thin_border
                if is_alt:
                    cell.fill = row_alt_fill
                    
                # Format numbers
                if col_idx in [4, 5]:
                    cell.number_format = '#,##0'
                elif col_idx == 6:
                    cell.number_format = '#,##0'
                    
        # Adjust column widths
        for col in ws.columns:
            max_len = 0
            for cell in col:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)
            
        # Create media directory if not exists
        os.makedirs('media', exist_ok=True)
        file_path = os.path.join('media', 'mijozlar_royxati.xlsx')
        wb.save(file_path)
        
        # Send via telegram
        caption = f"👥 *MeatFlow Mijozlar Zaxira Nusxasi*\n\nJami mijozlar soni: {customers.count()} ta\nSana: {timezone.localtime(timezone.now()).strftime('%d.%m.%Y %H:%M')}"
        send_document(chat_id, file_path, caption=caption)
        
    except Exception as e:
        print(f"[TG Bot] Customer Excel generation error: {e}")


def handle_mijozlar(chat_id):
    """Mijozlar ro'yxatini Excel shaklida jo'natadi."""
    send_message(chat_id, "⏳ Mijozlar ro'yxati shakllantirilmoqda, iltimos kuting...")
    send_customer_excel_backup(chat_id=chat_id)


def handle_oxirgi_savdolar(chat_id):
    """Oxirgi 5 ta savdo haqida ma'lumot beradi."""
    from pos.models import Sale
    sales = Sale.objects.all().order_by('-id')[:5]
    if not sales:
        send_message(chat_id, "ℹ️ Tizimda hali savdolar mavjud emas.")
        return
        
    text = "📑 **Oxirgi 5 ta savdo:**\n\n"
    for s in sales:
        time_str = timezone.localtime(s.created_at).strftime('%d.%m.%Y %H:%M')
        cust_name = f"{s.customer.first_name} {s.customer.last_name or ''}".strip() if s.customer else "Anonim Mijoz"
        text += (
            f"🔹 **Chek #{s.id}** ({time_str})\n"
            f"👤 Mijoz: {cust_name}\n"
            f"💰 Jami: {s.total_amount:,.0f} so'm\n"
            f"💵 To'lov: {s.final_paid:,.0f} so'm ({s.get_payment_method_display()})\n"
            f"📉 Chegirma: {s.discount_amount:,.0f} so'm | 💎 Bonus: {s.bonus_used:,.0f} ball\n"
            f"➕ Qarz: {s.debt_added:,.0f} so'm\n\n"
        )
    send_message(chat_id, text)


def handle_oxirgi_soyimlar(chat_id):
    """Oxirgi 5 ta so'yim (chorva qabuli) haqida ma'lumot beradi."""
    from pos.models import Slaughter
    slaughters = Slaughter.objects.all().order_by('-id')[:5]
    if not slaughters:
        send_message(chat_id, "ℹ️ Tizimda hali so'yimlar mavjud emas.")
        return
        
    text = "🐂 **Oxirgi 5 ta so'yim qabuli:**\n\n"
    for s in slaughters:
        time_str = timezone.localtime(s.created_at).strftime('%d.%m.%Y %H:%M')
        partner = ""
        if s.supplier:
            partner = f"Ta'minotchi: {s.supplier.first_name}"
        elif s.customer:
            partner = f"Mijoz: {s.customer.first_name}"
        else:
            partner = "Nomalum hamkor"
            
        text += (
            f"🔹 **So'yim #{s.id}** ({time_str})\n"
            f"🐄 Turi: {'Mol' if s.animal_type == 'mol' else 'Qo\'y'}\n"
            f"⚖️ Og'irlik: {s.total_weight:.3f} kg\n"
            f"💰 Narxi: {s.purchase_price_per_kg:,.0f} so'm/kg\n"
            f"🤝 Jami qiymat: {s.total_cost:,.0f} so'm\n"
            f"👤 Hamkor: {partner}\n\n"
        )
    send_message(chat_id, text)


def back_button_keyboard():
    """Orqaga qaytish tugmasi."""
    return {
        'inline_keyboard': [
            [{'text': '🔙 Asosiy Menyu', 'callback_data': 'cmd_menu'}],
        ]
    }


# ══════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ══════════════════════════════════════════════════════════

def handle_start(chat_id):
    """Botni ishga tushirish — salomlashuv va asosiy menyu."""
    text = (
        "🥩 *Baxmal Meat Kassa Bot*\n\n"
        "Assalomu alaykum! Men sizning kassa yordamchingizman.\n"
        "Pastdagi tugmalar orqali kerakli ma'lumotlarni tezkor olishingiz mumkin:"
    )
    send_message(chat_id, text, reply_markup=main_menu_reply_keyboard())


def handle_hisobot(chat_id, target_date=None, message_id=None):
    """Savdolar xulosasi — bugungi yoki berilgan sanadagi."""
    from pos.models import Sale, SaleItem, CashierShift

    if target_date is None:
        target_date = timezone.localdate()

    day_label = "📊 *Bugungi" if target_date == timezone.localdate() else f"📅 *{target_date.strftime('%d.%m.%Y')}"
    
    sales = Sale.objects.filter(created_at__date=target_date)
    total_count = sales.count()

    if total_count == 0:
        text = f"{day_label} Savdo Hisoboti*\n\n😔 Bu kunda hech qanday savdo qilinmagan."
        kb = back_button_keyboard()
        if message_id:
            edit_message(chat_id, message_id, text, reply_markup=kb)
        else:
            send_message(chat_id, text, reply_markup=kb)
        return

    total_sum = sales.aggregate(s=Sum('total_amount'))['s'] or Decimal('0')
    total_paid = sales.aggregate(s=Sum('final_paid'))['s'] or Decimal('0')
    total_debt = sales.aggregate(s=Sum('debt_added'))['s'] or Decimal('0')
    total_bonus = sales.aggregate(s=Sum('bonus_used'))['s'] or Decimal('0')
    total_discount = sales.aggregate(s=Sum('discount_amount'))['s'] or Decimal('0')

    naqd_count = sales.filter(payment_method='naqd').count()
    karta_count = sales.filter(payment_method='karta').count()
    nasiya_count = sales.filter(payment_method='nasiya').count()

    # Mahsulot taqsimoti
    items = SaleItem.objects.filter(sale__created_at__date=target_date)
    product_stats = items.values('product__name').annotate(
        total_weight=Sum('weight'),
        total_sum=Sum('item_total')
    ).order_by('-total_sum')

    products_text = ""
    for p in product_stats[:8]:
        name = p['product__name']
        kg = p['total_weight'] or 0
        sm = p['total_sum'] or 0
        products_text += f"  • {name}: *{kg:.1f} kg* — {int(sm):,} so'm\n"

    text = (
        f"{day_label} Savdo Hisoboti*\n"
        f"{'━' * 28}\n\n"
        f"🛒 *Jami savdolar:* {total_count} ta\n"
        f"💵 *Jami summa:* {int(total_sum):,} so'm\n"
        f"✅ *To'langan:* {int(total_paid):,} so'm\n"
        f"📋 *Nasiyaga:* {int(total_debt):,} so'm\n"
        f"💎 *Bonus sarflangan:* {int(total_bonus):,} so'm\n"
        f"🏷️ *Chegirma:* {int(total_discount):,} so'm\n\n"
        f"📌 *To'lov usullari:*\n"
        f"  💵 Naqd: {naqd_count} ta\n"
        f"  💳 Karta: {karta_count} ta\n"
        f"  📝 Nasiya: {nasiya_count} ta\n\n"
        f"📦 *Sotilgan mahsulotlar:*\n"
        f"{products_text}"
    )

    kb = back_button_keyboard()
    if message_id:
        edit_message(chat_id, message_id, text, reply_markup=kb)
    else:
        send_message(chat_id, text, reply_markup=kb)


def handle_qarz(chat_id, message_id=None):
    """Top 10 eng ko'p qarzdor mijozlar."""
    from pos.models import Customer

    debtors = Customer.objects.filter(debt_amount__gt=0).order_by('-debt_amount')[:10]

    if not debtors:
        text = "💰 *Qarzdorlar Ro'yxati*\n\n✅ Hech kim qarzdor emas! Barcha hisob-kitoblar to'liq."
    else:
        total_debt = Customer.objects.filter(debt_amount__gt=0).aggregate(s=Sum('debt_amount'))['s'] or 0
        debtor_count = Customer.objects.filter(debt_amount__gt=0).count()

        text = (
            f"💰 *Top Qarzdor Mijozlar*\n"
            f"{'━' * 28}\n\n"
            f"📊 Jami qarzdorlar: *{debtor_count}* ta\n"
            f"💵 Jami nasiya: *{int(total_debt):,}* so'm\n\n"
        )
        for i, c in enumerate(debtors, 1):
            emoji = "🔴" if c.debt_amount > 500000 else "🟡" if c.debt_amount > 200000 else "🟢"
            name = f"{c.first_name} {c.last_name or ''}"
            text += f"{emoji} *{i}.* {name} (`{c.custom_id}`)\n    💳 {int(c.debt_amount):,} so'm / Limit: {int(c.debt_limit):,} so'm\n"

    kb = back_button_keyboard()
    if message_id:
        edit_message(chat_id, message_id, text, reply_markup=kb)
    else:
        send_message(chat_id, text, reply_markup=kb)


def handle_zaxira(chat_id, message_id=None):
    """Ombordagi barcha mahsulotlar zaxirasi."""
    from pos.models import Stock

    stocks = Stock.objects.select_related('product').filter(product__is_active=True).order_by('product__name')

    if not stocks:
        text = "📦 *Ombor Zaxiralari*\n\n😔 Hech qanday mahsulot topilmadi."
    else:
        text = f"📦 *Ombor Zaxiralari*\n{'━' * 28}\n\n"
        for s in stocks:
            qty = s.quantity
            if qty <= 0:
                emoji = "🔴"
                status = "TUGAGAN"
            elif qty < 5:
                emoji = "🟡"
                status = "KAM"
            elif qty < 20:
                emoji = "🟢"
                status = ""
            else:
                emoji = "✅"
                status = ""
            
            status_text = f" ⚠️ *{status}*" if status else ""
            text += f"{emoji} *{s.product.name}:* {qty:.1f} kg{status_text}\n"

    kb = back_button_keyboard()
    if message_id:
        edit_message(chat_id, message_id, text, reply_markup=kb)
    else:
        send_message(chat_id, text, reply_markup=kb)


def handle_taminotchi(chat_id, message_id=None):
    """Ta'minotchilar balansi."""
    from pos.models import Supplier

    suppliers = Supplier.objects.all().order_by('-our_debt')

    if not suppliers:
        text = "🚜 *Ta'minotchilar*\n\n😔 Hech qanday ta'minotchi topilmadi."
    else:
        total_debt = suppliers.aggregate(s=Sum('our_debt'))['s'] or 0
        text = (
            f"🚜 *Ta'minotchilar Balansi*\n"
            f"{'━' * 28}\n\n"
            f"💵 Bizning jami qarzimiz: *{int(total_debt):,}* so'm\n\n"
        )
        for s in suppliers:
            emoji = "🔴" if s.our_debt > 1000000 else "🟡" if s.our_debt > 0 else "✅"
            name = f"{s.first_name} {s.last_name or ''}"
            if s.our_debt > 0:
                text += f"{emoji} *{name}* (`{s.custom_id}`)\n    Qarzimiz: {int(s.our_debt):,} so'm\n"
            else:
                text += f"{emoji} *{name}* — Qarz yo'q ✅\n"

    kb = back_button_keyboard()
    if message_id:
        edit_message(chat_id, message_id, text, reply_markup=kb)
    else:
        send_message(chat_id, text, reply_markup=kb)


def handle_shift(chat_id, message_id=None):
    """Hozirgi kassa shifti holati."""
    from pos.models import CashierShift

    active = CashierShift.objects.filter(is_open=True).first()

    if active:
        opened = timezone.localtime(active.opened_at).strftime('%H:%M — %d.%m.%Y')
        sales_count = active.sales.count() if hasattr(active, 'sales') else 0
        sales_sum = active.sales.aggregate(s=Sum('final_paid'))['s'] or 0 if hasattr(active, 'sales') else 0
        text = (
            f"🏪 *Kassa Shifti Holati*\n"
            f"{'━' * 28}\n\n"
            f"🟢 *SHIFT OCHIQ*\n\n"
            f"👤 Kassir: *{active.cashier.username}*\n"
            f"🕐 Ochilgan: {opened}\n"
            f"🛒 Savdolar: *{sales_count}* ta\n"
            f"💵 Jami tushumlar: *{int(sales_sum):,}* so'm"
        )
    else:
        last = CashierShift.objects.filter(is_open=False).order_by('-closed_at').first()
        if last:
            closed = timezone.localtime(last.closed_at).strftime('%H:%M — %d.%m.%Y') if last.closed_at else "—"
            text = (
                f"🏪 *Kassa Shifti Holati*\n"
                f"{'━' * 28}\n\n"
                f"🔴 *SHIFT YOPILGAN*\n\n"
                f"Oxirgi shift: {closed}\n"
                f"Kassir: *{last.cashier.username}*"
            )
        else:
            text = "🏪 *Kassa Shifti Holati*\n\n🔴 Hali hech qanday shift ochilmagan."

    kb = back_button_keyboard()
    if message_id:
        edit_message(chat_id, message_id, text, reply_markup=kb)
    else:
        send_message(chat_id, text, reply_markup=kb)


def handle_bonus(chat_id, message_id=None):
    """Top 10 eng ko'p bonus to'plagan mijozlar."""
    from pos.models import Customer

    top = Customer.objects.filter(bonus_points__gt=0).order_by('-bonus_points')[:10]

    if not top:
        text = "💎 *Bonus Liderlar*\n\n😔 Hech kim bonus to'plamagan."
    else:
        text = f"💎 *Top Bonus Liderlar*\n{'━' * 28}\n\n"
        for i, c in enumerate(top, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"  {i}."
            name = f"{c.first_name} {c.last_name or ''}"
            text += f"{medal} *{name}* — {c.bonus_points:,} ball\n"

    kb = back_button_keyboard()
    if message_id:
        edit_message(chat_id, message_id, text, reply_markup=kb)
    else:
        send_message(chat_id, text, reply_markup=kb)


def handle_yordam(chat_id, message_id=None):
    """Yordam — barcha buyruqlar ro'yxati."""
    text = (
        "❓ *Yordam — Buyruqlar Ro'yxati*\n"
        f"{'━' * 28}\n\n"
        "📊 `/hisobot` — Bugungi savdo xulosasi\n"
        "💰 `/qarz` — Top qarzdor mijozlar\n"
        "📦 `/zaxira` — Ombor zaxiralari\n"
        "🚜 `/taminotchi` — Ta'minotchilar balansi\n"
        "🏪 `/shift` — Kassa shifti holati\n"
        "💎 `/bonus` — Bonus liderlar\n"
        "👥 `/mijozlar` — Mijozlar ro'yxati (Excel fayl)\n"
        "📑 `/savdolar` — Oxirgi 5 ta savdo cheklari\n"
        "🐮 `/soyimlar` — Oxirgi 5 ta so'yim qabullari\n"
        "📅 `/savdo 2026-07-20` — Sanadagi savdolar\n"
        "❓ `/yordam` — Shu ro'yxat\n\n"
        "💡 *Shuningdek pastdagi doimiy tugmalardan ham foydalanishingiz mumkin!*"
    )
    kb = back_button_keyboard()
    if message_id:
        edit_message(chat_id, message_id, text, reply_markup=kb)
    else:
        send_message(chat_id, text, reply_markup=kb)


# ══════════════════════════════════════════════════════════
# DAILY REPORT GENERATOR
# ══════════════════════════════════════════════════════════

def generate_daily_report(target_date=None):
    """Kunlik to'liq hisobotni generatsiya qilish va guruhga yuborish."""
    from pos.models import Sale, SaleItem, Customer, Stock, Supplier, CashTransaction

    if target_date is None:
        target_date = timezone.localdate()

    sales = Sale.objects.filter(created_at__date=target_date)
    total_count = sales.count()
    total_sum = sales.aggregate(s=Sum('total_amount'))['s'] or Decimal('0')
    total_paid = sales.aggregate(s=Sum('final_paid'))['s'] or Decimal('0')
    total_debt = sales.aggregate(s=Sum('debt_added'))['s'] or Decimal('0')

    # To'lov usullari
    naqd_sum = sales.filter(payment_method='naqd').aggregate(s=Sum('final_paid'))['s'] or 0
    karta_sum = sales.filter(payment_method='karta').aggregate(s=Sum('final_paid'))['s'] or 0
    nasiya_sum = sales.filter(payment_method='nasiya').aggregate(s=Sum('debt_added'))['s'] or 0

    # Mahsulotlar
    items = SaleItem.objects.filter(sale__created_at__date=target_date)
    product_stats = items.values('product__name').annotate(
        total_weight=Sum('weight'),
        total_sum=Sum('item_total')
    ).order_by('-total_sum')

    products_text = ""
    for p in product_stats:
        name = p['product__name']
        kg = p['total_weight'] or 0
        sm = p['total_sum'] or 0
        products_text += f"  • {name}: {kg:.1f} kg — {int(sm):,} so'm\n"

    # Ombor holati
    stocks = Stock.objects.select_related('product').filter(product__is_active=True)
    low_stocks = []
    for s in stocks:
        if s.quantity < 5:
            low_stocks.append(f"  ⚠️ {s.product.name}: {s.quantity:.1f} kg")

    stock_warning = ""
    if low_stocks:
        stock_warning = "\n\n🚨 *KAM ZAXIRA OGOHLANTIRISHLARI:*\n" + "\n".join(low_stocks)

    # Jami qarz holati
    total_all_debt = Customer.objects.filter(debt_amount__gt=0).aggregate(s=Sum('debt_amount'))['s'] or 0
    debtor_count = Customer.objects.filter(debt_amount__gt=0).count()

    # Kassaga tushum
    cash_in = CashTransaction.objects.filter(
        created_at__date=target_date,
        transaction_type='in'
    ).aggregate(s=Sum('amount'))['s'] or 0
    cash_out = CashTransaction.objects.filter(
        created_at__date=target_date,
        transaction_type='out'
    ).aggregate(s=Sum('amount'))['s'] or 0

    date_str = target_date.strftime('%d.%m.%Y')
    text = (
        f"📋 *BAXMAL MEAT — KUNLIK HISOBOT*\n"
        f"📅 *{date_str}*\n"
        f"{'━' * 30}\n\n"
        f"🛒 *SAVDOLAR:*\n"
        f"  Jami: *{total_count}* ta savdo\n"
        f"  Umumiy summa: *{int(total_sum):,}* so'm\n"
        f"  To'langan: *{int(total_paid):,}* so'm\n"
        f"  Nasiyaga: *{int(total_debt):,}* so'm\n\n"
        f"💳 *TO'LOV USULLARI:*\n"
        f"  💵 Naqd: {int(naqd_sum):,} so'm\n"
        f"  💳 Karta: {int(karta_sum):,} so'm\n"
        f"  📝 Nasiya: {int(nasiya_sum):,} so'm\n\n"
        f"📦 *SOTILGAN MAHSULOTLAR:*\n"
        f"{products_text}\n"
        f"🏦 *KASSA OQIMI:*\n"
        f"  ⬆️ Kirim: {int(cash_in):,} so'm\n"
        f"  ⬇️ Chiqim: {int(cash_out):,} so'm\n\n"
        f"💰 *UMUMIY NASIYA HOLATI:*\n"
        f"  Qarzdorlar: *{debtor_count}* ta\n"
        f"  Jami nasiya: *{int(total_all_debt):,}* so'm"
        f"{stock_warning}"
    )

    send_message(CHAT_ID, text)
    return text


# ══════════════════════════════════════════════════════════
# LOW STOCK ALERT (savdodan keyin chaqiriladi)
# ══════════════════════════════════════════════════════════

def check_low_stock_alert(product_name, remaining_qty):
    """Agar mahsulot zaxirasi 5 kg dan past bo'lsa, Telegramga ogohlantirish yuborish."""
    if remaining_qty < 5 and remaining_qty >= 0:
        text = (
            f"🚨 *KAM ZAXIRA OGOHLANTIRISHLARI!*\n\n"
            f"📦 *{product_name}* zaxirasi juda kam!\n"
            f"📉 Qolgan: *{remaining_qty:.1f} kg*\n\n"
            f"Iltimos, yangi partiya qo'shing yoki ta'minotchiga buyurtma bering."
        )
        send_message(CHAT_ID, text)


# ══════════════════════════════════════════════════════════
# DISPATCHER — Buyruq va callback'larni yo'naltirish
# ══════════════════════════════════════════════════════════

def dispatch_command(chat_id, text_raw):
    """Matnli buyruqlarni tegishli handlerga yo'naltirish."""
    text = text_raw.strip().lower()

    # Remove @bot_username if present
    if '@' in text:
        text = text.split('@')[0]

    if text == '/start':
        handle_start(chat_id)
    elif text in ['/hisobot', '📊 bugungi hisobot']:
        handle_hisobot(chat_id)
    elif text in ['/qarz', '💰 qarzdorlar']:
        handle_qarz(chat_id)
    elif text in ['/zaxira', '📦 zaxira (ombor)', '📦 zaxira']:
        handle_zaxira(chat_id)
    elif text in ['/taminotchi', '/taminotchilar', '🚜 ta\'minotchilar']:
        handle_taminotchi(chat_id)
    elif text in ['/shift', '🏪 shift holati']:
        handle_shift(chat_id)
    elif text in ['/bonus', '💎 bonus liderlar']:
        handle_bonus(chat_id)
    elif text in ['/mijozlar', '👥 mijozlar ro\'yxati']:
        handle_mijozlar(chat_id)
    elif text in ['/savdolar', '📑 oxirgi savdolar']:
        handle_oxirgi_savdolar(chat_id)
    elif text in ['/soyimlar', '🐮 oxirgi so\'yimlar']:
        handle_oxirgi_soyimlar(chat_id)
    elif text in ['/yordam', '/help', '❓ yordam']:
        handle_yordam(chat_id)
    elif text == '📅 kechagi hisobot':
        yesterday = timezone.localdate() - timedelta(days=1)
        handle_hisobot(chat_id, target_date=yesterday)
    elif text.startswith('/savdo'):
        parts = text_raw.strip().split()
        if len(parts) >= 2:
            try:
                target = datetime.strptime(parts[1], '%Y-%m-%d').date()
                handle_hisobot(chat_id, target_date=target)
            except ValueError:
                send_message(chat_id, "❌ Noto'g'ri sana formati!\n\nTo'g'ri format: `/savdo 2026-07-20`")
        else:
            handle_hisobot(chat_id)


def dispatch_callback(chat_id, message_id, callback_data, callback_query_id):
    """Inline tugma callback'larini tegishli handlerga yo'naltirish."""
    answer_callback(callback_query_id, "⏳ Bajarilmoqda...")
    from pos.models import B2BOrder

    if callback_data.startswith('adm_appr_'):
        order_id = int(callback_data.replace('adm_appr_', ''))
        try:
            order = B2BOrder.objects.get(id=order_id)
            order.status = 'approved'
            order.save()
            notify_customer_order_status(order, "✅ Admin tomonidan tasdiqlandi")
            edit_message(chat_id, message_id, f"✅ *BUYURTMA #{order.id} TASDIQLANDI!*\n\nMijoz ({order.customer.first_name}) ga xabar yuborildi.")
        except Exception as e:
            send_message(chat_id, f"⚠️ Xato: {e}")

    elif callback_data.startswith('adm_prep_'):
        order_id = int(callback_data.replace('adm_prep_', ''))
        try:
            order = B2BOrder.objects.get(id=order_id)
            order.status = 'preparing'
            order.save()
            notify_customer_order_status(order, "🥩 Go'sht tortilmoqda / Qadoqlanmoqda")
            edit_message(chat_id, message_id, f"🥩 *BUYURTMA #{order.id} QADOQLANMOQDA!*")
        except Exception as e:
            send_message(chat_id, f"⚠️ Xato: {e}")

    elif callback_data.startswith('adm_ship_'):
        order_id = int(callback_data.replace('adm_ship_', ''))
        try:
            order = B2BOrder.objects.get(id=order_id)
            order.status = 'shipping'
            order.save()
            notify_customer_order_status(order, "🚚 Kuryer yo'lda (Yetkazib berilmoqda)")
            edit_message(chat_id, message_id, f"🚚 *BUYURTMA #{order.id} KURYERGA TOPSHIRILDI!*")
        except Exception as e:
            send_message(chat_id, f"⚠️ Xato: {e}")

    elif callback_data.startswith('adm_rej_'):
        order_id = int(callback_data.replace('adm_rej_', ''))
        try:
            order = B2BOrder.objects.get(id=order_id)
            order.status = 'rejected'
            order.save()
            notify_customer_order_status(order, "❌ Rad etildi (To'lov cheki mos kelmadi)")
            edit_message(chat_id, message_id, f"❌ *BUYURTMA #{order.id} RAD ETILDI.*")
        except Exception as e:
            send_message(chat_id, f"⚠️ Xato: {e}")

    elif callback_data == 'cmd_menu':
        handle_start_edit(chat_id, message_id)
    elif callback_data == 'cmd_hisobot':
        handle_hisobot(chat_id, message_id=message_id)
    elif callback_data == 'cmd_qarz':
        handle_qarz(chat_id, message_id=message_id)
    elif callback_data == 'cmd_zaxira':
        handle_zaxira(chat_id, message_id=message_id)
    elif callback_data == 'cmd_taminotchi':
        handle_taminotchi(chat_id, message_id=message_id)
    elif callback_data == 'cmd_shift':
        handle_shift(chat_id, message_id=message_id)
    elif callback_data == 'cmd_bonus':
        handle_bonus(chat_id, message_id=message_id)
    elif callback_data == 'cmd_kecha':
        yesterday = timezone.localdate() - timedelta(days=1)
        handle_hisobot(chat_id, target_date=yesterday, message_id=message_id)


def notify_customer_order_status(order, new_status_text):
    """Mijozga buyurtma statusi haqida bildirishnoma yuborish."""
    if not order.customer or not order.customer.telegram_chat_id:
        return

    chat_id = order.customer.telegram_chat_id
    try:
        from .customer_bot import send_message as send_customer_msg, main_menu_reply_keyboard
        msg = (
            f"🔔 *BUYURTMANINGIZ STATUSI O'ZGARDI!* (Buyurtma #{order.id})\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 *Mahsulot:* {order.product.name} ({order.requested_weight} kg)\n"
            f"📊 *Yangi status:* *{new_status_text}*\n\n"
            f"📌 Real vaqt rejimida kuzatish uchun *'📌 Buyurtma Statusi (Live)'* tugmasini bosing."
        )
        send_customer_msg(chat_id, msg, reply_markup=main_menu_reply_keyboard())
    except Exception as e:
        print(f"[Notify Customer Error]: {e}")


def handle_start_edit(chat_id, message_id):
    """Start menyusini tahrirlash (tugma orqali qaytganda)."""
    text = (
        "🥩 *Baxmal Meat Kassa Bot*\n\n"
        "Quyidagi tugmalardan birini tanlang:"
    )
    edit_message(chat_id, message_id, text, reply_markup=main_menu_keyboard())
