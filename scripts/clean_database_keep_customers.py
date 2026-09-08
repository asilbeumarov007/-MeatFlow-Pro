import os
import sys

sys.path.insert(0, r'c:\b\meat')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from decimal import Decimal
from django.db import transaction
from pos.models import (
    Customer, Product, Stock, StockBatch, Sale, SaleItem,
    CashierShift, CashTransaction, PaymentProof, Slaughter,
    B2BOrder, CustomerLog, AIChatMessage, Notebook, Supplier
)

print("=" * 60)
print("BAZANI TOZALASH (FAQAT MIJOZLAR VA ULARNING QARZLARI SAQLANADI)")
print("=" * 60)

with transaction.atomic():
    # 1. Clear Sales & Items
    sale_items_count = SaleItem.objects.count()
    SaleItem.objects.all().delete()
    print(f"[-] SaleItem ochirildi: {sale_items_count} ta")

    sales_count = Sale.objects.count()
    Sale.objects.all().delete()
    print(f"[-] Sale (Savdolar) ochirildi: {sales_count} ta")

    # 2. Clear Shifts
    shifts_count = CashierShift.objects.count()
    CashierShift.objects.all().delete()
    print(f"[-] CashierShift (Kassa smenalari) ochirildi: {shifts_count} ta")

    # 3. Clear Cash Transactions (Kirim / Chiqim)
    tx_count = CashTransaction.objects.count()
    CashTransaction.objects.all().delete()
    print(f"[-] CashTransaction (Kassa tranzaksiyalari) ochirildi: {tx_count} ta")

    # 4. Clear Payment Proofs (Cheklar)
    proof_count = PaymentProof.objects.count()
    PaymentProof.objects.all().delete()
    print(f"[-] PaymentProof (Tolov cheklari) ochirildi: {proof_count} ta")

    # 5. Clear Slaughters & Stock Batches
    slaughter_count = Slaughter.objects.count()
    Slaughter.objects.all().delete()
    print(f"[-] Slaughter (Soyimlar) ochirildi: {slaughter_count} ta")

    batch_count = StockBatch.objects.count()
    StockBatch.objects.all().delete()
    print(f"[-] StockBatch (Partiyalar) ochirildi: {batch_count} ta")

    # 6. Reset Stock quantities to 0
    Stock.objects.all().update(quantity=Decimal('0.000'))
    print(f"[OK] Mahsulotlar zaxirasi 0.000 kg ga tushirildi (Mahsulotlar nomi saqlandi)")

    # 7. Clear B2B Orders
    b2b_count = B2BOrder.objects.count()
    B2BOrder.objects.all().delete()
    print(f"[-] B2BOrder (Online buyurtmalar) ochirildi: {b2b_count} ta")

    # 8. Clear Customer Logs & AI Messages
    logs_count = CustomerLog.objects.count()
    CustomerLog.objects.all().delete()
    print(f"[-] CustomerLog (Xabarlar tarixi) ochirildi: {logs_count} ta")

    ai_count = AIChatMessage.objects.count()
    AIChatMessage.objects.all().delete()
    print(f"[-] AIChatMessage (AI xabarlari) ochirildi: {ai_count} ta")

    # 9. Clear Notebook
    notes_count = Notebook.objects.count()
    Notebook.objects.all().delete()
    print(f"[-] Notebook (Qoralamalar) ochirildi: {notes_count} ta")

    # 10. Summary of Preserved Customers
    customers = Customer.objects.all()
    total_debt = sum(c.debt_amount for c in customers)
    print("=" * 60)
    print(f"[OK] SAQLAB QOLINGAN MIJOZLAR: {customers.count()} ta")
    print(f"[OK] JAMI MIJOZLAR QARZI: {total_debt:,.0f} so'm")
    print("=" * 60)
    print("Muvaffaqiyatli yakunlandi! Baza toza holatga keltirildi.")
