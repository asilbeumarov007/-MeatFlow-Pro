"""
Baxmal Meat Kassa — Telegram Bot Long-Polling Management Command
================================================================
Ishga tushirish: python manage.py run_telegram_bot

Bu buyruq Telegram API'dan long-polling usulida yangi xabarlarni kutib,
kelgan buyruq va tugma bosilishlarini pos.telegram_bot moduliga yo'naltiradi.
"""
import time
import sys
import requests
from django.core.management.base import BaseCommand
from pos.telegram_bot import (
    API_URL, dispatch_command, dispatch_callback
)

# Fix Windows console UTF-8 output encoding for emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass


def safe_write(stream, text):
    """Windows terminalda emojilar charmap xatosini bermasligi uchun xavfsiz yozish."""
    try:
        stream.write(text + '\n')
    except Exception:
        try:
            clean_text = text.encode('ascii', errors='ignore').decode('ascii')
            stream.write(clean_text + '\n')
        except:
            pass


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
                    offset = results[-3]['update_id']
                    safe_write(self.stdout, f"[INFO] {len(results) - 3} ta eski xabar o'tkazib yuborildi.")
        except Exception as e:
            safe_write(self.stdout, f"[INFO] Startup checkda xatolik: {e}")

        safe_write(self.stdout, "\n===== BAXMAL MEAT TELEGRAM BOT ISHGA TUSHDI =====\nLong-polling timeout: 30s\nBuyruqlarni kutmoqda...\n")

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
                    safe_write(self.stderr, f"[XATO] Telegram API xatosi: {resp.status_code}")
                    time.sleep(5)
                    continue

                data = resp.json()
                if not data.get('ok'):
                    safe_write(self.stderr, f"[XATO] Telegram javobi: {data}")
                    time.sleep(5)
                    continue

                results = data.get('result', [])

                for update in results:
                    offset = update['update_id'] + 1

                    # Oddiy matn yoki ovozli xabarlar
                    if 'message' in update:
                        msg = update['message']
                        chat_id = msg['chat']['id']
                        sender = msg.get('from', {}).get('first_name', 'Nomalum')

                        if 'voice' in msg:
                            voice_id = msg['voice']['file_id']
                            safe_write(self.stdout, f"[OVOZ] {sender}: Voice message (chat: {chat_id})")
                            try:
                                from pos.telegram_bot import dispatch_voice_message
                                dispatch_voice_message(chat_id, voice_id)
                            except Exception as e:
                                safe_write(self.stderr, f"[XATO] Ovozli xabarni bajarishda: {e}")
                        elif 'audio' in msg:
                            audio_id = msg['audio']['file_id']
                            safe_write(self.stdout, f"[AUDIO] {sender}: Audio message (chat: {chat_id})")
                            try:
                                from pos.telegram_bot import dispatch_voice_message
                                dispatch_voice_message(chat_id, audio_id)
                            except Exception as e:
                                safe_write(self.stderr, f"[XATO] Audio xabarni bajarishda: {e}")
                        else:
                            text = msg.get('text', '')
                            if text:
                                safe_write(self.stdout, f"[BUYRUQ] {sender}: {text} (chat: {chat_id})")
                                try:
                                    dispatch_command(chat_id, text)
                                except Exception as e:
                                    safe_write(self.stderr, f"[XATO] Buyruqni bajarishda: {e}")
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
                        safe_write(self.stdout, f"[TUGMA] {sender}: {callback_data} (chat: {chat_id})")
                        try:
                            dispatch_callback(chat_id, message_id, callback_data, callback_query_id)
                        except Exception as e:
                            safe_write(self.stderr, f"[XATO] Callback bajarishda: {e}")
                            from pos.telegram_bot import answer_callback
                            answer_callback(callback_query_id, f"Xatolik: {str(e)[:100]}")

            except requests.exceptions.Timeout:
                continue
            except requests.exceptions.ConnectionError:
                safe_write(self.stderr, "[XATO] Internet aloqasi uzildi. 10 soniyadan keyin qayta urinish...")
                time.sleep(10)
            except KeyboardInterrupt:
                safe_write(self.stdout, "\n🛑 Bot to'xtatildi. Xayr!")
                break
            except Exception as e:
                safe_write(self.stderr, f"[XATO] Kutilmagan xato: {e}")
                time.sleep(5)
