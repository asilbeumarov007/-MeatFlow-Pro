from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
import requests
import os
from pos.models import Customer, PaymentSetting

class Command(BaseCommand):
    help = "Qarzi bor va Telegram boti bog'langan mijozlarga avtomatik qarz eslatmalarini yuborish"

    def handle(self, *args, **options):
        debtor_customers = Customer.objects.filter(
            debt_amount__gt=0,
            telegram_chat_id__isnull=False
        ).exclude(telegram_chat_id='')

        self.stdout.write(self.style.SUCCESS(f"Tizimda {debtor_customers.count()} ta Telegram bog'langan qarzdor mijozlar topildi."))

        bot_token = os.environ.get('CUSTOMER_BOT_TOKEN', '7847391919:AAEEk2dO6XzQ-1sX_w-W4b-6P4k8L-9w0yM')
        
        # Payment Card Details
        pay_setting = PaymentSetting.objects.filter(is_active=True).first()
        card_info = "💳 *To'lov Rekviziti (Karta):* `8600 1234 5678 9012` (Baxmal Meat)\n"
        if pay_setting and pay_setting.card_number:
            card_info = f"💳 *To'lov Rekviziti:* `{pay_setting.card_number}` ({pay_setting.card_holder or 'Baxmal Meat'})\n"

        sent_count = 0
        for customer in debtor_customers:
            try:
                debt_str = f"{customer.debt_amount:,.0f}".replace(',', ' ')
                msg = (
                    f"⚠️ *HURMATLI {customer.first_name.upper()}!*\n\n"
                    f"Sizning *Baxmal Meat Pro* tizimida *{debt_str} so'm* muddati kelgan qarzingiz mavjud.\n\n"
                    f"{card_info}"
                    f"To'lovni amalga oshirgach, chek fotosini ushbu botga yuklashingizni so'raymiz.\n\n"
                    f"Rahmat! 🤝"
                )

                payload = {
                    'chat_id': customer.telegram_chat_id,
                    'text': msg,
                    'parse_mode': 'Markdown',
                    'reply_markup': {
                        'inline_keyboard': [
                            [{'text': "📸 Hozir To'lov Chekini Yuborish", 'callback_data': "pay_debt_now"}]
                        ]
                    }
                }

                r = requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json=payload, timeout=5)
                if r.status_code == 200:
                    sent_count += 1
                    self.stdout.write(f" - {customer.first_name} (ID: {customer.custom_id}): Eslatma yuborildi.")
                else:
                    self.stdout.write(self.style.WARNING(f" - {customer.first_name}: Xatolik {r.status_code}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f" - {customer.first_name}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Jami {sent_count} ta mijozga qarz eslatmasi muvaffaqiyatli yuborildi!"))
