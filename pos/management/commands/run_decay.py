from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from pos.models import StockBatch, CashTransaction

class Command(BaseCommand):
    help = "Sovuqxonadagi mahsulot partiyalarining kunlik qurish zararini (decay loss) hisoblash va kassaga xarajat sifatida yozish"

    def handle(self, *args, **options):
        active_batches = StockBatch.objects.filter(current_quantity__gt=0)
        self.stdout.write(self.style.SUCCESS(f"Tizimda {active_batches.count()} ta faol zaxira partiyalari topildi."))

        total_loss_amount = Decimal("0.00")
        total_loss_weight = Decimal("0.000")

        for batch in active_batches:
            days = batch.get_days_passed()
            if days <= 0:
                continue

            # Bir kun oldingi va bugungi vazn farqi
            # Kechagi vazn: factor = (1 - decay_rate/100)^(days-1)
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
