import logging
from django.utils import timezone
from decimal import Decimal
from .models import Customer, CustomerLog
from .sms_service import send_via_eskiz, clean_phone_number

logger = logging.getLogger(__name__)

def generate_default_reminder_message(customer):
    """Xushmuomala, professional qarz eslatmasi matnini shakllantirish."""
    debt_str = f"{abs(customer.debt_amount):,.0f}".replace(",", " ")
    first_name = customer.first_name.strip() if customer.first_name else "Mijoz"
    
    return (
        f"Assalomu alaykum, hurmatli {first_name}! 'Baxmal Meat' do'konimizdan olgan go'sht mahsulotlari "
        f"uchun tashakkur. Sizning joriy nasiya qoldig'ingiz: {debt_str} so'm. "
        f"O'zingizga qulay vaqtda hisob-kitob qilishingizni iltimos qilamiz. "
        f"Murojaat uchun: +998933057375. Ishlaringizga baraka!"
    )

def send_debt_reminder(customer, custom_text=None, channel='auto', sent_by=None):
    """
    Qarzdor mijozga SMS yoki Telegram orqali eslatma yuborish.
    channel: 'auto' (agar TG bo'lsa TG, aks holda SMS), 'telegram', 'sms', 'both'
    """
    if customer.debt_amount <= Decimal('0.00'):
        return {
            'success': False,
            'message': f"{customer.first_name}da qarz mavjud emas (balans: {customer.debt_amount} so'm)."
        }

    message_text = custom_text.strip() if custom_text and custom_text.strip() else generate_default_reminder_message(customer)
    results = []
    effective_channel = channel

    # Resolve 'auto'
    if channel == 'auto':
        if customer.telegram_chat_id:
            effective_channel = 'telegram'
        else:
            effective_channel = 'sms'

    # 1. Telegram orqali yuborish
    if effective_channel in ('telegram', 'both'):
        if customer.telegram_chat_id:
            try:
                from .customer_bot import send_message as send_cust_msg
                tg_text = (
                    f"🔔 *QARZ ESLATMASI — BAXMAL MEAT*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"{message_text}\n\n"
                    f"💳 *To'lov qilish uchun:* Ilovamizdagi to'lov bo'limidan yoki to'g'ridan-to'g'ri do'konimizga murojaat qilishingiz mumkin."
                )
                tg_res = send_cust_msg(customer.telegram_chat_id, tg_text)
                results.append(('telegram', True, "Telegram orqali yuborildi"))
            except Exception as e:
                logger.error(f"Telegram reminder error: {e}")
                results.append(('telegram', False, f"Telegram xatosi: {e}"))
                if channel == 'auto':
                    # Fallback to SMS if TG fails
                    effective_channel = 'sms'
        else:
            if channel == 'telegram':
                return {
                    'success': False,
                    'message': f"{customer.first_name}da Telegram ulanmagan! SMS orqali yuborishni tanlang."
                }
            effective_channel = 'sms'

    # 2. SMS orqali yuborish (Eskiz.uz)
    if effective_channel in ('sms', 'both'):
        phone = clean_phone_number(customer.phone)
        if not phone:
            results.append(('sms', False, "Telefon raqami noto'g'ri yoki mavjud emas"))
        else:
            sms_res = send_via_eskiz(phone, message_text)
            if sms_res.get('status') == 'success':
                results.append(('sms', True, f"Eskiz.uz SMS yuborildi (+{phone})"))
            else:
                results.append(('sms', False, sms_res.get('message', 'SMS yuborishda nomaʼlum xatolik')))

    # Xulosa qilish
    success_count = sum(1 for r in results if r[1])
    if success_count > 0:
        # Audit va mijoz profilini yangilash
        now = timezone.now()
        customer.last_reminder_sent_at = now
        customer.reminder_count = (customer.reminder_count or 0) + 1
        customer.save(update_fields=['last_reminder_sent_at', 'reminder_count'])

        # CustomerLog ga qayd etish
        channel_names = ", ".join([r[0].upper() for r in results if r[1]])
        CustomerLog.objects.create(
            customer=customer,
            log_type='reminder',
            title=f"Qarz eslatmasi ({channel_names})",
            message=message_text,
            details={
                'channel': channel,
                'effective_channels': [r[0] for r in results if r[1]],
                'sent_by': getattr(sent_by, 'username', 'system') if sent_by else 'system',
                'results': results
            },
            amount=customer.debt_amount
        )

        return {
            'success': True,
            'message': f"Eslatma muvaffaqiyatli yuborildi! ({channel_names})",
            'channel': channel_names,
            'sent_at': now.strftime('%d.%m.%Y %H:%M'),
            'reminder_count': customer.reminder_count,
            'details': results
        }
    else:
        err_msg = "; ".join([f"{r[0]}: {r[2]}" for r in results])
        return {
            'success': False,
            'message': f"Xabarni yetkazib bo'lmadi: {err_msg}",
            'details': results
        }
