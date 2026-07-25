"""
Baxmal Meat Kassa — Kunlik Hisobot Yuborish
============================================
Ishga tushirish: python manage.py send_daily_report

Har kuni soat 22:00 da cron/Task Scheduler orqali ishga tushiriladi:
  Cron: 0 22 * * * cd /path/to/meat && python manage.py send_daily_report
  Windows Task Scheduler: python.exe manage.py send_daily_report
"""
from django.core.management.base import BaseCommand
from pos.telegram_bot import generate_daily_report


class Command(BaseCommand):
    help = 'Kunlik savdo hisobotini Telegram guruhga yuborish'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            default=None,
            help='Sana (YYYY-MM-DD formatda). Default: bugun'
        )

    def handle(self, *args, **options):
        from datetime import datetime

        target_date = None
        if options['date']:
            try:
                target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stderr.write(self.style.ERROR("Noto'g'ri sana formati! YYYY-MM-DD kerak."))
                return

        self.stdout.write("📋 Kunlik hisobot tayyorlanmoqda...")

        try:
            report = generate_daily_report(target_date)
            self.stdout.write(self.style.SUCCESS("✅ Kunlik hisobot Telegramga muvaffaqiyatli yuborildi!"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Xatolik: {e}"))
