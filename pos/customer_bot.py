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

CUSTOMER_BOT_TOKEN = os.environ.get('CUSTOMER_BOT_TOKEN', '')
ADMIN_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
ADMIN_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
SITE_URL = os.environ.get('SITE_URL', 'https://baxmalmeat.uz')  # Production rasmiy domeningiz

API_URL = f"https://api.telegram.org/bot{CUSTOMER_BOT_TOKEN}"

# State tracker for multi-step order flow
# Format: USER_STATES[chat_id] = {'action': '...', 'order_id': 104, 'cart': {...}}
USER_STATES = {}


# ══════════════════════════════════════════════════════════
# TELEGRAM API HELPERS
# ══════════════════════════════════════════════════════════

def send_message(chat_id, text, reply_markup=None, parse_mode='Markdown'):
    """Mijozlar botidan xabar yuborish (Markdown xato bo'lsa avtomatik oddiy matnda yuboradi)."""
    payload = {
        'chat_id': chat_id,
        'text': text,
    }
    if parse_mode:
        payload['parse_mode'] = parse_mode
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        r = requests.post(f"{API_URL}/sendMessage", json=payload, timeout=10)
        res = r.json()
        if not res.get('ok') and parse_mode:
            # Fallback retry without markdown formatting
            payload.pop('parse_mode', None)
            r2 = requests.post(f"{API_URL}/sendMessage", json=payload, timeout=10)
            return r2.json()
        return res
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
        res = r.json()
        if not res.get('ok'):
            payload.pop('parse_mode', None)
            r2 = requests.post(url, json=payload, timeout=10)
            return r2.json()
        return res
    except Exception as e:
        print(f"[Admin TG Bot Photo Send Error]: {e}")
        return None


def send_admin_text_notification(text, reply_markup=None):
    """Admin botiga matnli bildirishnoma yuborish (xavfsiz retry bilan)."""
    url = f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': ADMIN_CHAT_ID,
        'text': text,
        'parse_mode': 'Markdown',
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        r = requests.post(url, json=payload, timeout=10)
        res = r.json()
        if not res.get('ok'):
            payload.pop('parse_mode', None)
            r2 = requests.post(url, json=payload, timeout=10)
            return r2.json()
        return res
    except Exception as e:
        print(f"[Admin TG Bot Text Send Error]: {e}")
        return None


def query_gemini_meat_assistant(prompt):
    """AI Go'sht Maslahatchisi — Gemini AI + O'zbek milliy retseptlar intellektual yordamchi."""
    import re
    prompt_lower = prompt.lower()
    from pos.models import Product

    # Get active products in store
    products = Product.objects.filter(is_active=True).select_related('stock')
    prod_list = []
    for p in products:
        qty = p.stock.quantity if hasattr(p, 'stock') else 0
        prod_list.append(f"• *{p.name}* — `{p.price_per_kg:,.0f}` so'm/kg (Zaxira: {qty:.1f} kg)")
    prod_text = "\n".join(prod_list) if prod_list else "• Mahsulotlar mavjud"

    # Extract person count if mentioned (e.g. "4 kishi", "10 odam", "2 kishiga")
    person_match = re.search(r'(\d+)\s*(kishi|odam|kishilik)', prompt_lower)
    person_count = int(person_match.group(1)) if person_match else None

    # 1. Try Gemini API if GEMINI_API_KEY is configured
    from django.conf import settings
    api_key = os.environ.get('GEMINI_API_KEY', '').strip() or getattr(settings, 'GEMINI_API_KEY', '').strip() or GEMINI_API_KEY
    if api_key:
        models_to_try = ['gemini-3.6-flash', 'gemini-3.7-flash', 'gemini-3.5-flash']
        products_str = ", ".join([f"{p.name} ({p.price_per_kg:,.0f} so'm/kg)" for p in products])
        system_instruction = (
            "Siz Baxmal Meat go'sht do'konining professional AI maslahatchisisiz. "
            "Mijozlarga retseptlar, osh/shashlik/qozonkabob/jarkob uchun necha kg go'sht kerakligi va qaysi qism mos kelishi bo'yicha "
            f"do'konda mavjud mahsulotlar ({products_str}) asosida qisqa, xushmuomala va o'zbek tilida maslahat bering."
        )
        for model_name in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                payload = {
                    "contents": [{"parts": [{"text": f"{system_instruction}\n\nMijoz savoli: {prompt}"}]}]
                }
                r = requests.post(url, json=payload, timeout=30)
                if r.status_code == 200:
                    res_data = r.json()
                    text = res_data['candidates'][0]['content']['parts'][0]['text']
                    return f"{text}\n\n🛒 *Baxmal Meat Do'konida Mavjud:* \n{prod_text}"
            except Exception as e:
                continue

    # 2. Rule-Based Smart NLP & Math Engine
    # Jarkop / Jarkob / Qovurma
    if any(w in prompt_lower for w in ['jarkob', 'jarkop', 'jarkov', 'zharkop', 'jarkovda']):
        n_persons = person_count or 4
        meat_kg = n_persons * 0.25
        potatoes_g = n_persons * 200
        return (
            f"🥘 *JARKOP (JARKOB) UCHUN ANIQ ME'YOR VA TAVSIYA:*\n\n"
            f"👤 *Insonlar soni:* **{n_persons} kishi**\n"
            f"🥩 *Kerakli toza go'sht:* **{meat_kg:.1f} kg** (Mol son lahm yoki biqin qismi)\n"
            f"🥔 *Qo'shimchalar:* **{potatoes_g}g** kartoshka, 2 ta piyoz, **150g** dumba yog'i\n\n"
            f"💡 *Pishirish siri:* Go'sht va dumbani o'rtacha olovda qizartirib qovurib olib, keyin past olovda dimlasangiz, jarkop o'ta sersharbat va mazzali chiqadi.\n\n"
            f"🛒 *Baxmal Meat Do'konida Mavjud:* \n{prod_text}"
        )
    # Osh / Palov / Plov
    elif any(w in prompt_lower for w in ['osh', 'palov', 'plov', 'guruch']):
        n_persons = person_count or 6
        rice_kg = n_persons * 0.15
        meat_kg = rice_kg * 1.1
        return (
            f"🍚 *OSH VA PALOV UCHUN MUKAMMAL TAVSIYA:*\n\n"
            f"👤 *Hisob-kitob:* **{n_persons} kishi** uchun (~{rice_kg:.1f} kg guruch)\n"
            f"🥩 *Kerakli go'sht:* **{meat_kg:.1f} kg** (Mol son lahm + 1-2 bo'lak qobirg'a suyagi)\n"
            f"🧈 *Dumba yog'i:* **{n_persons * 40}g** dumba yog'i\n\n"
            f"💡 *Pishirish siri:* Osh lazzatli bo'lishi uchun son go'shti (lahm) bilan birga biroz qobirg'a suyagi va dumba solish maslahat beriladi.\n\n"
            f"🛒 *Baxmal Meat Do'konida Mavjud:* \n{prod_text}"
        )
    # Shashlik / Kabob
    elif any(w in prompt_lower for w in ['kabob', 'shashlik', 'gijda']):
        n_persons = person_count or 4
        meat_kg = n_persons * 0.3
        fat_g = n_persons * 50
        return (
            f"🥩 *SHASHLIK VA KABOB UCHUN TAVSIYA:*\n\n"
            f"👤 *Insonlar soni:* **{n_persons} kishi**\n"
            f"🥩 *Kerakli go'sht:* **{meat_kg:.1f} kg** (Mol son lahm yoki Qo'y qobirg'asi)\n"
            f"🧈 *Dumba yog'i:* **{fat_g}g** dumba yog'i\n\n"
            f"💡 *Pishirish siri:* Go'shtni piyoz va mineral suv bilan 2 soat marinovka qilsangiz, sho'rva va shashlik juda yumshoq chiqadi.\n\n"
            f"🛒 *Baxmal Meat Do'konida Mavjud:* \n{prod_text}"
        )
    # Steik / Bifshteks
    elif any(w in prompt_lower for w in ['steik', 'steyk', 'steak', 'bifshteks']):
        n_persons = person_count or 2
        meat_kg = n_persons * 0.35
        return (
            f"🥩 *STEYK (STEAK) UCHUN TAVSIYA:*\n\n"
            f"👤 *Insonlar soni:* **{n_persons} kishi**\n"
            f"🥩 *Kerakli go'sht:* **{meat_kg:.1f} kg** (Mol antrekot, ribeye yoki lahm qismi)\n\n"
            f"💡 *Pishirish siri:* Tovada har bir tomonini 3-4 daqiqa sariyog' va rozmarin bilan qovursangiz, mazzasi a'lo bo'ladi.\n\n"
            f"🛒 *Baxmal Meat Do'konida Mavjud:* \n{prod_text}"
        )
    # Qozonkabob / Dimlama / Qovurma
    elif any(w in prompt_lower for w in ['qozon', 'dimlama', 'qovurma', 'jiz']):
        n_persons = person_count or 4
        meat_kg = n_persons * 0.3
        return (
            f"🍲 *QOZONKABOB VA DIMLAMA UCHUN TAVSIYA:*\n\n"
            f"👤 *Insonlar soni:* **{n_persons} kishi**\n"
            f"🥩 *Kerakli go'sht:* **{meat_kg:.1f} kg** (Mol biqin/qobirg'a va suyakli go'shtlar)\n\n"
            f"💡 *Pishirish siri:* Go'sht biroz yog'liroq va suyakli bo'lsa, qozonkabob o'ta sersharbat chiqadi.\n\n"
            f"🛒 *Baxmal Meat Do'konida Mavjud:* \n{prod_text}"
        )
    # Sho'rva / Manti / Somsa / Lag'mon
    elif any(w in prompt_lower for w in ['shorva', "sho'rva", 'manti', 'somsa', 'lagmon', "lag'mon"]):
        n_persons = person_count or 4
        meat_kg = n_persons * 0.25
        return (
            f"🍜 *SHO'RVA, MANTI VA SOMSA UCHUN TAVSIYA:*\n\n"
            f"👤 *Insonlar soni:* **{n_persons} kishi**\n"
            f"🥩 *Kerakli go'sht:* **{meat_kg:.1f} kg** (Mol ko'krak/qobirg'a va lahm go'sht)\n\n"
            f"🛒 *Baxmal Meat Do'konida Mavjud:* \n{prod_text}"
        )
    else:
        n_persons = person_count or 4
        meat_kg = n_persons * 0.25
        return (
            f"🥩 *BAXMAL MEAT — AI MASLAHATCHISI:*\n\n"
            f"👤 *Insonlar soni:* **{n_persons} kishi** uchun taxminiy go'sht me'yori: **{meat_kg:.1f} kg**\n\n"
            f"Siz so'ragan taom bo'yicha tavsiyamiz:\n"
            f"1. *Jarkop va Qozonkabob:* {n_persons} kishi uchun ~1.0 kg mol lahm/qobirg'a va 800g kartoshka.\n"
            f"2. *Osh va Palov:* 1 kg oshga 1.2 kg son lahm va 250g dumba tavsiya etiladi.\n"
            f"3. *Shashlik:* {n_persons} kishi uchun ~1.2 kg mol son lahm va dumba yog'i.\n\n"
            f"🛒 *Baxmal Meat Do'konidagi Joriy Narxlar va Zaxira:* \n{prod_text}"
        )


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


