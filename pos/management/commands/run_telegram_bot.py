"""
Baxmal Meat Kassa — Telegram Bot Long-Polling Management Command
================================================================
Ishga tushirish: python manage.py run_telegram_bot

Bu buyruq Telegram API'dan long-polling usulida yangi xabarlarni kutib,
kelgan buyruq va tugma bosilishlarini pos.telegram_bot moduliga yo'naltiradi.
"""
import time
import requests
from django.core.management.base import BaseCommand
from pos.telegram_bot import (
    API_URL, dispatch_command, dispatch_callback
)


class Command(BaseCommand):
    help = 'Baxmal Meat Telegram botni ishga tushirish (long-polling)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Long-polling timeout (soniyalarda), default: 30'
        )

    def handle(self, *args, **options):
        timeout = options['timeout']
        offset = 0

        # Eski kutilayotgan xabarlarni tozalash (faqat judayam ko'p tiqilib qolgandagina)
        try:
            flush = requests.get(f"{API_URL}/getUpdates", params={'limit': 100}, timeout=10)
            if flush.status_code == 200:
                results = flush.json().get('result', [])
                if len(results) > 15:
                    # Oxirgi 3 tasini olib qolib, qolganini o'tkazib yuboramiz
                    offset = results[-3]['update_id']
                    self.stdout.write(f"[INFO] {len(results) - 3} ta eski xabar o'tkazib yuborildi.")
        except Exception as e:
            self.stdout.write(f"[INFO] Startup checkda xatolik: {e}")

        self.stdout.write(self.style.SUCCESS(
            "\n===== BAXMAL MEAT TELEGRAM BOT ISHGA TUSHDI =====\n"
            f"Long-polling timeout: {timeout}s\n"
            "Buyruqlarni kutmoqda...\n"
        ))

        while True:
            try:
                url = f"{API_URL}/getUpdates"
                params = {
                    'offset': offset,
                    'timeout': timeout,
                    'allowed_updates': ['message', 'callback_query'],
                }
                resp = requests.get(url, params=params, timeout=timeout + 10)

                if resp.status_code != 200:
                    self.stderr.write(f"[XATO] Telegram API xatosi: {resp.status_code}")
                    time.sleep(5)
                    continue

                data = resp.json()
                if not data.get('ok'):
                    self.stderr.write(f"[XATO] Telegram javobi: {data}")
                    time.sleep(5)
                    continue

                results = data.get('result', [])

                for update in results:
                    offset = update['update_id'] + 1

                    # Oddiy matn buyruqlari
                    if 'message' in update:
                        msg = update['message']
                        chat_id = msg['chat']['id']
                        text = msg.get('text', '')

                        if text:
                            sender = msg.get('from', {}).get('first_name', 'Nomalum')
                            self.stdout.write(
                                f"[BUYRUQ] {sender}: {text} (chat: {chat_id})"
                            )
                            try:
                                dispatch_command(chat_id, text)
                            except Exception as e:
                                self.stderr.write(f"[XATO] Buyruqni bajarishda: {e}")
                                from pos.telegram_bot import send_message
                                send_message(chat_id, f"❌ Xatolik yuz berdi:\n`{str(e)[:200]}`")

                    # Inline tugma callback'lari
                    elif 'callback_query' in update:
                        cq = update['callback_query']
                        chat_id = cq['message']['chat']['id']
                        message_id = cq['message']['message_id']
                        callback_data = cq.get('data', '')
                        callback_query_id = cq['id']

                        sender = cq.get('from', {}).get('first_name', 'Nomalum')
                        self.stdout.write(
                            f"[TUGMA] {sender}: {callback_data} (chat: {chat_id})"
                        )
                        try:
                            dispatch_callback(chat_id, message_id, callback_data, callback_query_id)
                        except Exception as e:
                            self.stderr.write(f"[XATO] Callback bajarishda: {e}")
                            from pos.telegram_bot import answer_callback, send_message
                            answer_callback(callback_query_id, f"Xatolik: {str(e)[:100]}")

            except requests.exceptions.Timeout:
                # Long-polling timeout — bu normal holat
                continue
            except requests.exceptions.ConnectionError:
                self.stderr.write("[XATO] Internet aloqasi uzildi. 10 soniyadan keyin qayta urinish...")
                time.sleep(10)
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING("\n\n🛑 Bot to'xtatildi. Xayr!"))
                break
            except Exception as e:
                self.stderr.write(f"[XATO] Kutilmagan xato: {e}")
                time.sleep(5)
