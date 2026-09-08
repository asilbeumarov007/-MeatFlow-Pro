import sys
import time
import threading
import requests
from django.core.management.base import BaseCommand
from pos.telegram_bot import (
    API_URL as ADMIN_API_URL, dispatch_command as admin_dispatch_command,
    dispatch_callback as admin_dispatch_callback, dispatch_voice_message
)
from pos.customer_bot import CUSTOMER_BOT_TOKEN, handle_customer_update

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def safe_print(msg):
    try:
        sys.stdout.write(msg + '\n')
        sys.stdout.flush()
    except Exception:
        try:
            sys.stdout.write(msg.encode('ascii', errors='ignore').decode('ascii') + '\n')
            sys.stdout.flush()
        except Exception:
            pass


def run_admin_bot_loop():
    """Admin / Kassa Boti uchun Long-Polling sikli."""
    offset = 0
    safe_print("[ADMIN BOT] Ishga tushmoqda...")
    while True:
        try:
            url = f"{ADMIN_API_URL}/getUpdates"
            params = {
                'offset': offset,
                'timeout': 20,
                'allowed_updates': ['message', 'callback_query'],
            }
            resp = requests.get(url, params=params, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('ok'):
                    for update in data.get('result', []):
                        offset = update['update_id'] + 1
                        try:
                            if 'message' in update:
                                msg = update['message']
                                chat_id = msg['chat']['id']
                                
                                if 'voice' in msg:
                                    voice_id = msg['voice']['file_id']
                                    safe_print(f"[ADMIN BOT] 🎙️ Ovozli xabar qabul qilindi ({chat_id})")
                                    dispatch_voice_message(chat_id, voice_id)
                                elif 'audio' in msg:
                                    audio_id = msg['audio']['file_id']
                                    safe_print(f"[ADMIN BOT] 🎵 Audio xabar qabul qilindi ({chat_id})")
                                    dispatch_voice_message(chat_id, audio_id)
                                else:
                                    text = msg.get('text', '')
                                    safe_print(f"[ADMIN BOT] Xabar ({chat_id}): {text}")

                                    # Check if admin is replying to a customer notification message
                                    reply_to = msg.get('reply_to_message')
                                    if reply_to and (reply_to.get('text') or reply_to.get('caption')):
                                        import re
                                        from decimal import Decimal
                                        from pos.models import Customer, CustomerLog
                                        from pos.customer_bot import send_message as send_customer_msg
                                        from pos.telegram_bot import send_message as send_admin_msg
                                        
                                        orig_text = reply_to.get('text') or reply_to.get('caption') or ''
                                        chat_id_match = (
                                            re.search(r'ID:\s*`?(\d+)`?', orig_text) or
                                            re.search(r'user\?id=(\d+)', orig_text)
                                        )
                                        if chat_id_match:
                                            target_chat_id = chat_id_match.group(1)
                                            customer_obj = Customer.objects.filter(telegram_chat_id=target_chat_id).first()
                                            if customer_obj:
                                                CustomerLog.objects.create(
                                                    customer=customer_obj,
                                                    log_type='bonus',
                                                    title="Do'kon xabari",
                                                    message=text,
                                                    details={'source': 'telegram_admin'},
                                                    amount=Decimal('0.00')
                                                )
                                            send_customer_msg(target_chat_id, f"💬 *Baxmal Meat Operatoridan Javob:*\n\n{text}")
                                            send_admin_msg(chat_id, f"✅ *Javobingiz mijozga yetkazildi!*")
                                            continue

                                    admin_dispatch_command(chat_id, text)
                            elif 'callback_query' in update:
                                cb = update['callback_query']
                                chat_id = cb['message']['chat']['id']
                                msg_id = cb['message']['message_id']
                                cb_data = cb.get('data', '')
                                cb_id = cb['id']
                                safe_print(f"[ADMIN BOT] Callback ({chat_id}): {cb_data}")
                                admin_dispatch_callback(chat_id, msg_id, cb_data, cb_id)
                        except Exception as e:
                            safe_print(f"[ADMIN BOT XATO]: {e}")

            elif resp.status_code == 409:
                safe_print("[ADMIN BOT] 409 Conflict - 5 soniya kutilmoqda...")
                time.sleep(5)
            else:
                time.sleep(3)
        except Exception as e:
            time.sleep(3)


def run_customer_bot_loop():
    """Mijozlar E-Commerce Boti uchun Long-Polling sikli."""
    offset = 0
    safe_print("[CUSTOMER BOT] Ishga tushmoqda...")
    url = f"https://api.telegram.org/bot{CUSTOMER_BOT_TOKEN}/getUpdates"
    while True:
        try:
            params = {
                'offset': offset,
                'timeout': 20,
                'allowed_updates': ['message', 'callback_query'],
            }
            resp = requests.get(url, params=params, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('ok'):
                    for update in data.get('result', []):
                        offset = update['update_id'] + 1
                        try:
                            handle_customer_update(update)
                        except Exception as e:
                            safe_print(f"[CUSTOMER BOT XATO]: {e}")
            elif resp.status_code == 409:
                safe_print("[CUSTOMER BOT] 409 Conflict - 5 soniya kutilmoqda...")
                time.sleep(5)
            else:
                time.sleep(3)
        except Exception as e:
            time.sleep(3)


class Command(BaseCommand):
    help = "Ikkala Telegram botni (Admin va Mijoz) bir vaqtda parallel ishga tushiradi."

    def handle(self, *args, **options):
        safe_print("==================================================")
        safe_print("  MEATFLOW PRO — IKKALA TELEGRAM BOT ISHGA TUSHDI ")
        safe_print("==================================================")
        safe_print("1. Admin & Kassa Boti: [Faol]")
        safe_print("2. Mijozlar E-Commerce Boti: [Faol]")
        safe_print("Telegramdan xabarlar kutilmoqda...\n")

        t1 = threading.Thread(target=run_admin_bot_loop, daemon=True)
        t2 = threading.Thread(target=run_customer_bot_loop, daemon=True)

        t1.start()
        t2.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            safe_print("\nBotlar to'xtatildi.")
