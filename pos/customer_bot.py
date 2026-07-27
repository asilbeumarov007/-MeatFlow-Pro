"""
Baxmal Meat — Customer Telegram Bot Engine (Enterprise Omnichannel)
===================================================================
Foydalanuvchilar va Mijozlar uchun E-Commerce, Savat, Delivery/Location,
Click/Payme To'lov cheki va Live Order Tracking integratsiyasi.
"""
import os
import requests
from decimal import Decimal
from datetime import datetime
from django.utils import timezone
from django.db.models import Q
from .models import Customer, Product, Sale, SaleItem, CustomerLog, B2BOrder
from .translit import latin_to_cyrillic, cyrillic_to_latin

CUSTOMER_BOT_TOKEN = os.environ.get('CUSTOMER_BOT_TOKEN', '8728579523:AAG9mtvfeVd95svVNVJ-NnGUOTknTzPkDg8')
ADMIN_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8898055369:AAFbUW9nLVRXwG-xd0oP1ftQ5vZpTjcL4x8')
ADMIN_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '-1004312267841')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000')  # Production da o'zgartiring

API_URL = f"https://api.telegram.org/bot{CUSTOMER_BOT_TOKEN}"

# State tracker for multi-step order flow
# Format: USER_STATES[chat_id] = {'action': '...', 'order_id': 104, 'cart': {...}}
USER_STATES = {}


# ══════════════════════════════════════════════════════════
# TELEGRAM API HELPERS
# ══════════════════════════════════════════════════════════

def send_message(chat_id, text, reply_markup=None, parse_mode='Markdown'):
    """Mijozlar botidan xabar yuborish."""
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
        print(f"[Customer TG Bot] Xabar yuborishda xato: {e}")
        return None


def answer_callback(callback_query_id, text=""):
    """Callback query javobi."""
    try:
        requests.post(f"{API_URL}/answerCallbackQuery", json={
            'callback_query_id': callback_query_id,
            'text': text,
        }, timeout=5)
    except:
        pass


def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode='Markdown'):
    """Xabarni tahrirlash."""
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
        print(f"[Customer TG Bot] Tahrirlashda xato: {e}")
        return None


