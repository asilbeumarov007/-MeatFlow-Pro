import requests
import json
import re
from django.conf import settings

def clean_phone_number(phone):
    """Telefon raqamini 998901234567 formatiga o'tkazish."""
    if not phone:
        return ""
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) == 9:
        return "998" + digits
    if len(digits) == 12 and digits.startswith('998'):
        return digits
    return digits

def send_via_eskiz(phone, message):
    """Eskiz.uz API bearer token login va SMS yuborish."""
    direct_token = getattr(settings, 'ESKIZ_TOKEN', getattr(settings, 'SMS_API_TOKEN', ''))
    login = getattr(settings, 'SMS_API_LOGIN', getattr(settings, 'ESKIZ_EMAIL', ''))
    password = getattr(settings, 'SMS_API_PASSWORD', getattr(settings, 'ESKIZ_PASSWORD', ''))

    token = direct_token
    if not token and login and password:
        try:
            auth_url = "https://notify.eskiz.uz/api/auth/login"
            payload = {'email': login, 'password': password}
            r_auth = requests.post(auth_url, data=payload, timeout=6)
            if r_auth.status_code == 200:
                token_data = r_auth.json()
                token = token_data.get('data', {}).get('token')
            else:
                print(f"[Eskiz Auth Fail HTTP {r_auth.status_code}]: {r_auth.text}")
                return {'status': 'error', 'message': f"Eskiz login xatosi: Parol yoki Email noto'g'ri (HTTP {r_auth.status_code})"}
        except Exception as e:
            print(f"[Eskiz Auth Exception]: {e}")
            return {'status': 'error', 'message': str(e)}

    if not token:
        return {'status': 'error', 'message': "Eskiz tokenini olib bo'lmadi! Login yoki parol xato."}

    try:
        send_url = "https://notify.eskiz.uz/api/message/sms/send"
        headers = {'Authorization': f'Bearer {token}'}
        send_payload = {
            'mobile_phone': phone,
            'message': message,
            'from': '4546'
        }
        r_send = requests.post(send_url, data=send_payload, headers=headers, timeout=8)
        if r_send.status_code == 200:
            res_json = r_send.json()
            return {
                'status': 'success',
                'message': f"Eskiz.uz orqali SMS yuborildi (+{phone})",
                'data': res_json
            }
        else:
            print(f"[Eskiz Send Fail HTTP {r_send.status_code}]: {r_send.text}")
            return {'status': 'error', 'message': f"Eskiz SMS yuborishda xatolik: {r_send.text}"}
    except Exception as e:
        print(f"[Eskiz Exception]: {e}")
        return {'status': 'error', 'message': str(e)}

def send_via_sms_uz(phone, message):
    login = getattr(settings, 'SMS_API_LOGIN', '')
    password = getattr(settings, 'SMS_API_PASSWORD', '')
    if not login or not password:
        return None
    try:
        url = "https://notify.sms.uz/api/send"
        payload = {'login': login, 'password': password, 'phone': phone, 'text': message}
        r = requests.post(url, data=payload, timeout=6)
        if r.status_code == 200:
            return {'status': 'success', 'message': f"SMS.uz orqali yuborildi (+{phone})", 'data': r.text}
    except Exception as e:
        print(f"[SMS.uz Error]: {e}")
    return None

def send_via_playmobile(phone, message):
    login = getattr(settings, 'SMS_API_LOGIN', '')
    password = getattr(settings, 'SMS_API_PASSWORD', '')
    originator = getattr(settings, 'SMS_ORIGINATOR', '3700')
    if not login or not password:
        return None
    try:
        url = "https://send.playmobile.uz/send"
        payload = {
            "messages": [{
                "recipient": phone,
                "message-id": "bm_" + str(phone)[-6:],
                "sms": {"originator": originator, "content": {"text": message}}
            }]
        }
        r = requests.post(url, json=payload, auth=(login, password), timeout=6)
        if r.status_code == 200:
            return {'status': 'success', 'message': f"PlayMobile.uz orqali yuborildi (+{phone})", 'data': r.json()}
    except Exception as e:
        print(f"[PlayMobile Error]: {e}")
    return None

def send_sms(phone, message):
    """Ko'p provayderli universal SMS yuborish mexanizmi."""
    clean_phone = clean_phone_number(phone)
    if not clean_phone or len(clean_phone) != 12:
        return {'status': 'error', 'message': "Yaroqsiz telefon raqami!"}

    provider = getattr(settings, 'SMS_PROVIDER', 'eskiz')

    if provider == 'eskiz':
        res = send_via_eskiz(clean_phone, message)
        if res: return res

    elif provider == 'sms_uz':
        res = send_via_sms_uz(clean_phone, message)
        if res: return res

    elif provider == 'playmobile':
        res = send_via_playmobile(clean_phone, message)
        if res: return res

    # Simulyatsiya fallback
    print(f"[SMS SIMULATION - Provider: {provider}] To: +{clean_phone} | Text: {message}")
    return {
        'status': 'success',
        'simulated': True,
        'message': f"SMS simulyatsiya qilindi (+{clean_phone}): '{message[:35]}...'"
    }

def send_sale_sms(customer_name, phone, total_amount, debt_amount=0):
    t_fmt = "{:,.0f}".format(total_amount).replace(',', ' ')
    msg = f"Baxmal Meat: Rahmat! Xaridingiz {t_fmt} so'm."
    if debt_amount > 0:
        d_fmt = "{:,.0f}".format(debt_amount).replace(',', ' ')
        msg += f" Joriy qarz: {d_fmt} so'm."
    msg += " Tel: +998770824477"
    return send_sms(phone, msg)

def send_debt_reminder_sms(customer_name, phone, debt_amount):
    d_fmt = "{:,.0f}".format(debt_amount).replace(',', ' ')
    msg = f"Baxmal Meat: Hurmatli {customer_name}, do'konimizdan nasiya qarz balansingiz {d_fmt} so'm. To'lov karta: 8600123456789012. Rahmat!"
    return send_sms(phone, msg)