def main_menu_reply_keyboard(chat_id=None, is_registered=True):
    webapp_url = f"{SITE_URL}/pos/my-cabinet/"
    if chat_id:
        webapp_url += f"?chat_id={chat_id}"
    
    if not is_registered:
        return {
            'keyboard': [
                [{'text': "🚀 Onlayn Go'sht Do'koni (WebApp)", 'web_app': {'url': webapp_url}}],
                [{'text': '📱 Telefon raqamni ulash', 'request_contact': True}],
                [{'text': "🔍 Daftardan profilimni topish (AI/Smart)"}],
                [{'text': "🥩 AI Maslahatchisi"}, {'text': "🏪 Do'kon Haqida"}],
                [{'text': '💬 Admin bilan Aloqa'}]
            ],
            'resize_keyboard': True
        }

    return {
        'keyboard': [
            [{'text': "🚀 Onlayn Go'sht Do'koni (WebApp)", 'web_app': {'url': webapp_url}}],
            [{'text': "🛒 Go'sht Buyurtma Qilish"}, {'text': '📦 Buyurtmalarim'}],
            [{'text': "💳 Qarz To'lash / Chek Yuborish"}, {'text': '👤 Shaxsiy Kabinet'}],
            [{'text': '🧾 Xaridlar Tarixi'}, {'text': "🥩 AI Maslahatchisi"}],
            [{'text': '🏪 Do\'kon Haqida'}, {'text': '💬 Admin bilan Aloqa'}]
        ],
        'resize_keyboard': True
    }


def render_telegram_stepper_bar(status):
    if status == 'rejected':
        return "❌ ━━━━━━━━━━━━━━━━ RAD ETILDI"
    
    steps = [
        ('Qabul', status in ['pending', 'payment_uploaded', 'approved', 'preparing', 'shipping', 'completed']),
        ('Tasdiq', status in ['approved', 'preparing', 'shipping', 'completed']),
        ('Qadoq', status in ['preparing', 'shipping', 'completed']),
        ('Yetkazish', status in ['shipping', 'completed']),
        ('Tayyor', status == 'completed'),
    ]
    parts = []
    for name, active in steps:
        parts.append(f"{'🟢' if active else '⚪'} {name}")
    return " ➜ ".join(parts)


