import sys
from django.core.management.base import BaseCommand
from django.utils import timezone
from pos.telegram_bot import send_daily_executive_digest

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

class Command(BaseCommand):
    help = "Do'kon egasiga kechki avtomatik Z-Hisobot va savdo xulosasini Telegram orqali yuboradi."

    def add_arguments(self, parser):
        parser.add_argument('--chat_id', type=str, help="Telegram Chat ID (ixtiyoriy)")
        parser.add_argument('--date', type=str, help="Hisobot sanasi YYYY-MM-DD (ixtiyoriy)")

    def handle(self, *args, **options):
        chat_id = options.get('chat_id')
        target_date = None
        if options.get('date'):
            from datetime import datetime
            try:
                target_date = datetime.strptime(options.get('date'), '%Y-%m-%d').date()
            except ValueError:
                self.stderr.write(self.style.ERROR("Noto'g'ri sana formati! YYYY-MM-DD kiritilishi lozim."))
                return

        self.stdout.write("Kechki Z-Hisobot Telegramga yuborilmoqda...")
        result = send_daily_executive_digest(chat_id=chat_id, target_date=target_date)
        if result:
            self.stdout.write(self.style.SUCCESS("[OK] Kechki Z-Hisobot muvaffaqiyatli yuborildi!"))
        else:
            self.stderr.write(self.style.WARNING("[OGOHLANTIRISH] Hisobot yuborilmadi. Telegram sozlamalarini tekshiring."))

