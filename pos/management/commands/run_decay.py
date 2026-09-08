import sys
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from pos.models import StockBatch, CashTransaction
from pos.telegram_bot import send_message, CHAT_ID

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
    help = "Sovuqxonadagi mahsulot partiyalarining kunlik qurish zararini (decay loss) hisoblash va vitrinadagi 2+ kunlik partiyalar bo'yicha AI tavsiyalarini jo'natish"

    def handle(self, *args, **options):
        active_batches = StockBatch.objects.filter(current_quantity__gt=Decimal('0.05'))
        self.stdout.write(self.style.SUCCESS(f"Tizimda {active_batches.count()} ta faol zaxira partiyalari topildi."))

        total_loss_amount = Decimal("0.00")
        total_loss_weight = Decimal("0.000")
        ai_warnings = []

        for batch in active_batches:
            days = batch.get_days_passed()
            
            # AI Recommendation for batches >= 2 days
            ai_rec = batch.get_ai_recommendation()
            if ai_rec:
                ai_warnings.append(ai_rec)

            if days <= 0:
                continue

            # Bir kun oldingi va bugungi vazn farqi
            factor_yesterday = Decimal(str((1 - float(batch.decay_rate_per_day)/100.0) ** (days - 1)))
            weight_yesterday = (batch.current_quantity * factor_yesterday).quantize(Decimal('0.001'))

            weight_today = batch.get_decayed_weight()
            day_loss = (weight_yesterday - weight_today).quantize(Decimal('0.001'))

            if day_loss > 0:
                loss_cost = (day_loss * batch.purchase_price_per_kg).quantize(Decimal('0.01'))
                
                # Chiqim tranzaksiyasini yaratish
                CashTransaction.objects.create(
                    transaction_type='out',
                    amount=loss_cost,
                    category='expense',
                    payment_method='naqd',
                    description=f"Kunlik zaxira qurish zarari: {batch.product.name} (Partiya #{batch.id}) - {day_loss} kg"
                )

                total_loss_amount += loss_cost
                total_loss_weight += day_loss
                
                self.stdout.write(f" - Partiya #{batch.id} ({batch.product.name}): Qurish = {day_loss} kg, Zarar = {loss_cost:,} so'm")

        self.stdout.write(self.style.SUCCESS(
            f"Jami hisoblangan kunlik qurish zarari: {total_loss_weight} kg ({total_loss_amount:,} so'm)"
        ))

        # Telegram AI ogohlantirishini yuborish
        if ai_warnings:
            self.stdout.write(self.style.WARNING(f"⚠️ {len(ai_warnings)} ta partiya bo'yicha AI tavsiyasi shakllantirildi."))
            msg = (
                f"🥩 *VITRINA & QURISH ZARARI — AI TAVSIYALARI*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Do'kon mudiriga diqqat! Vitrinada 2 kundan ortiq turgan partiyalar aniqlandi:\n\n"
            )
            for idx, w in enumerate(ai_warnings, 1):
                msg += (
                    f"{idx}. ⚠️ *{w['product_name']}* (Partiya #{w['batch_id']})\n"
                    f"   ⏳ *Turgan vaqti:* `{w['days']} kun` | 📦 *Qoldiq:* `{w['quantity']:.2f} kg`\n"
                    f"   📉 *Taxminiy yo'qotish:* `{w['decay_loss_kg']:.3f} kg` (~`{w['decay_loss_sum']:,.0f}` so'm)\n"
                    f"   💡 *AI Maslahat:* _{w['message']}_\n\n"
                )
            msg += (
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ *Tavsiya:* Zararni kamaytirish uchun ushbu partiyalarni qiymaga aylantiring yoki maxsus chegirma e'lon qiling."
            )
            try:
                send_message(CHAT_ID, msg)
                self.stdout.write(self.style.SUCCESS("[OK] AI tavsiyalari Telegramga yuborildi!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Telegramga yuborishda xato: {e}"))