def location_reply_keyboard():
    """Lokatsiya va yetkazib berish turi tugmalari."""
    return {
        'keyboard': [
            [{'text': '📍 Manzilni (GPS) Yuborish', 'request_location': True}],
            [{'text': '🏃 Samovivoz (Do\'kondan olib ketish)'}],
            [{'text': '❌ Buyurtmani bekor qilish'}, {'text': '🏠 Asosiy Menyu'}]
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

# (Duplicate query_gemini_meat_assistant removed, main implementation is above)


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
        Q(custom_id__iexact=query) | Q(custom_id__icontains=query) |
        Q(note__icontains=query) | Q(note__icontains=q_latin) | Q(note__icontains=q_cyrillic)
    )

    if digits:
        filters |= Q(custom_id__iexact=digits) | Q(custom_id__iexact=f"M-{digits}") | Q(custom_id__icontains=digits)
        if len(digits) >= 3:
            filters |= Q(phone__icontains=digits)

    candidates = Customer.objects.filter(filters).order_by('-debt_amount', 'id').distinct()[:6]
    return list(candidates)


def get_customer_by_chat_id(chat_id):
    """Chat ID orqali mijozni olish."""
    return Customer.objects.filter(telegram_chat_id=str(chat_id)).first()


# ══════════════════════════════════════════════════════════
# CORE HANDLERS
# ══════════════════════════════════════════════════════════

def handle_customer_update(update):
    """Telegram Update-ni qayta ishlash."""

    # A. Inline Tugma Bosilganda (Callback Query)
    if 'callback_query' in update:
        cb = update['callback_query']
        chat_id = str(cb['from']['id'])
        data = cb.get('data', '')
        cb_id = cb['id']
        answer_callback(cb_id)

        customer = get_customer_by_chat_id(chat_id)

        if data.startswith('claim_profile_'):
            cust_id = int(data.replace('claim_profile_', ''))
            target_cust = Customer.objects.filter(id=cust_id).first()
            if target_cust:
                target_cust.telegram_chat_id = chat_id
                target_cust.save()
                debt_line = f"💰 *Joriy qarz:* `{target_cust.debt_amount:,.0f}` so'm\n" if target_cust.debt_amount > 0 else "✅ *Qarzingiz yo'q*\n"
                msg = (
                    f"🎉 *PROFIL MUVAFFAQIYATLI ULANDI!*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"Assalomu alaykum, hurmatli *{target_cust.first_name} {target_cust.last_name or ''}*!\n\n"
                    f"🆔 *Sizning ID:* `{target_cust.custom_id}`\n"
                    f"📞 *Telefon:* `{mask_phone(target_cust.phone)}`\n"
                    f"{debt_line}"
                    f"💎 *Bonus ballar:* `{target_cust.bonus_points}` ball\n\n"
                    f"Barcha imkoniyatlar siz uchun ochildi! 🥩"
                )
                try:
                    edit_message(chat_id, cb['message']['message_id'], msg)
                except:
                    pass
                send_message(chat_id, "Asosiy menyu:", reply_markup=main_menu_reply_keyboard(chat_id, is_registered=True))
            else:
                send_message(chat_id, "⚠️ Tanlangan profil topilmadi.")
            return

        elif data == 'create_new_guest_profile':
            from_user = cb.get('from', {})
            first_name = from_user.get('first_name') or 'Mijoz'
            last_name = from_user.get('last_name') or ''
            chat_suffix = chat_id[-6:] if len(chat_id) >= 6 else chat_id
            new_cust, _ = Customer.objects.get_or_create(
                telegram_chat_id=chat_id,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone': f"+998{chat_suffix.zfill(9)}",
                    'custom_id': f"M-{chat_suffix}"
                }
            )
            msg = (
                f"🎉 *YANGI PROFILINGIZ OCHILDI!*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Hurmatli *{new_cust.first_name}*, profilingiz (ID: `{new_cust.custom_id}`) muvaffaqiyatli ro'yxatdan o'tkazildi.\n\n"
                f"Xush kelibsiz! 🥩"
            )
            try:
                edit_message(chat_id, cb['message']['message_id'], msg)
            except:
                pass
            send_message(chat_id, "Asosiy menyu:", reply_markup=main_menu_reply_keyboard(chat_id, is_registered=True))
            return

        elif data == 'cancel_profile_search':
            USER_STATES.pop(chat_id, None)
            try:
                edit_message(chat_id, cb['message']['message_id'], "❌ Qidiruv bekor qilindi.")
            except:
                pass
            send_message(chat_id, "Asosiy menyu:", reply_markup=main_menu_reply_keyboard(chat_id, is_registered=False))
            return

        elif data == 'prompt_search_name':
            USER_STATES[chat_id] = {'action': 'awaiting_profile_search'}
            msg = (
                "🔍 *DAFTARDAN ISM/ID BO'YICHA QIDIRISH*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Iltimos, daftardagi ismingiz, familiyangiz yoki ID raqamingizni chatga yozib yuboring (masalan: `Asadbek` yoki `15`):"
            )
            try:
                edit_message(chat_id, cb['message']['message_id'], msg)
            except Exception:
                pass
        elif data == 'create_new_guest_profile':
            st = USER_STATES.pop(chat_id, None)
            phone_val = st.get('phone') if isinstance(st, dict) else None
            if not phone_val:
                phone_val = f"+998{chat_id[-9:]}" if len(chat_id) >= 9 else f"+99890{random.randint(1000000, 9999999)}"

            first_name = cb.get('from', {}).get('first_name') or 'Telegram Mijoz'
            last_name = cb.get('from', {}).get('last_name') or ''
            username = cb.get('from', {}).get('username') or ''

            custom_id = f"C-{random.randint(1000, 9999)}"
            while Customer.objects.filter(custom_id=custom_id).exists():
                custom_id = f"C-{random.randint(1000, 9999)}"

            welcome_bonus = 5
            new_cust = Customer.objects.create(
                first_name=first_name,
                last_name=last_name,
                phone=phone_val,
                telegram_chat_id=chat_id,
                custom_id=custom_id,
                bonus_points=welcome_bonus,
                note=f"🤖 Telegram bot orqali mustaqil ro'yxatdan o'tgan mijoz (@{username})".strip()
            )

            CustomerLog.objects.create(
                customer=new_cust,
                log_type='bonus',
                title="🎁 Xush kelibsiz bonusi!",
                amount=welcome_bonus,
                note=f"Baxmal Meat botidan muvaffaqiyatli ro'yxatdan o'tganingiz uchun {welcome_bonus} bonus balli sovg'a qilindi!"
            )

            # Notify Admin Telegram Bot
            try:
                from pos.views_api import send_telegram_notification
                send_telegram_notification(
                    f"🤖 *Yangi Mijoz Telegram Botdan Ro'yxatdan O'tdi!*\n\n"
                    f"👤 *F.I.O:* {new_cust.first_name} {new_cust.last_name or ''}\n"
                    f"📞 *Telefon:* `{new_cust.phone}`\n"
                    f"🆔 *Mijoz ID:* `{new_cust.custom_id}`\n"
                    f"⭐ *Start Bonus:* `{welcome_bonus}` ball\n"
                    f"💬 *Telegram:* @{username} (`{chat_id}`)"
                )
            except Exception:
                pass

            msg = (
                f"🎉 *TABRIKLAYMIZ!*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Hurmatli *{new_cust.first_name}*, siz uchun Baxmal Meat tizimida yangi shaxsiy hisob ochildi:\n\n"
                f"🆔 *Mijoz ID:* `{new_cust.custom_id}`\n"
                f"📞 *Telefon:* `{new_cust.phone}`\n"
                f"🎁 *Xush kelibsiz bonusi:* `{welcome_bonus}` bonus ball hisobingizga qo'shildi!\n\n"
                f"Endi do'konimizdan go'sht xarid qilganingizda ushbu ID yoki telefon raqamingizni aytsangiz kifoya."
            )
            try:
                edit_message(chat_id, cb['message']['message_id'], msg)
            except:
                send_message(chat_id, msg)

            send_message(chat_id, "Asosiy menyudan foydalanishingiz mumkin:", reply_markup=main_menu_reply_keyboard(chat_id, is_registered=True))
            return

        elif data.startswith('order_prod_'):
            prod_id = int(data.replace('order_prod_', ''))
            product = Product.objects.filter(id=prod_id).first()
            if product:
                USER_STATES[chat_id] = {'action': 'awaiting_weight', 'prod_id': product.id}
                msg = (
                    f"🥩 *{product.name}*\n"
                    f"💵 Narxi: `{product.price_per_kg:,.0f}` so'm/kg\n\n"
                    f"Iltimos, necha kg sotib olmoqchi bo'lsangiz vaznini yozib yuboring:\n"
                    f"✍️ *Misol:* `2` yoki `1.5` yoki `5`"
                )
                send_message(chat_id, msg)
            return

        elif data in ['pay_debt_now', 'upload_proof_now']:
            USER_STATES[chat_id] = 'awaiting_payment_proof'
            pay_details, qr_images = get_active_payment_settings_details()
            debt_sum = customer.debt_amount if customer else Decimal('0.00')
            debt_str = f"💰 *Sizning Joriy Qarzingiz:* `{debt_sum:,.0f}` so'm\n\n" if debt_sum > 0 else "✅ *Sizda qarz mavjud emas.*\n\n"

            msg = (
                "━━━━━━━━━━━━━━━━━━━━━━━\n"
                "💳 *QARZ TO'LASH VA REKVIZITLAR*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 *Mijoz:* {customer.first_name if customer else 'Mijoz'} ({customer.custom_id if customer else ''})\n"
                f"{debt_str}"
                "🏦 *Do'kon Karta Raqami:*\n"
                "`8600123456789012` *(ustiga 1 marta bossangiz nusxalanadi!)*\n"
                "Ega: *Baxmal Meat*\n\n"
                f"{pay_details}\n\n"
                "📸 *To'lovni amalga oshirgach, to'lov kvitansiyasi (skrinshot yoki foto)ni to'g'ridan-to'g'ri ushbu chatga yuboring!*\n\n"
                "📌 _Chek kelishi bilan admin tasdiqlaydi va qarzingiz avtomatik yopiladi._"
            )
            inline_kb = {
                'inline_keyboard': [
                    [{'text': "🌐 Sayt orqali to'lash (Click/Payme)", 'url': f"{SITE_URL}/pos/my-cabinet/"}]
                ]
            }
            send_message(chat_id, msg, reply_markup=inline_kb)
            for qr_title, qr_path in qr_images:
                send_customer_photo(chat_id, qr_path, caption=f"📲 *{qr_title} QR Kodi*")
            return

        elif data.startswith('cancel_order_'):
            order_id = int(data.replace('cancel_order_', ''))
            order = B2BOrder.objects.filter(id=order_id, status='pending').first()
            if order:
                order.status = 'rejected'
                order.save()
            USER_STATES.pop(chat_id, None)
            send_message(chat_id, "❌ *Buyurtma bekor qilindi.*", reply_markup=main_menu_reply_keyboard(chat_id, is_registered=bool(customer)))
            return

        return

    # B. Xabar Kelganda (Message)
    if 'message' in update:
        message = update['message']
        chat_id = str(message['chat']['id'])
        text = message.get('text', '').strip()
        contact = message.get('contact')
        location = message.get('location')
        photo = message.get('photo')
        web_app_data = message.get('web_app_data')

        customer = get_customer_by_chat_id(chat_id)
        from_user = message.get('from', {})
        tg_username = from_user.get('username')
        tg_first_name = from_user.get('first_name') or 'Mijoz'
        tg_last_name = from_user.get('last_name') or ''

        # Handle WebApp Order Submission Data
        if web_app_data:
            try:
                import json
                raw_payload = web_app_data.get('data', '{}')
                parsed_data = json.loads(raw_payload)
                order_id = parsed_data.get('order_id')
                total_sum = parsed_data.get('total_sum', 0)
                items_summary = parsed_data.get('items_text', 'Go\'sht mahsulotlari')
                delivery_type_txt = '🚚 Yetkazib berish (Dostavka)' if parsed_data.get('delivery_type') == 'delivery' else '🏪 Samovivoz'

                conf_msg = (
                    f"🎉 *BUYURTMANGIZ QABUL QILINDI!*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🆔 *Buyurtma ID:* `#{order_id}`\n"
                    f"🥩 *Tarkibi:* {items_summary}\n"
                    f"💰 *Jami summa:* `{total_sum:,.0f}` so'm\n"
                    f"📍 *Turi:* {delivery_type_txt}\n"
                    f"⏳ *Holati:* `Qadoqlanmoqda...`\n\n"
                    f"Tez orada operatorimiz siz bilan bog'lanadi! Rahmat!"
                )
                send_message(chat_id, conf_msg, reply_markup=main_menu_reply_keyboard(chat_id, is_registered=bool(customer)))
                return
            except Exception as w_err:
                print(f"[WebApp Data Handle Error]: {w_err}")

        # Handle explicit cancellation requests
        if text in ["❌ Buyurtmani bekor qilish", "❌ Bekor qilish", "bekor qilish"]:
            st = USER_STATES.pop(chat_id, None)
            if isinstance(st, dict) and st.get('order_id'):
                order = B2BOrder.objects.filter(id=st['order_id'], status='pending').first()
                if order:
                    order.status = 'rejected'
                    order.save()
                    send_message(chat_id, f"❌ *Buyurtma #{order.id} bekor qilindi.*", reply_markup=main_menu_reply_keyboard(chat_id, is_registered=bool(customer)))
                    return
            send_message(chat_id, "❌ *Jarayon bekor qilindi.*", reply_markup=main_menu_reply_keyboard(chat_id, is_registered=bool(customer)))
            return

        # 1. Kontakt yuborilganda (Avtorizatsiya / Real profil topish)
        if contact:
            phone_num = contact.get('phone_number', '').replace('+', '').strip()
            possible_phones = [phone_num, f"+{phone_num}", f"998{phone_num[-9:]}", f"+998{phone_num[-9:]}"]
            matched_customer = Customer.objects.filter(Q(phone__in=possible_phones) | Q(phone__icontains=phone_num[-9:])).first()

            if matched_customer:
                matched_customer.telegram_chat_id = chat_id
                matched_customer.save()
                debt_line = f"💰 *Joriy qarz:* `{matched_customer.debt_amount:,.0f}` so'm\n" if matched_customer.debt_amount > 0 else "✅ *Qarzingiz yo'q*\n"
                msg = (
                    f"✅ *Muvaffaqiyatli ulandiz!*\n\n"
                    f"Hurmatli *{matched_customer.first_name} {matched_customer.last_name or ''}*, profilingiz (ID: `{matched_customer.custom_id}`) Baxmal Meat botiga biriktirildi.\n\n"
                    f"{debt_line}"
                    f"💎 *Bonus ballar:* `{matched_customer.bonus_points}` ball"
                )
                send_message(chat_id, msg, reply_markup=main_menu_reply_keyboard(chat_id, is_registered=True))
            else:
                clean_phone = f"+998{phone_num[-9:]}" if len(phone_num) >= 9 else f"+{phone_num}"
                USER_STATES[chat_id] = {'action': 'awaiting_profile_search', 'phone': clean_phone}
                msg = (
                    f"⚠️ *Ushbu telefon raqam ({clean_phone}) bilan bog'liq mijoz daftarda topilmadi!*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"Daftardagi qarz va profilingizni topish uchun:\n"
                    f"✍️ **Daftardagi ismingiz, familiyangiz yoki ID raqamingizni** yozib yuboring (masalan: `Asadbek` yoki `15`).\n\n"
                    f"💡 _AI tizimimiz daftardagi yozuvlar orasidan profilingizni bir zumda topib beradi._"
                )
                inline_kb = {
                    'inline_keyboard': [
                        [{'text': "🔍 Daftardan ism/ID orqali qidirish", 'callback_data': 'prompt_search_name'}],
                        [{'text': "➕ Yangi mijoz sifatida ochish", 'callback_data': 'create_new_guest_profile'}]
                    ]
                }
                send_message(chat_id, msg, reply_markup=inline_kb)
            return

        # Handle '🏠 Asosiy Menyu' reset or /start
        if text == '🏠 Asosiy Menyu' or text == '/start':
            st = USER_STATES.pop(chat_id, None)
            if isinstance(st, dict) and st.get('order_id'):
                B2BOrder.objects.filter(id=st['order_id'], status='pending').update(status='rejected')
            
            webapp_url = f"{SITE_URL}/pos/my-cabinet/?chat_id={chat_id}"
            
            if customer:
                name = customer.first_name
                debt = customer.debt_amount
                score = customer.get_credit_score()
                debt_line = f"💰 Qarzingiz: `{debt:,.0f}` so'm" if debt > 0 else "✅ Qarzingiz yo'q"
                
                msg = (
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🏪 *BAXMAL MEAT — DO'KON BOTI*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"👋 Assalomu alaykum, *{name}*!\n\n"
                    f"📊 *Sizning ma'lumotlaringiz:*\n"
                    f"{debt_line}\n"
                    f"⭐ Ishonchlilik: *{score}*\n\n"
                    f"🛒 *Onlayn go'sht xarid qilish uchun pastdagi WebApp tugmasini bosing:* 👇\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"⏰ Ish vaqti: *07:00 — 20:00*\n"
                    f"📞 Tel: *+998 77 082 44 77*\n"
                    f"🌐 Sayt: baxmalmeat.uz"
                )
                send_message(chat_id, msg, reply_markup=main_menu_reply_keyboard(chat_id, is_registered=True))
            else:
                msg = (
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🏪 *BAXMAL MEAT — DO'KON BOTI*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"👋 Assalomu alaykum, *{tg_first_name}*!\n\n"
                    f"🥩 *Baxmal Meat* sifatli va halol go'sht mahsulotlari do'koniga xush kelibsiz!\n\n"
                    f"📋 *Profilingizni ulash uchun 2 ta qulay usul:*\n"
                    f"1️⃣ **📱 Telefon raqamni ulash** tugmasini bosing (Avtomatik ulanadi)\n"
                    f"2️⃣ **🔍 Daftardan profilimni topish** tugmasini bosing yoki ismingiz/ID raqamingizni yozib yuboring (AI orqali daftardagi qarzingiz va profilingiz topiladi)\n\n"
                    f"🛒 *Do'kon vitrinasi va buyurtma:* Pastdagi **🚀 Onlayn Go'sht Do'koni (WebApp)** orqali.\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"⏰ Ish vaqti: *07:00 — 20:00*\n"
                    f"📞 Tel: *+998 77 082 44 77*"
                )
                send_message(chat_id, msg, reply_markup=main_menu_reply_keyboard(chat_id, is_registered=False))
            return

        # Handle Profile Search Request Button
        if text in ['🔍 Daftardan profilimni topish (AI/Smart)', '🔍 Daftardan profilimni topish', '🔍 Daftardan qidirish (Ism/Izoh)', '🔍 Daftardan qidirish', '🔍 Qidirish']:
            USER_STATES[chat_id] = {'action': 'awaiting_profile_search'}
            msg = (
                "🔍 *DAFTARDAN PROFILINGIZNI TOPISH (AI / SMART QIDIRUV)*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Daftardagi yoki do'konda yozilgan ismingiz, familiyangiz, daftardagi ID raqamingiz yoki telefoningizni yozib yuboring:\n\n"
                "✍️ *Misol:* `Asadbek` yoki `15` yoki `Umarov` yoki `901234567`\n\n"
                "💡 _AI tizimimiz daftardagi barcha yozuvlar orasidan profilingizni bir zumda topib beradi._"
            )
            inline_cancel = {
                'inline_keyboard': [
                    [{'text': "❌ Bekor qilish", 'callback_data': 'cancel_profile_search'}]
                ]
            }
            send_message(chat_id, msg, reply_markup=inline_cancel)
            return

        # Check if awaiting profile search OR unregistered user typed search term (not a standard menu button)
        is_searching = (isinstance(USER_STATES.get(chat_id), dict) and USER_STATES[chat_id].get('action') == 'awaiting_profile_search')
        is_unreg_search = (not customer and text and not text.startswith('/') and text not in [
            '🏠 Asosiy Menyu', '🥩 AI Maslahatchisi', '🏪 Do\'kon Haqida', "🏪 Do'kon Haqida", '💬 Admin bilan Aloqa', '📱 Telefon raqamni ulash', "🚀 Onlayn Go'sht Do'koni (WebApp)"
        ])

        if is_searching or is_unreg_search:
            USER_STATES.pop(chat_id, None)
            candidates = find_customer_candidates(text)

            if candidates:
                msg_lines = [
                    "🔍 *DAFTARDAN TOPILGAN PROFILLAR:*",
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    f"So'rovingiz (*{text}*) bo'yicha quyidagi mijozlar topildi:\n"
                ]
                inline_keyboard = []
                for idx, cand in enumerate(candidates, 1):
                    full_name = f"{cand.first_name} {cand.last_name or ''}".strip()
                    phone_masked = mask_phone(cand.phone)
                    debt_val = f"{cand.debt_amount:,.0f} so'm" if cand.debt_amount > 0 else "0 so'm (Qarz yo'q)"

                    msg_lines.append(
                        f"*{idx}. 👤 {full_name}*\n"
                        f"   🆔 ID: `{cand.custom_id}`\n"
                        f"   📞 Tel: `{phone_masked}`\n"
                        f"   💰 Qarz balansi: *{debt_val}*\n"
                    )
                    inline_keyboard.append([
                        {'text': f"✅ Bu men: {cand.first_name} (ID: {cand.custom_id})", 'callback_data': f"claim_profile_{cand.id}"}
                    ])

                inline_keyboard.append([
                    {'text': "➕ Ro'yxatda yo'qman (Yangi ochish)", 'callback_data': 'create_new_guest_profile'}
                ])
                msg_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                msg_lines.append("👇 *O'zingizga tegishli profil ustiga bosing:*")

                send_message(chat_id, "\n".join(msg_lines), reply_markup={'inline_keyboard': inline_keyboard})
                return
            else:
                if is_searching:
                    msg = (
                        f"❌ *'{text}' bo'yicha daftardan mijoz topilmadi.*\n\n"
                        f"Iltimos, ism yoki ID raqamini to'g'ri kiritganingizni tekshirib qayta yozing yoki **📱 Telefon raqamni ulash** orqali yangi profil oching."
                    )
                    send_message(chat_id, msg, reply_markup=main_menu_reply_keyboard(chat_id, is_registered=False))
                    return

        # Handle weight input for product ordering
        if chat_id in USER_STATES and isinstance(USER_STATES[chat_id], dict) and USER_STATES[chat_id].get('action') == 'awaiting_weight':
            prod_id = USER_STATES[chat_id].get('prod_id')
            product = Product.objects.filter(id=prod_id).first()
            if product:
                try:
                    weight_val = Decimal(text.replace(',', '.'))
                    if weight_val <= 0:
                        raise ValueError()

                    order = B2BOrder.objects.create(
                        customer=customer,
                        product=product,
                        requested_weight=weight_val,
                        status='pending'
                    )

                    USER_STATES[chat_id] = {'action': 'awaiting_location', 'order_id': order.id}
                    total_price = weight_val * product.price_per_kg

                    msg = (
                        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"🛍 *BUYURTMA TAYYORLANDI!* (Buyurtma #{order.id})\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"🥩 *Mahsulot:* {product.name}\n"
                        f"⚖️ *Vazni:* `{weight_val}` kg\n"
                        f"💵 *Jami Summa:* `{total_price:,.0f}` so'm\n\n"
                        f"👇 *Endi yetkazib berish uchun pastdagi tugmalardan birini tanlang:*"
                    )
                    send_message(chat_id, msg, reply_markup=location_reply_keyboard())
                    return
                except:
                    send_message(chat_id, "⚠️ Iltimos, faqat raqam shaklida to'g'ri vazn kiriting (masalan: `2` yoki `1.5`):")
                    return

        # Handle pickup selection when awaiting_location
        if text in ["🏃 Samovivoz (Do'kondan olib ketish)", "🏃 Samovivoz"] and chat_id in USER_STATES and isinstance(USER_STATES[chat_id], dict) and USER_STATES[chat_id].get('action') == 'awaiting_location':
            order_id = USER_STATES[chat_id].get('order_id')
            try:
                order = B2BOrder.objects.get(id=order_id)
                order.delivery_type = 'pickup'
                order.delivery_address = "Do'kondan olib ketish (Samovivoz)"
                order.save()

                USER_STATES[chat_id] = {'action': 'awaiting_payment_proof', 'order_id': order.id}

                total_sum = order.requested_weight * order.product.price_per_kg
                pay_details, qr_images = get_active_payment_settings_details()

                msg = (
                    f"💳 *TO'LOVNI AMALGA OSHIRISH*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📦 *Mahsulot:* {order.product.name} ({order.requested_weight} kg)\n"
                    f"🏃 *Topshirish:* Do'kondan olib ketish (Samovivoz)\n"
                    f"💵 *Jami Summa:* `{total_sum:,.0f}` so'm\n\n"
                    f"{pay_details}\n\n"
                    f"📸 *To'lovni amalga oshirgach, to'lov cheki (kvitansiya/skrinshot) fotosini ushbu chatga yuboring!*"
                )
                inline_cancel = {
                    'inline_keyboard': [
                        [{'text': "❌ Buyurtmani Bekor Qilish", 'callback_data': f"cancel_order_{order.id}"}]
                    ]
                }
                send_message(chat_id, msg, reply_markup=inline_cancel)

                for qr_title, qr_path in qr_images:
                    send_customer_photo(chat_id, qr_path, caption=f"📲 *{qr_title} QR Kodi* — Telefon kamerasi orqali skaner qilib to'lang")
            except Exception as e:
                send_message(chat_id, f"⚠️ Xato: {e}")
            return

        # 3. Lokatsiya kelganda (Delivery address)
        if location and chat_id in USER_STATES and isinstance(USER_STATES[chat_id], dict) and USER_STATES[chat_id].get('action') == 'awaiting_location':
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
                inline_cancel = {
                    'inline_keyboard': [
                        [{'text': "❌ Buyurtmani Bekor Qilish", 'callback_data': f"cancel_order_{order.id}"}]
                    ]
                }
                send_message(chat_id, msg, reply_markup=inline_cancel)

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
                        deliv_addr_text = order.delivery_address if order.delivery_address else "Do'kondan olib ketish"

                        # Build Admin Notification Card with Inline Action Buttons
                        admin_caption = (
                            f"💳 *YANGI TO'LOV CHEKI VA BUYURTMA!* (Buyurtma #{order.id})\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"👤 *Mijoz:* {customer.first_name} {customer.last_name or ''}\n"
                            f"🆔 *ID:* `{customer.custom_id}` | 📞 `{customer.phone}`\n"
                            f"⭐ *Skoring:* {customer.get_credit_score()}\n\n"
                            f"🥩 *Mahsulot:* {order.product.name} ({order.requested_weight} kg)\n"
                            f"🚗 *Turi:* {order.get_delivery_type_display()}\n"
                            f"📍 *Manzil:* {deliv_addr_text}\n"
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
                    if customer.debt_amount <= 0:
                        send_message(chat_id, "ℹ️ Hurmatli mijoz, hozirda sizda to'lanmagan nasiya qarzi mavjud emas. Chek qabul qilinmadi.", reply_markup=main_menu_reply_keyboard())
                        return

                    proof = None
                    if saved_proof_path:
                        img_url_path = f"/media/{saved_proof_path}"
                        from .models import PaymentProof
                        proof_amount = customer.debt_amount
                        proof = PaymentProof.objects.create(
                            customer=customer,
                            image=saved_proof_path,
                            amount=proof_amount,
                            provider='karta',
                            note='Telegram chat orqali yuborilgan to\'lov cheki',
                            is_verified=False
                        )
                        CustomerLog.objects.create(
                            customer=customer,
                            log_type='debt_pay',
                            title="Mijoz xabari",
                            message=f"📸 To'lov cheki yuborildi ({proof_amount:,.0f} so'm)",
                            details={'image_url': img_url_path, 'source': 'telegram', 'proof_id': proof.id},
                            amount=proof_amount
                        )

                    try:
                        from .telegram_bot import send_payment_proof_photo
                        if proof:
                            send_payment_proof_photo(proof)
                        else:
                            admin_msg = (
                                f"💳 *Yangi To'lov Cheki Yuborildi!*\n\n"
                                f"👤 *Mijoz:* {customer.first_name} {customer.last_name or ''}\n"
                                f"🆔 *ID:* `{customer.custom_id}` | 📞 {customer.phone}\n"
                                f"📊 *Joriy qarz:* {customer.debt_amount:,} so'm"
                            )
                            send_admin_photo_notification(file_id, admin_msg)
                    except Exception as tg_adm_err:
                        print(f"[Admin notify error]: {tg_adm_err}")

                    send_message(chat_id, "✅ To'lov chekingiz adminga yuborildi! Tekshirilgach balansingiz yangilanadi.", reply_markup=main_menu_reply_keyboard())
                return

        # 5. Asosiy Menyu Buyruqlari
        if text == '🛒 Go\'sht Buyurtma Qilish':
            products = Product.objects.filter(is_active=True)
            if not products.exists():
                send_message(chat_id, "⚠️ Hozirda sotuvda mahsulotlar mavjud emas.")
                return

            msg_lines = [
                "━━━━━━━━━━━━━━━━━━━━━━━",
                "🥩 *BAXMAL MEAT — MAHSULOTLAR*",
                "━━━━━━━━━━━━━━━━━━━━━━━",
                ""
            ]
            inline_keyboard = []
            for p in products:
                stock_kg = getattr(p, 'stock_kg', 0) or 0
                stock_badge = f"🟢 {stock_kg:.0f} kg" if stock_kg > 0 else "🔴 Tugagan"
                msg_lines.append(
                    f"🥩 *{p.name}*\n"
                    f"   💵 Narxi: `{p.price_per_kg:,.0f}` so'm/kg\n"
                    f"   📦 Zaxira: {stock_badge}\n"
                )
                if stock_kg > 0:
                    inline_keyboard.append([
                        {'text': f"🛒 {p.name} — {p.price_per_kg:,.0f} so'm/kg", 'callback_data': f"order_prod_{p.id}"}
                    ])

            msg_lines.append("━━━━━━━━━━━━━━━━━━━━━━━")
            msg_lines.append("👇 *Buyurtma uchun mahsulotni tanlang:*")

            reply_markup = {'inline_keyboard': inline_keyboard}
            send_message(chat_id, "\n".join(msg_lines), reply_markup=reply_markup)

        elif text in ['📌 Buyurtma Statusi (Live)', '📦 Buyurtmalarim']:
            orders = B2BOrder.objects.filter(customer=customer).order_by('-created_at')[:5]
            if not orders.exists():
                send_message(chat_id, "━━━━━━━━━━━━━━━━━━━━━━━\n📦 *BUYURTMALARIM*\n━━━━━━━━━━━━━━━━━━━━━━━\n\nℹ️ Sizda hozircha buyurtmalar mavjud emas.\n\n💡 _Buyurtma berish uchun_ *'🛒 Go'sht Buyurtma Qilish'* _tugmasini bosing._", reply_markup=main_menu_reply_keyboard())
                return

            lines = [
                "━━━━━━━━━━━━━━━━━━━━━━━",
                "📦 *BUYURTMALARIM — JONLI TRACKING*",
                "━━━━━━━━━━━━━━━━━━━━━━━",
                ""
            ]
            for o in orders:
                status_info = {
                    'pending': ('⏳', 'Chek kutilmoqda'),
                    'payment_uploaded': ('📸', 'Chek tekshirilmoqda'),
                    'approved': ('✅', 'Admin tasdiqladi'),
                    'preparing': ('🥩', 'Qadoqlanmoqda'),
                    'shipping': ('🚚', 'Kuryer yo\'lda'),
                    'completed': ('🎉', 'Yetkazib berildi'),
                    'rejected': ('❌', 'Rad etildi')
                }.get(o.status, ('❔', o.get_status_display()))

                total_price = o.requested_weight * o.product.price_per_kg
                stepper_bar = render_telegram_stepper_bar(o.status)
                delivery_text = '🏃 Samovivoz' if o.delivery_type == 'pickup' else '🚗 Yetkazish'
                
                lines.append(
                    f"┌─── 📦 *Buyurtma #{o.id}* ───┐\n"
                    f"│ 🥩 {o.product.name} ({o.requested_weight} kg)\n"
                    f"│ 💵 Jami: `{total_price:,.0f}` so'm\n"
                    f"│ {delivery_text}\n"
                    f"│ {status_info[0]} *{status_info[1]}*\n"
                    f"│ {stepper_bar}\n"
                    f"│ 📅 {o.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                    f"└──────────────────────┘\n"
                )
            send_message(chat_id, "\n".join(lines), reply_markup=main_menu_reply_keyboard())

        elif text in ["💳 Qarz To'lash / Chek Yuborish", "💳 Qarz To'lash (Karta)", '💳 Karta va Rekvizitlar', '💳 Karta Rekviziti', "💳 Qarz To'lash"]:
            pay_details, qr_images = get_active_payment_settings_details()
            debt_sum = customer.debt_amount if customer else Decimal('0.00')
            debt_str = f"💰 *Sizning Joriy Qarzingiz:* `{debt_sum:,.0f}` so'm\n\n" if debt_sum > 0 else "💰 *Sizda hozircha qarz mavjud emas.*\n\n"

            msg = (
                "━━━━━━━━━━━━━━━━━━━━━━━\n"
                "💳 *QARZ TO'LASH VA KARTA REKVIZITLARI*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 *Mijoz:* {customer.first_name if customer else 'Mijoz'} ({customer.custom_id if customer else ''})\n"
                f"{debt_str}"
                "🏦 *Do'kon Plastik Karta Raqami:*\n"
                "`8600123456789012` *(ustiga 1 marta bossangiz nusxalanadi!)*\n"
                "Ega: *Baxmal Meat Enterprise*\n"
                "To'lov Turlari: *Click / Payme / Bank Ilovasi*\n\n"
                f"{pay_details}\n\n"
                "📸 *To'lovni amalga oshirgach, to'lov kvitansiyasi (skrinshot/foto)ni shu chatga yuboring!*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━"
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

        elif text in ['👤 Shaxsiy Kabinet & Qarz', '👤 Shaxsiy Kabinet (Balans)', '💰 Qarz va Kredit', '👤 Shaxsiy Kabinet']:
            smart_score = customer.calculate_smart_score()
            credit_score = customer.get_credit_score()
            
            # Loyalty level
            if smart_score >= 90:
                level = '👑 OLTIN Darajali Mijoz'
                level_emoji = '👑'
            elif smart_score >= 70:
                level = '💎 KUMUSH Darajali Mijoz'
                level_emoji = '💎'
            elif smart_score >= 50:
                level = '🥉 BRONZA Darajali Mijoz'
                level_emoji = '🥉'
            else:
                level = '🆕 Yangi Mijoz'
                level_emoji = '🆕'
            
            # Debt progress bar
            limit_used_pct = 0
            if customer.debt_limit > 0:
                limit_used_pct = min(100, int(customer.debt_amount / customer.debt_limit * 100))
            filled = limit_used_pct // 10
            bar = '▓' * filled + '░' * (10 - filled)
            
            score_color = '🟢' if smart_score >= 80 else ('🟡' if smart_score >= 50 else '🔴')
            
            barter_info = ""
            if hasattr(customer, 'supplier_profile') and customer.supplier_profile:
                sup_debt = customer.supplier_profile.our_debt
                barter_info = f"\n🚜 *Bizning sizdan qarzimiz:* `{sup_debt:,.0f}` so'm"
            
            msg = (
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{level_emoji} *SHAXSIY KABINET*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 *F.I.SH:* {customer.first_name} {customer.last_name or ''}\n"
                f"🆔 *Mijoz ID:* `{customer.custom_id}`\n"
                f"📞 *Telefon:* `{mask_phone(customer.phone)}`\n"
                f"🏅 *Daraja:* {level}\n\n"
                f"━━━━ 💰 *MOLIYAVIY MA'LUMOTLAR* ━━━━\n\n"
                f"💰 *Joriy Qarz:* `{customer.debt_amount:,.0f}` so'm\n"
                f"💳 *Kredit Limiti:* `{customer.debt_limit:,.0f}` so'm\n"
                f"📊 *Limitdan foydalanish:* `{limit_used_pct}%`\n"
                f"   `{bar}` {limit_used_pct}%\n\n"
                f"💎 *Bonus Ballar:* `{customer.bonus_points}` ball\n"
                f"{score_color} *Kredit Skoring:* *{credit_score}* ({smart_score}/100)\n"
                f"{barter_info}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{'⚠️ _Diqqat: Kredit limitingiz tugab qolmoqda!_' if limit_used_pct > 80 else '✅ _Kredit holatingiz yaxshi._'}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━"
            )
            inline_kb = {
                'inline_keyboard': [
                    [{'text': "💳 Qarzni Hozir To'lash", 'callback_data': 'pay_debt_now'}],
                    [{'text': '🌐 Veb-saytda Kabinetni Ochish', 'url': f"{SITE_URL}/pos/my-cabinet/"}]
                ]
            }
            send_message(chat_id, msg, reply_markup=inline_kb)

        elif text == '🥩 AI Go\'sht Maslahatchisi':
            USER_STATES[chat_id] = {'action': 'awaiting_ai_prompt'}
            msg = (
                "🤖 *Baxmal Meat — AI Maslahatchisi*\n\n"
                "Manga go'sht retseptlari, shashlik/qozonkabob/osh uchun necha kg go'sht va qaysi qism mos kelishi haqida istalgan savolingizni berishingiz mumkin:\n\n"
                "✍️ *Misol:* `10 kishi shashlik uchun necha kg go'sht kerak?` yoki `1kg oshga qaysi go'sht mos?`"
            )
            send_message(chat_id, msg)

        elif (isinstance(USER_STATES.get(chat_id), dict) and USER_STATES[chat_id].get('action') == 'awaiting_ai_prompt') or any(kw in text.lower() for kw in ['osh', 'palov', 'plov', 'kabob', 'shashlik', 'dimlama', 'qozon', 'shorva', "sho'rva", 'manti', 'somsa', 'lagmon', "lag'mon", 'jarkob', 'jarkop', 'jarkov', 'steik', 'steyk', 'retsept', 'maslahat', 'pishir', 'kishi']):
            if isinstance(USER_STATES.get(chat_id), dict):
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
            send_message(chat_id, "\n".join(text_lines), reply_markup=main_menu_reply_keyboard(chat_id, is_registered=True))

        elif text == '💬 Admin bilan Aloqa':
            USER_STATES[chat_id] = 'awaiting_support_msg'
            send_message(chat_id, "✍️ Adminga yubormoqchi bo'lgan savol yoki xabaringizni yozing:")

        elif USER_STATES.get(chat_id) == 'awaiting_support_msg':
            USER_STATES.pop(chat_id, None)
            if customer:
                CustomerLog.objects.create(
                    customer=customer,
                    log_type='bonus',
                    title="Mijoz xabari",
                    message=text,
                    details={'source': 'telegram'},
                    amount=Decimal('0.00')
                )
                cust_display = f"{customer.first_name} {customer.last_name or ''}".strip()
                cust_id_tag = f"({customer.custom_id})"
                phone_tag = customer.phone
            else:
                cust_display = f"{tg_first_name} {tg_last_name}".strip()
                cust_id_tag = "(Mehmon)"
                phone_tag = "Ulanmagan"

            tg_link = f"@{tg_username}" if tg_username else f"[{tg_first_name}](tg://user?id={chat_id})"

            admin_msg = (
                f"💬 *Mijozdan yangi xabar!*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 *Mijoz:* {cust_display} {cust_id_tag}\n"
                f"✈️ *Telegram:* {tg_link} (ID: `{chat_id}`)\n"
                f"📞 *Tel:* {phone_tag}\n\n"
                f"💬 *Xabar:* {text}"
            )
            send_admin_text_notification(admin_msg)
            send_message(chat_id, "✅ Xabaringiz adminga yetkazildi va saytdagi chatda ham ko'rinadi. Tez orada javob beramiz!", reply_markup=main_menu_reply_keyboard(chat_id, is_registered=bool(customer)))

        elif text == '🏪 Do\'kon Haqida':
            msg = (
                "━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🏪 *BAXMAL MEAT — DO'KON MA'LUMOTLARI*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🥩 *Baxmal Meat* — yangi, sifatli va 100% halol\n"
                "go'sht mahsulotlari do'koni.\n\n"
                "━━━━ 📋 *ASOSIY MA'LUMOTLAR* ━━━━\n\n"
                "⏰ *Ish vaqti:* Har kuni 07:00 — 20:00\n"
                "📞 *Telefon:* +998 77 082 44 77\n"
                "🌐 *Veb-sayt:* baxmalmeat.uz\n"
                "📍 *Manzil:* Jizzax viloyati Baxmal tumani Sangzor MFY Guzari\n\n"
                "━━━━ 🥩 *MAHSULOT VA XIZMATLAR* ━━━━\n\n"
                "✅ Yangi so'yilgan sifatli mol go'shti\n"
                "✅ Yangi so'yilgan qo'y go'shti\n"
                "✅ Yetkazib berish xizmati (Delivery)\n"
                "✅ Nasiya (kredit) daftari xizmati\n"
                "✅ 24/7 AI Go'sht Maslahatchisi\n\n"
                "━━━━ 🏆 *AFZALLIKLARIMIZ* ━━━━\n\n"
                "🔬 Veterinar nazorati ostida (Halol)\n"
                "❄️ Sovuq zanjir (Cold Chain) saqlash\n"
                "📱 24/7 Telegram Bot & Shaxsiy Kabinet\n"
                "💳 Naqd va Karta orqali to'lov (Click/Payme/Terminal)\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n"
                "_Biz bilan doimo toza, halol va sifatli go'sht!_ 🥩"
            )
            inline_kb = {
                'inline_keyboard': [
                    [{'text': '🌐 Veb-saytni Ochish', 'url': f"{SITE_URL}"}],
                    [{'text': '📍 Do\'kon Lokatsiyasi (Xarita)', 'url': 'https://maps.google.com/?q=Sangzor+Baxmal+Meat'}]
                ]
            }
            send_message(chat_id, msg, reply_markup=inline_kb)

        elif text == "🌐 Veb-saytga O'tish":
            cabinet_url = f"{SITE_URL}/pos/my-cabinet/?chat_id={chat_id}"
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

        elif text:
            # Fallback for ANY normal text message sent by customer (e.g. "Salom", inquiries)
            if customer:
                CustomerLog.objects.create(
                    customer=customer,
                    log_type='bonus',
                    title="Mijoz xabari",
                    message=text,
                    details={'source': 'telegram'},
                    amount=Decimal('0.00')
                )
                cust_display = f"{customer.first_name} {customer.last_name or ''}".strip()
                cust_id_tag = f"({customer.custom_id})"
                phone_tag = customer.phone
            else:
                cust_display = f"{tg_first_name} {tg_last_name}".strip()
                cust_id_tag = "(Mehmon)"
                phone_tag = "Ulanmagan"

            tg_link = f"@{tg_username}" if tg_username else f"[{tg_first_name}](tg://user?id={chat_id})"

            admin_msg = (
                f"💬 *Mijozdan yangi xabar!*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 *Mijoz:* {cust_display} {cust_id_tag}\n"
                f"✈️ *Telegram:* {tg_link} (ID: `{chat_id}`)\n"
                f"📞 *Tel:* {phone_tag}\n\n"
                f"💬 *Xabar:* {text}"
            )
            send_admin_text_notification(admin_msg)
            send_message(
                chat_id,
                "✅ *Xabaringiz adminga yetkazildi.*\nTez orada siz bilan bog'lanamiz yoki javob beramiz!",
                reply_markup=main_menu_reply_keyboard(chat_id, is_registered=bool(customer))
            )

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

        # Admin status update callback handlers
        elif data.startswith('adm_app_'):
            order_id = int(data.replace('adm_app_', ''))
            try:
                order = B2BOrder.objects.get(id=order_id)
                order.status = 'approved'
                order.save()
                answer_callback(cq_id, text="✅ Buyurtma tasdiqlandi!")
                edit_message(chat_id, cq['message']['message_id'], f"✅ Buyurtma #{order.id} tasdiqlandi va tayyorlanishga o'tdi!")
                from .telegram_bot import notify_customer_order_status
                notify_customer_order_status(order)
            except Exception as e:
                answer_callback(cq_id, text=f"Xatolik: {e}")

        elif data.startswith('adm_prep_'):
            order_id = int(data.replace('adm_prep_', ''))
            try:
                order = B2BOrder.objects.get(id=order_id)
                order.status = 'preparing'
                order.save()
                answer_callback(cq_id, text="🥩 Qadoqlashga berildi!")
                edit_message(chat_id, cq['message']['message_id'], f"🥩 Buyurtma #{order.id} qadoqlanmoqda!")
                from .telegram_bot import notify_customer_order_status
                notify_customer_order_status(order)
            except Exception as e:
                answer_callback(cq_id, text=f"Xatolik: {e}")

        elif data.startswith('adm_ship_'):
            order_id = int(data.replace('adm_ship_', ''))
            try:
                order = B2BOrder.objects.get(id=order_id)
                order.status = 'shipping'
                order.save()
                answer_callback(cq_id, text="🚚 Kuryer yo'lda!")
                edit_message(chat_id, cq['message']['message_id'], f"🚚 Buyurtma #{order.id} kuryer yo'lda!")
                from .telegram_bot import notify_customer_order_status
                notify_customer_order_status(order)
            except Exception as e:
                answer_callback(cq_id, text=f"Xatolik: {e}")

        elif data.startswith('adm_rej_'):
            order_id = int(data.replace('adm_rej_', ''))
            try:
                order = B2BOrder.objects.get(id=order_id)
                order.status = 'rejected'
                order.save()
                answer_callback(cq_id, text="❌ Buyurtma rad etildi!")
                edit_message(chat_id, cq['message']['message_id'], f"❌ Buyurtma #{order.id} rad etildi!")
                from .telegram_bot import notify_customer_order_status
                notify_customer_order_status(order)
            except Exception as e:
                answer_callback(cq_id, text=f"Xatolik: {e}")
