"""
Django Management Command: run_customer_bot
=============================================
Foydalanuvchilar (Mijozlar) Telegram botini doimiy eshitib turish (Long Polling).
"""
import time
import requests
from django.core.management.base import BaseCommand
from pos.customer_bot import CUSTOMER_BOT_TOKEN, handle_customer_update

class Command(BaseCommand):
    help = 'Runs the Customer Telegram Bot via long polling'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=================================================="))
        self.stdout.write(self.style.SUCCESS("    BAXMAL MEAT: FOYDALANUVCHILAR BOTI v1.0       "))
        self.stdout.write(self.style.SUCCESS("=================================================="))
        self.stdout.write(f"Bot Token: {CUSTOMER_BOT_TOKEN[:10]}...")
        self.stdout.write("Telegramdan yangi xabarlarni kutmoqdaman...\n")

        offset = 0
        url = f"https://api.telegram.org/bot{CUSTOMER_BOT_TOKEN}/getUpdates"

        while True:
            try:
                params = {'timeout': 20, 'offset': offset}
                response = requests.get(url, params=params, timeout=25)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('ok'):
                        for update in data.get('result', []):
                            offset = update['update_id'] + 1
                            try:
                                handle_customer_update(update)
                            except Exception as e:
                                self.stdout.write(self.style.ERROR(f"Update handler error: {e}"))
                elif response.status_code == 409:
                    self.stdout.write(self.style.WARNING("Boshqa jarayon botni eshitmoqda (Conflict). 5 soniya kutilmoqda..."))
                    time.sleep(5)
                else:
                    self.stdout.write(self.style.WARNING(f"Telegram API response: {response.status_code}"))
                    time.sleep(2)

            except KeyboardInterrupt:
                self.stdout.write(self.style.SUCCESS("\nBot to'xtatildi."))
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Polling error: {e}"))
                time.sleep(2)