def send_customer_photo(chat_id, photo_path_or_url, caption=""):
    """Mijozga rasm (masalan QR kod) yuborish."""
    url = f"{API_URL}/sendPhoto"
    try:
        if os.path.exists(photo_path_or_url):
            with open(photo_path_or_url, 'rb') as f:
                r = requests.post(url, data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': f}, timeout=15)
                return r.json()
    except Exception as e:
        print(f"[Customer TG Bot Send Photo Error]: {e}")
        return None


def download_telegram_photo(file_id):
    """Telegram serveridan fotoni yuklab olib media/payment_proofs/ papkaga saqlash."""
    try:
        r = requests.get(f"{API_URL}/getFile?file_id={file_id}", timeout=10).json()
        if r.get('ok'):
            file_path = r['result']['file_path']
            file_url = f"https://api.telegram.org/file/bot{CUSTOMER_BOT_TOKEN}/{file_path}"
            img_r = requests.get(file_url, timeout=15)
            if img_r.status_code == 200:
                target_dir = os.path.join('media', 'payment_proofs')
                os.makedirs(target_dir, exist_ok=True)
                filename = f"proof_tg_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_id[:8]}.jpg"
                rel_path = f"payment_proofs/{filename}"
                full_path = os.path.join(target_dir, filename)
                with open(full_path, 'wb') as f:
                    f.write(img_r.content)
                return rel_path
    except Exception as e:
        print(f"[TG Photo Download Error]: {e}")
    return None



def get_active_payment_settings_details():
    """Admin panelida kiritilgan barcha aktiv to'lov rekvizitlari va QR kodlar."""
    from .models import PaymentSetting
    settings = PaymentSetting.objects.filter(is_active=True)
    if not settings.exists():
        return "💳 `8600 1234 5678 9012` (Baxmal Meat)", []

    lines = []
    qr_list = []
    for s in settings:
        card_str = f"💳 `{s.card_number}`" if s.card_number else ""
        holder_str = f" ({s.card_holder})" if s.card_holder else ""
        instr_str = f"\n📝 _{s.instructions}_" if s.instructions else ""
        lines.append(f"📲 *{s.title}*\n{card_str}{holder_str}{instr_str}")
        if s.qr_code and os.path.exists(s.qr_code.path):
            qr_list.append((s.title, s.qr_code.path))

    return "\n\n".join(lines), qr_list


def send_admin_photo_notification(photo_file_id, caption, reply_markup=None):
    """Admin botiga rasm va inline boshqaruv tugmalari bilan bildirishnoma yuborish."""
    url = f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/sendPhoto"
    payload = {
        'chat_id': ADMIN_CHAT_ID,
        'photo': photo_file_id,
        'caption': caption,
        'parse_mode': 'Markdown',
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.json()
    except Exception as e:
        print(f"[Admin TG Bot Photo Send Error]: {e}")
        return None


def send_admin_text_notification(text, reply_markup=None):
    """Admin botiga matnli bildirishnoma yuborish."""
    url = f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': ADMIN_CHAT_ID,
        'text': text,
        'parse_mode': 'Markdown',
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[Admin TG Bot Text Send Error]: {e}")


# ══════════════════════════════════════════════════════════
# KEYBOARD BUILDERS
# ══════════════════════════════════════════════════════════

def registration_keyboard():
    """Kontakt ulash va qidirish tugmalari."""
    return {
        'keyboard': [
            [{'text': '📱 Telefon raqamni yuborish', 'request_contact': True}],
            [{'text': '🔍 Daftardan qidirish (Ism/Izoh)'}]
        ],
        'resize_keyboard': True
    }


def main_menu_reply_keyboard():
    """Asosiy mijoz menyusi — Telegram + Sayt birlashtirilgan."""
    return {
        'keyboard': [
            [{'text': "🛒 Go'sht Buyurtma Qilish"}, {'text': '📌 Buyurtma Statusi (Live)'}],
            [{'text': "💳 Qarz To'lash (Karta)"}, {'text': "📸 To'lov Chekini Yuborish"}],
            [{'text': '👤 Shaxsiy Kabinet (Balans)'}, {'text': '💰 Qarz va Kredit'}],
            [{'text': "🥩 AI Go'sht Maslahatchisi"}, {'text': '🧾 Xaridlar Tarixi'}],
            [{'text': '💬 Admin bilan Aloqa'}, {'text': "🌐 Veb-saytga O'tish"}]
        ],
        'resize_keyboard': True
    }


def render_telegram_stepper_bar(status):
    """Telegram bot uchun 4 bosqichli Live Progress Bar."""
    if status == 'rejected':
        return "❌ *STATUS:* Rad etildi"
    
    s1 = "🟢 Qabul" if status in ['pending', 'payment_uploaded', 'approved', 'preparing', 'shipping', 'completed'] else "⚪️ Qabul"
    s2 = "🟢 Qadoqlash" if status in ['approved', 'preparing', 'shipping', 'completed'] else "⚪️ Qadoqlash"
    s3 = "🟢 Yo'lda" if status in ['shipping', 'completed'] else "⚪️ Yo'lda"
    s4 = "🟢 Yetkazildi" if status == 'completed' else "⚪️ Yetkazildi"

    return f"{s1} ➔ {s2} ➔ {s3} ➔ {s4}"


def location_reply_keyboard():
    """Lokatsiya yuborish tugmasi."""
    return {
        'keyboard': [
            [{'text': '📍 Manzilni (GPS) Yuborish', 'request_location': True}],
            [{'text': '🏃 Samovivoz (Do\'kondan olib ketish)'}],
            [{'text': '🏠 Asosiy Menyu'}]
        ],
        'resize_keyboard': True
    }


def mask_phone(phone):
    """Telefon raqamini qisman yashirish: +998 90 *** 4567"""
    if not phone or len(phone) < 7:
        return phone or "Yashiringan"
    clean = ''.join(filter(str.isdigit, phone))
    if len(clean) >= 9:
        return f"+{clean[:3]} {clean[3:5]} *** {clean[-4:]}"
    return f"{phone[:3]}***{phone[-3:]}"


# ══════════════════════════════════════════════════════════
# AI & GEMINI HELPERS
# ══════════════════════════════════════════════════════════

def query_gemini_meat_assistant(user_prompt):
    """Gemini AI orqali go'sht va retseptlar bo'yicha maslahat olish."""
    if not GEMINI_API_KEY:
        return "🥩 Baxmal Meat: Shashlik uchun mol va qo'y go'shtining yumshoq qismlari, qozonkabob uchun esa qobirg'a va biqin qismlari eng yaxshi tanlovdir!"

    products_str = ", ".join([f"{p.name} ({p.price_per_kg:,.0f} so'm/kg)" for p in Product.objects.filter(is_active=True)])
    system_instruction = (
        "Siz Baxmal Meat go'sht do'konining professional AI maslahatchisisiz. "
        "Mijozlarga retseptlar, shashlik/qozonkabob uchun necha kg go'sht kerakligi va qaysi qism mos kelishi bo'yicha "
        f"do'konda mavjud mahsulotlar ({products_str}) asosida qisqa, xushmuomala va o'zbek tilida maslahat bering."
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": f"{system_instruction}\n\nMijoz savoli: {user_prompt}"}]}]
    }
    try:
        r = requests.post(url, json=payload, timeout=12)
        res_data = r.json()
        text = res_data['candidates'][0]['content']['parts'][0]['text']
        return text
    except Exception as e:
        print(f"[Gemini AI Error]: {e}")
        return "🥩 *Baxmal Meat Maslahati:* Shashlik va kabob uchun yumshoq son va qobirg'a go'shtlari eng yaxshi tanlovdir. Bir kishiga o'rtacha 300-400 gramm go'sht hisoblanadi."


def find_customer_candidates(query):
    """Mijozlar va ta'minotchilar orasidan AI/Smart qidiruv."""
    query = query.strip()
    if not query:
        return []

    q_latin = cyrillic_to_latin(query)
    q_cyrillic = latin_to_cyrillic(query)
    digits = ''.join(filter(str.isdigit, query))

    filters = (
        Q(first_name__icontains=query) | Q(last_name__icontains=query) |
        Q(first_name__icontains=q_latin) | Q(last_name__icontains=q_latin) |
        Q(first_name__icontains=q_cyrillic) | Q(last_name__icontains=q_cyrillic) |
        Q(custom_id__icontains=query) | Q(note__icontains=query) |
        Q(note__icontains=q_latin) | Q(note__icontains=q_cyrillic)
    )

    if len(digits) >= 4:
        filters |= Q(phone__icontains=digits)

    candidates = Customer.objects.filter(filters).distinct()[:5]
    return list(candidates)


def get_customer_by_chat_id(chat_id):
    """Chat ID orqali mijozni olish."""
    return Customer.objects.filter(telegram_chat_id=str(chat_id)).first()


# ══════════════════════════════════════════════════════════
# CORE HANDLERS
# ══════════════════════════════════════════════════════════

def handle_customer_update(update):
    """Telegram Update-ni qayta ishlash."""
    if 'message' in update:
        message = update['message']
        chat_id = str(message['chat']['id'])
        text = message.get('text', '').strip()
        contact = message.get('contact')
        location = message.get('location')
        photo = message.get('photo')

        customer = get_customer_by_chat_id(chat_id)

        # 1. Kontakt yuborilganda (Avtorizatsiya)
        if contact:
            phone_num = contact.get('phone_number', '').replace('+', '').strip()
            possible_phones = [phone_num, f"+{phone_num}", f"998{phone_num[-9:]}", f"+998{phone_num[-9:]}"]
            matched_customer = Customer.objects.filter(Q(phone__in=possible_phones) | Q(phone__icontains=phone_num[-9:])).first()

            if matched_customer:
                matched_customer.telegram_chat_id = chat_id
                matched_customer.save()
                msg = f"✅ *Muvaffaqiyatli ulandiz!*\n\nHurmatli *{matched_customer.first_name} {matched_customer.last_name or ''}*, profilingiz Baxmal Meat botiga biriktirildi."
                send_message(chat_id, msg, reply_markup=main_menu_reply_keyboard())
            else:
                msg = f"⚠️ *Afsuski, telefon raqamingiz (+{phone_num}) bazadan topilmadi.*\n\nQarz daftardagi ismingiz yoki izohingizni matn ko'rinishida yozib yuboring (masalan: *Abduxaliq tog'a* yoki *Qo'shni Eshmat*)."
                send_message(chat_id, msg, reply_markup=registration_keyboard())
            return

        # 2. Ulash so'rovi holatidagi yoki ro'yxatdan o'tmagan foydalanuvchi
        if not customer and not text.startswith('claim_'):
            if text == '🔍 Daftardan qidirish (Ism/Izoh)' or text.startswith('/start'):
                msg = (
                    "🥩 *Baxmal Meat — Akkauntni Ulash*\n\n"
                    "Iltimos, pastdagi *'📱 Telefon raqamni yuborish'* tugmasini bosing yoki "
                    "qarz daftarda ismingiz/izohingiz qanday yozilgan bo'lsa shuni matn qilib yuboring:\n\n"
                    "✍️ *Misol:* `Abduxaliq tog'a` yoki `901234567`"
                )
                send_message(chat_id, msg, reply_markup=registration_keyboard())
                return

            # AI Smart Candidate Search
            candidates = find_customer_candidates(text)
            if candidates:
                send_message(chat_id, f"🔍 *'{text}'* bo'yicha bazadan {len(candidates)} ta mos profil topildi.\nO'zingizga tegishlisini tanlang:")
                for c in candidates:
                    is_barter = hasattr(c, 'supplier_profile') and c.supplier_profile is not None
                    role_tag = " [Chorvador / Ta'minotchi]" if is_barter else ""
                    note_tag = f"\n📝 *Daftardagi izoh:* {c.note}" if c.note else ""
                    
                    card_msg = (
                        f"👤 *{c.first_name} {c.last_name or ''}*{role_tag}\n"
                        f"🆔 *ID:* `{c.custom_id}`\n"
                        f"📞 *Tel:* `{mask_phone(c.phone)}` {note_tag}\n"
                        f"💰 *Joriy Qarz:* `{c.debt_amount:,.0f}` so'm | ⭐ *Skoring:* {c.get_credit_score()}"
                    )
                    reply_markup = {
                        'inline_keyboard': [
                            [{'text': f"✅ Shu menman (ID: {c.custom_id})", 'callback_data': f"claim_profile_{c.id}"}]
                        ]
                    }
                    send_message(chat_id, card_msg, reply_markup=reply_markup)
            else:
                msg = (
                    f"⚠️ *'{text}'* bo'yicha ma'lumotlar bazasidan hech narsa topilmadi.\n\n"
                    "Iltimos, ismingizni boshqacha yozib ko'ring yoki *'📱 Telefon raqamni yuborish'* tugmasini bosing."
                )
                send_message(chat_id, msg, reply_markup=registration_keyboard())
            return

        # Handle '🏠 Asosiy Menyu' reset
        if text == '🏠 Asosiy Menyu' or text == '/start':
            USER_STATES.pop(chat_id, None)
            send_message(chat_id, f"👋 Xush kelibsiz, *{customer.first_name if customer else 'Mijoz'}*!", reply_markup=main_menu_reply_keyboard())
            return

        # 3. Lokatsiya kelganda (Delivery address)
        if location and chat_id in USER_STATES and USER_STATES[chat_id].get('action') == 'awaiting_location':
            order_id = USER_STATES[chat_id].get('order_id')
            lat = location.get('latitude')
            lng = location.get('longitude')

            try:
                order = B2BOrder.objects.get(id=order_id)
                order.delivery_type = 'delivery'
                order.latitude = lat
                order.longitude = lng
                order.delivery_address = f"GPS Koordinata: {lat:.6f}, {lng:.6f}"
                order.save()

                USER_STATES[chat_id] = {'action': 'awaiting_payment_proof', 'order_id': order.id}

                total_sum = order.requested_weight * order.product.price_per_kg
                pay_details, qr_images = get_active_payment_settings_details()

                msg = (
                    f"💳 *TO'LOVNI AMALGA OSHIRISH*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📦 *Mahsulot:* {order.product.name} ({order.requested_weight} kg)\n"
                    f"🚗 *Yetkazish:* GPS Lokatsiya qabul qilindi\n"
                    f"💵 *Jami Summa:* `{total_sum:,.0f}` so'm\n\n"
                    f"{pay_details}\n\n"
                    f"📸 *To'lovni amalga oshirgach, to'lov cheki (kvitansiya/skrinshot) fotosini ushbu chatga yuboring!*"
                )
                send_message(chat_id, msg)

                # Send QR code photos if available
                for qr_title, qr_path in qr_images:
                    send_customer_photo(chat_id, qr_path, caption=f"📲 *{qr_title} QR Kodi* — Telefon kamerasi orqali skaner qilib to'lang")
            except Exception as e:
                send_message(chat_id, f"⚠️ Xato: {e}")
            return

        # 4. Foto yuborilganda (To'lov cheki)
        if photo:
            current_state = USER_STATES.get(chat_id, {})
            order_id = current_state.get('order_id') if isinstance(current_state, dict) else None

            if order_id or current_state == 'awaiting_payment_proof':
                file_id = photo[-1]['file_id']
                USER_STATES.pop(chat_id, None)

                # Download photo file to media folder
                saved_proof_path = download_telegram_photo(file_id)

                if order_id:
                    try:
                        order = B2BOrder.objects.get(id=order_id)
                        order.status = 'payment_uploaded'
                        if saved_proof_path:
                            order.payment_proof_image = saved_proof_path
                        order.save()

                        # Also log to CustomerLog for chat timeline visibility
                        img_url_path = f"/media/{saved_proof_path}" if saved_proof_path else ""
                        CustomerLog.objects.create(
                            customer=customer,
                            log_type='bonus',
                            title="Mijoz xabari",
                            message=f"📸 To'lov cheki yuborildi (Buyurtma #{order.id})",
                            details={'image_url': img_url_path, 'order_id': order.id, 'source': 'telegram'},
                            amount=Decimal('0.00')
                        )

                        total_price = order.requested_weight * order.product.price_per_kg

                        # Build Admin Notification Card with Inline Action Buttons
                        admin_caption = (
                            f"💳 *YANGI TO'LOV CHEKI VA BUYURTMA!* (Buyurtma #{order.id})\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"👤 *Mijoz:* {customer.first_name} {customer.last_name or ''}\n"
                            f"🆔 *ID:* `{customer.custom_id}` | 📞 `{customer.phone}`\n"
                            f"⭐ *Skoring:* {customer.get_credit_score()}\n\n"
                            f"🥩 *Mahsulot:* {order.product.name} ({order.requested_weight} kg)\n"
                            f"🚗 *Turi:* {order.get_delivery_type_display()}\n"
                            f"📍 *Manzil:* {order.delivery_address or 'Do\'kondan olib ketish'}\n"
                            f"💵 *To'lov Summasi:* `{total_price:,.0f}` so'm"
                        )
                        reply_markup = {
                            'inline_keyboard': [
                                [
                                    {'text': '✅ Tasdiqlash', 'callback_data': f"adm_appr_{order.id}"},
                                    {'text': '🥩 Qadoqlash', 'callback_data': f"adm_prep_{order.id}"}
                                ],
                                [
                                    {'text': '🚚 Kuryerga berish', 'callback_data': f"adm_ship_{order.id}"},
                                    {'text': '❌ Rad etish', 'callback_data': f"adm_rej_{order.id}"}
                                ]
                            ]
                        }
                        send_admin_photo_notification(file_id, admin_caption, reply_markup=reply_markup)

                        cust_msg = (
                            f"🎉 *To'lov chekingiz va buyurtmangiz qabul qilindi!* (Buyurtma #{order.id})\n\n"
                            f"📦 *{order.product.name}:* {order.requested_weight} kg\n"
                            f"💵 *Jami:* `{total_price:,.0f}` so'm\n\n"
                            f"⏳ Admin to'lovni tekshirib tasdiqlagach, buyurtma ijroga beriladi.\n"
                            f"📌 Buyurtma holatini *'📌 Buyurtma Statusi (Live)'* tugmasi orqali kuzatib borishingiz mumkin."
                        )
                        send_message(chat_id, cust_msg, reply_markup=main_menu_reply_keyboard())
                    except Exception as e:
                        send_message(chat_id, f"⚠️ Buyurtmaga chek biriktirishda xato: {e}")
                else:
                    if saved_proof_path:
                        img_url_path = f"/media/{saved_proof_path}"
                        CustomerLog.objects.create(
                            customer=customer,
                            log_type='bonus',
                            title="Mijoz xabari",
                            message="📸 To'lov cheki yuborildi",
                            details={'image_url': img_url_path, 'source': 'telegram'},
                            amount=Decimal('0.00')
                        )
                    admin_msg = (
                        f"💳 *Yangi To'lov Cheki Yuborildi!*\n\n"
                        f"👤 *Mijoz:* {customer.first_name} {customer.last_name or ''}\n"
                        f"🆔 *ID:* `{customer.custom_id}` | 📞 {customer.phone}\n"
                        f"📊 *Joriy qarz:* {customer.debt_amount:,} so'm"
                    )
                    send_admin_photo_notification(file_id, admin_msg)
                    send_message(chat_id, "✅ To'lov chekingiz adminga yuborildi! Tekshirilgach balansingiz yangilanadi.", reply_markup=main_menu_reply_keyboard())
                return

        # 5. Asosiy Menyu Buyruqlari
        if text == '🛒 Go\'sht Buyurtma Qilish':
            products = Product.objects.filter(is_active=True)
            if not products.exists():
                send_message(chat_id, "⚠️ Hozirda sotuvda mahsulotlar mavjud emas.")
                return

            inline_keyboard = []
            for p in products:
                inline_keyboard.append([
                    {'text': f"{p.name} — {p.price_per_kg:,.0f} so'm/kg", 'callback_data': f"order_prod_{p.id}"}
                ])

            reply_markup = {'inline_keyboard': inline_keyboard}
            send_message(chat_id, "🥩 *Buyurtma qilmoqchi bo'lgan go'sht turini tanlang:*", reply_markup=reply_markup)

        elif text == '📌 Buyurtma Statusi (Live)':
            orders = B2BOrder.objects.filter(customer=customer).order_by('-created_at')[:3]
            if not orders.exists():
                send_message(chat_id, "ℹ️ Sizda aktiv buyurtmalar mavjud emas.")
                return

            lines = ["📌 *JONLI BUYURTMA STATUSLARI (LIVE TRACKING):*", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
            for o in orders:
                status_emoji = {
                    'pending': '⏳ Chek kutilmoqda',
                    'payment_uploaded': '📸 Chek tekshirilmoqda',
                    'approved': '✅ Admin tasdiqladi',
                    'preparing': '🥩 Go\'sht tortilmoqda/Qadoqlanmoqda',
                    'shipping': '🚚 Kuryer yo\'lda',
                    'completed': '🎉 Yetkazib berildi',
                    'rejected': '❌ Rad etildi'
                }.get(o.status, o.get_status_display())

                total_price = o.requested_weight * o.product.price_per_kg
                stepper_bar = render_telegram_stepper_bar(o.status)
                lines.append(
                    f"📦 *Buyurtma #{o.id}:* {o.product.name} ({o.requested_weight} kg)\n"
                    f"💵 Jami: `{total_price:,.0f}` so'm ({o.get_delivery_type_display()})\n"
                    f"{stepper_bar}\n"
                    f"📊 *Holat:* *{status_emoji}*\n"
                    f"📅 {o.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                )
            send_message(chat_id, "\n".join(lines), reply_markup=main_menu_reply_keyboard())

        elif text in ["💳 Qarz To'lash (Karta)", '💳 Karta va Rekvizitlar', '💳 Karta Rekviziti', "💳 Qarz To'lash"]:
            pay_details, qr_images = get_active_payment_settings_details()
            debt_sum = customer.debt_amount if customer else Decimal('0.00')
            debt_str = f"💰 *Sizning Joriy Qarzingiz:* `{debt_sum:,.0f}` so'm\n\n" if debt_sum > 0 else "💰 *Sizda hozircha qarz mavjud emas.*\n\n"

            msg = (
                "💳 *QARZ TO'LASH VA KARTA REKVIZITLARI*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 *Mijoz:* {customer.first_name if customer else 'Mijoz'} ({customer.custom_id if customer else ''})\n"
                f"{debt_str}"
                "🏦 *Do'kon Plastik Karta Raqami:*\n"
                "`8600123456789012` *(ustiga 1 marta bossangiz nusxalanadi!)*\n"
                "Ega: *Baxmal Meat Enterprise*\n"
                "To'lov Turlari: *Click / Payme / Bank Ilovasi*\n\n"
                f"{pay_details}\n\n"
                "📸 *To'lovni amalga oshirgach, pastdagi '📸 To'lov Chekini Yuborish' tugmasini bosing va chek fotosini chatga yuboring!*"
            )
            inline_kb = {
                'inline_keyboard': [
                    [{'text': "📸 Hozir To'lov Chekini Yuborish", 'callback_data': 'upload_proof_now'}],
                    [{'text': "🌐 Saytdan To'lash (Click/Payme)", 'url': f"{SITE_URL}/pos/my-cabinet/"}]
                ]
            }
            send_message(chat_id, msg, reply_markup=inline_kb)
            for qr_title, qr_path in qr_images:
                send_customer_photo(chat_id, qr_path, caption=f"📲 *{qr_title} QR Kodi*")

        elif text in ["📸 To'lov Chekini Yuborish", "📸 To'lov Cheki"]:
            USER_STATES[chat_id] = 'awaiting_payment_proof'
            msg = (
                "📸 *TO'LOV CHEKINI YUBORISH*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "💳 *Do'kon Karta Raqami:* `8600123456789012` (Baxmal Meat)\n\n"
                "Iltimos, Click/Payme yoki bank ilovasi orqali bajarilgan to'lov kvitansiyasi (skrinshot yoki foto)ni ushbu chatga yuboring.\n\n"
                "📌 *Foto kelishi bilan admin paneli hamda balansingizga avtomatik biriktiriladi!*"
            )
            send_message(chat_id, msg)

        elif text == '👤 Shaxsiy Kabinet (Balans)':
            smart_score = customer.calculate_smart_score()
            credit_score = customer.get_credit_score()
            barter_info = ""
            if hasattr(customer, 'supplier_profile') and customer.supplier_profile:
                sup_debt = customer.supplier_profile.our_debt
                barter_info = f"\n🚜 *Bizning sizdan qarzimiz:* `{sup_debt:,.0f}` so'm"

            msg = (
                f"👤 *SHAXSIY KABINET*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"👤 *F.I.SH:* {customer.first_name} {customer.last_name or ''}\n"
                f"🆔 *Mijoz ID:* `{customer.custom_id}`\n"
                f"📞 *Telefon:* `{customer.phone}`\n\n"
                f"💰 *Joriy Qarz:* `{customer.debt_amount:,.0f}` so'm\n"
                f"💳 *Kredit Limiti:* `{customer.debt_limit:,.0f}` so'm\n"
                f"💎 *Bonus Ballar:* `{customer.bonus_points}` ball\n"
                f"⭐ *Ishonchlilik Darajasi:* *{credit_score}* ({smart_score}/100 ball)"
                f"{barter_info}"
            )
            send_message(chat_id, msg, reply_markup=main_menu_reply_keyboard())

        elif text == '🥩 AI Go\'sht Maslahatchisi':
            USER_STATES[chat_id] = {'action': 'awaiting_ai_prompt'}
            msg = (
                "🤖 *Baxmal Meat — AI Maslahatchisi*\n\n"
                "Manga go'sht retseptlari, shashlik/qozonkabob uchun necha kg go'sht va qaysi qism mos kelishi haqida istalgan savolingizni berishingiz mumkin:\n\n"
                "✍️ *Misol:* `10 kishi shashlik uchun necha kg go'sht kerak?`"
            )
            send_message(chat_id, msg)

        elif isinstance(USER_STATES.get(chat_id), dict) and USER_STATES[chat_id].get('action') == 'awaiting_ai_prompt':
            USER_STATES.pop(chat_id, None)
            send_message(chat_id, "🤖 *AI o'ylanmoqda...* ⏳")
            ai_reply = query_gemini_meat_assistant(text)
            send_message(chat_id, f"🥩 *AI Maslahatchi Javobi:*\n\n{ai_reply}", reply_markup=main_menu_reply_keyboard())

        elif text == '🧾 Xaridlar Tarixi':
            sales = Sale.objects.filter(customer=customer).order_by('-created_at')[:5]
            if not sales.exists():
                send_message(chat_id, "ℹ️ Sizda hali xaridlar tarixi mavjud emas.")
                return

            text_lines = ["🧾 *OXIRGI XARIDLARINGIZ:*", "━━━━━━━━━━━━━━━━━━━"]
            for s in sales:
                date_str = s.created_at.strftime('%d.%m.%Y %H:%M')
                items = s.items.all()
                item_str = ", ".join([f"{it.product.name} ({it.weight} kg)" for it in items])
                text_lines.append(
                    f"📅 *{date_str}* (Chek #{s.id})\n"
                    f"📦 {item_str}\n"
                    f"💵 Jami: `{s.final_paid:,.0f}` so'm ({s.get_payment_method_display()})\n"
                )
            send_message(chat_id, "\n".join(text_lines), reply_markup=main_menu_reply_keyboard())

        elif text == '💬 Admin bilan Aloqa':
            USER_STATES[chat_id] = 'awaiting_support_msg'
            send_message(chat_id, "✍️ Adminga yubormoqchi bo'lgan xabaringizni yozib qoldiring:")

        elif USER_STATES.get(chat_id) == 'awaiting_support_msg':
            USER_STATES.pop(chat_id, None)
            # Save to CustomerLog so it appears in web cabinet chat too
            CustomerLog.objects.create(
                customer=customer,
                log_type='bonus',
                title="Mijoz xabari",
                message=text,
                details={'source': 'telegram'},
                amount=Decimal('0.00')
            )
            admin_msg = (
                f"💬 *Mijozdan yangi xabar!*\n\n"
                f"👤 *Mijoz:* {customer.first_name} ({customer.custom_id})\n"
                f"📞 *Tel:* {customer.phone}\n\n"
                f"💬 *Xabar:* {text}"
            )
            send_admin_text_notification(admin_msg)
            send_message(chat_id, "✅ Xabaringiz adminga yetkazildi va saytdagi chatda ham ko'rinadi. Tez orada javob beramiz!", reply_markup=main_menu_reply_keyboard())

        elif text == '💰 Qarz va Kredit':
            smart_score = customer.calculate_smart_score()
            credit_score = customer.get_credit_score()
            limit_used_pct = 0
            if customer.debt_limit > 0:
                limit_used_pct = min(100, int(customer.debt_amount / customer.debt_limit * 100))

            # Progress bar for credit limit usage
            filled = limit_used_pct // 10
            bar = '█' * filled + '░' * (10 - filled)

            score_emoji = '🟢' if smart_score >= 80 else ('🟡' if smart_score >= 50 else '🔴')
            msg = (
                f"💰 *QARZ VA KREDIT MA'LUMOTLARI*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"💳 *Joriy Qarz:* `{customer.debt_amount:,.0f}` so'm\n"
                f"🏦 *Kredit Limiti:* `{customer.debt_limit:,.0f}` so'm\n"
                f"📊 *Limitdan foydalanish:* `{limit_used_pct}%`\n"
                f"`{bar}` {limit_used_pct}%\n\n"
                f"💎 *Bonus Ballar:* `{customer.bonus_points}` ball\n"
                f"{score_emoji} *Kredit Skoring:* `{credit_score}`\n"
                f"📈 *Smart Skoring:* `{smart_score}/100 ball`\n\n"
                f"{'⚠️ Diqqat: Kredit limitingiz tugab qolmoqda!' if limit_used_pct > 80 else '✅ Kredit holatiz yaxshi.'}"
            )
            inline_kb = {
                'inline_keyboard': [
                    [{'text': "💳 Qarzni Hozir To'lash (Karta)", 'callback_data': 'pay_debt_now'}]
                ]
            }
            send_message(chat_id, msg, reply_markup=inline_kb)

        elif text == "🌐 Veb-saytga O'tish":
            cabinet_url = f"{SITE_URL}/pos/my-cabinet/"
            inline_kb = {
                'inline_keyboard': [
                    [{'text': '👤 Shaxsiy Kabinet', 'url': cabinet_url}],
                    [{'text': '💬 Real-time Chat (Sayt)', 'url': cabinet_url + '#chat'}],
                ]
            }
            msg = (
                f"🌐 *Baxmal Meat — Veb Sayt*\n\n"
                f"Saytdagi shaxsiy kabinetingizda quyidagilar mavjud:\n"
                f"• 💬 Real-time chat (Telegramdan kelgan xabarlar ko'rinadi)\n"
                f"• 📦 B2B buyurtmalar\n"
                f"• 📊 Qarz va to'lovlar tarixi\n"
                f"• 📸 To'lov cheki yuklash\n\n"
                f"👇 Quyidagi tugmani bosib kiring:"
            )
            send_message(chat_id, msg, reply_markup=inline_kb)

    # 6. Callback Queries (Inline buttons)
    elif 'callback_query' in update:
        cq = update['callback_query']
        cq_id = cq['id']
        chat_id = str(cq['message']['chat']['id'])
        data = cq.get('data', '')

        answer_callback(cq_id)

        # Profile claim / linking
        if data.startswith('claim_profile_'):
            cust_id = int(data.replace('claim_profile_', ''))
            try:
                target_customer = Customer.objects.get(id=cust_id)
                target_customer.telegram_chat_id = chat_id
                target_customer.save()

                msg = (
                    f"✅ *Muvaffaqiyatli ulandiz!*\n\n"
                    f"Hurmatli *{target_customer.first_name} {target_customer.last_name or ''}*, "
                    f"profilingiz (ID: `{target_customer.custom_id}`) Telegram botingizga muvaffaqiyatli biriktirildi."
                )
                edit_message(chat_id, cq['message']['message_id'], msg)
                send_message(chat_id, "Asosiy menyudan foydalanishingiz mumkin:", reply_markup=main_menu_reply_keyboard())
            except Customer.DoesNotExist:
                send_message(chat_id, "⚠️ Tanlangan profil bazada topilmadi.")

        elif data == 'upload_proof_now':
            USER_STATES[chat_id] = 'awaiting_payment_proof'
            send_message(chat_id, "📸 *To'lov chekini (kvitansiya/skrinshot) fotosini chatga yuboring:*")

        elif data == 'pay_debt_now':
            pay_details, qr_images = get_active_payment_settings_details()
            customer = get_customer_by_chat_id(chat_id)
            debt_sum = customer.debt_amount if customer else Decimal('0.00')
            debt_str = f"💰 *Sizning Joriy Qarzingiz:* `{debt_sum:,.0f}` so'm\n\n" if debt_sum > 0 else "💰 *Sizda hozircha qarz mavjud emas.*\n\n"

            msg = (
                "💳 *QARZ TO'LASH VA KARTA REKVIZITLARI*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{debt_str}"
                "🏦 *Do'kon Plastik Karta Raqami:*\n"
                "`8600123456789012` *(ustiga 1 marta bossangiz nusxalanadi!)*\n"
                "Ega: *Baxmal Meat Enterprise*\n"
                "To'lov Turlari: *Click / Payme / Bank Ilovasi*\n\n"
                f"{pay_details}\n\n"
                "📸 *To'lovni amalga oshirgach, pastdagi '📸 To'lov Chekini Yuborish' tugmasini bosing va chek fotosini chatga yuboring!*"
            )
            inline_kb = {
                'inline_keyboard': [
                    [{'text': "📸 Hozir To'lov Chekini Yuborish", 'callback_data': 'upload_proof_now'}],
                    [{'text': "🌐 Saytdan To'lash (Click/Payme)", 'url': f"{SITE_URL}/pos/my-cabinet/"}]
                ]
            }
            send_message(chat_id, msg, reply_markup=inline_kb)

        elif data.startswith('order_prod_'):
            prod_id = int(data.replace('order_prod_', ''))
            try:
                product = Product.objects.get(id=prod_id)
                inline_keyboard = [
                    [
                        {'text': '1 kg', 'callback_data': f"confirm_ord_{product.id}_1"},
                        {'text': '2 kg', 'callback_data': f"confirm_ord_{product.id}_2"},
                        {'text': '5 kg', 'callback_data': f"confirm_ord_{product.id}_5"},
                    ],
                    [
                        {'text': '10 kg', 'callback_data': f"confirm_ord_{product.id}_10"},
                        {'text': '20 kg', 'callback_data': f"confirm_ord_{product.id}_20"},
                    ]
                ]
                edit_message(chat_id, cq['message']['message_id'], f"📦 *{product.name}* ({product.price_per_kg:,.0f} so'm/kg)\n\nKerakli og'irlikni tanlang:", reply_markup={'inline_keyboard': inline_keyboard})
            except Product.DoesNotExist:
                send_message(chat_id, "⚠️ Mahsulot topilmadi.")

        elif data.startswith('confirm_ord_'):
            user_from = cq.get('from', {})
            user_id = str(user_from.get('id', chat_id))
            customer = get_customer_by_chat_id(chat_id) or get_customer_by_chat_id(user_id)

            if not customer:
                first_name = user_from.get('first_name', 'Telegram Mijoz')
                last_name = user_from.get('last_name', '')
                phone = f"+tg_{user_id}"
                custom_id = f"TG-{user_id[-6:] if len(user_id) >= 6 else user_id}"
                
                customer, _ = Customer.objects.get_or_create(
                    phone=phone,
                    defaults={
                        'first_name': first_name,
                        'last_name': last_name,
                        'custom_id': custom_id,
                        'telegram_chat_id': user_id,
                        'note': f"Telegram Bot orqali mehmon profil (Chat ID: {user_id})"
                    }
                )
                if not customer.telegram_chat_id:
                    customer.telegram_chat_id = user_id
                    customer.save()

            parts = data.split('_')
            prod_id = int(parts[2])
            weight = Decimal(parts[3])

            try:
                product = Product.objects.get(id=prod_id)
                order = B2BOrder.objects.create(
                    customer=customer,
                    product=product,
                    requested_weight=weight,
                    status='pending',
                    notes="Telegram Bot orqali yaratilgan buyurtma draft"
                )

                USER_STATES[chat_id] = {'action': 'awaiting_location', 'order_id': order.id}

                msg = (
                    f"🛵 *YETKAZIB BERISH TURINI TANLANG:*\n\n"
                    f"📦 *Mahsulot:* {product.name} ({weight} kg)\n"
                    f"💵 *Jami:* `{weight * product.price_per_kg:,.0f}` so'm\n\n"
                    f"Iltimos, pastdagi *'📍 Manzilni (GPS) Yuborish'* tugmasini bosing yoki Samovivozni tanlang."
                )
                edit_message(chat_id, cq['message']['message_id'], msg)
                send_message(chat_id, "Manzil belgilash:", reply_markup=location_reply_keyboard())
            except Exception as e:
                print(f"[Customer TG Bot Order Error]: {e}")
                send_message(chat_id, f"⚠️ Buyurtma yaratishda xato: {str(e)}", parse_mode=None)
