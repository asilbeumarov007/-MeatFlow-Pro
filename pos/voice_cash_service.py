import re
import os
import json
import logging
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum
from .models import CashTransaction, Supplier, Customer, CashierShift, Sale

logger = logging.getLogger(__name__)

def parse_uzbek_amount(text):
    """
    O'zbekcha matndagi summani son shakliga o'tkazish.
    Masalan:
      '45 ming' -> 45000
      '5 million' -> 5000000
      '1.5 million' -> 1500000
      'bir yarim million' -> 1500000
      'yarim million' -> 500000
      '250000' -> 250000
    """
    text = text.lower().replace(",", ".").strip()
    
    # 1. Yarim million / bir yarim million
    if "bir yarim million" in text or "1.5 million" in text or "1.5 mln" in text:
        return Decimal('1500000.00')
    if "yarim million" in text or "0.5 million" in text:
        return Decimal('500000.00')

    # 2. X million / mln
    m_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:million|mln)', text)
    if m_match:
        val = float(m_match.group(1)) * 1_000_000
        return Decimal(str(int(val)))

    # 3. X ming / k
    k_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:ming|k\b)', text)
    if k_match:
        val = float(k_match.group(1)) * 1_000
        return Decimal(str(int(val)))

    # 4. Oddiy raqamlar (kamida 3-4 xonali yoki so'm bilan kelgan)
    num_match = re.search(r'(\d{3,12})', text.replace(" ", ""))
    if num_match:
        return Decimal(num_match.group(1))

    # 5. So'z bilan raqamlar
    word_map = {
        'bir': 1, 'ikki': 2, 'uch': 3, 'to\'rt': 4, 'besh': 5,
        'olti': 6, 'yetti': 7, 'sakkiz': 8, 'to\'qqiz': 9, 'o\'n': 10,
        'yigirma': 20, 'o\'ttiz': 30, 'qirq': 40, 'ellik': 50,
        'oltmish': 60, 'yetmish': 70, 'sakson': 80, 'to\'qson': 90,
        'yuz': 100
    }
    for w, num in word_map.items():
        if f"{w} ming" in text:
            return Decimal(str(num * 1000))
        if f"{w} million" in text:
            return Decimal(str(num * 1000000))

    return Decimal('0.00')

def find_matching_supplier(text):
    """Matnda ta'minotchi (chorvador) nomi bor-yo'qligini aniqlash."""
    t_lower = text.lower()
    suppliers = list(Supplier.objects.all())
    
    # 1. To'liq ism (First + Last)
    for s in suppliers:
        full = f"{(s.first_name or '').strip()} {(s.last_name or '').strip()}".lower().strip()
        if full and len(full) >= 5 and full in t_lower:
            return s

    # 2. Ism bo'yicha aniq moslik (First Name priority!)
    for s in suppliers:
        f_name = (s.first_name or "").lower().strip()
        if f_name and len(f_name) >= 3 and f_name in t_lower:
            return s

    # 3. Custom ID (masalan T-2255 yoki 2255)
    for s in suppliers:
        c_id = (s.custom_id or "").lower().strip()
        if c_id and c_id in t_lower:
            return s

    # 4. Familiya bo'yicha (umumiy so'zlar: jiyan, toga, aka, uka hisobga olinmaydi)
    generic_words = {'jiyan', 'toga', 'tog\'a', 'aka', 'uka', 'ukam', 'akam', 'bobo', 'mulla'}
    for s in suppliers:
        l_name = (s.last_name or "").lower().strip()
        if l_name and len(l_name) >= 3 and l_name not in generic_words and l_name in t_lower:
            return s

    return None

def parse_voice_cash_intent(raw_text):
    """
    Ovozli matndan tranzaksiya parametrlarini ajratib olish (Lokal NLU).
    """
    t_lower = raw_text.lower().strip()
    amount = parse_uzbek_amount(t_lower)
    
    # 1. Tranzaksiya turi (in yoki out)
    in_keywords = ['kirim', 'kiritildi', 'kassaga', 'qo\'shildi', 'tushum', 'berdi', 'oldi', 'qaytdi', 'olib keldi']
    out_keywords = ['chiqim', 'xarajat', 'berildi', 'berdim', 'to\'landi', 'to\'ladik', 'sarflandi', 'ketdi', 'to\'lov']
    
    # Check supplier first
    matched_supplier = find_matching_supplier(t_lower)
    
    # Heuristics for direction
    is_in = any(kw in t_lower for kw in in_keywords)
    is_out = any(kw in t_lower for kw in out_keywords)
    
    if matched_supplier and ('berildi' in t_lower or 'berdim' in t_lower or 'to\'landi' in t_lower or 'to\'ladik' in t_lower or is_out):
        tx_type = 'out'
        category = 'supplier_pay'
        desc = f"{matched_supplier.first_name} {matched_supplier.last_name or ''}ga chorva to'lovi".strip()
    elif is_in and not is_out:
        tx_type = 'in'
        if 'mayda' in t_lower or 'boshlang\'ich' in t_lower or 'float' in t_lower:
            category = 'kassa_float'
            desc = "Kassaga mayda pul kiritildi"
        elif 'qarz' in t_lower or 'nasiya' in t_lower:
            category = 'debt_pay'
            desc = "Mijozdan nasiya to'lovi qabul qilindi"
        else:
            category = 'other'
            desc = "Kassaga kirim"
    else:
        # Default out (chiqim / xarajat)
        tx_type = 'out'
        if 'oylik' in t_lower or 'ish haqi' in t_lower or 'avans' in t_lower:
            category = 'salary'
            desc = "Ish haqi / avans to'lovi"
        elif 'tushlik' in t_lower or 'ovqat' in t_lower or 'choy' in t_lower:
            category = 'expense'
            desc = "Xodimlar tushligi"
        elif 'ijara' in t_lower or 'arenda' in t_lower:
            category = 'expense'
            desc = "Do'kon ijarasi (arenda)"
        elif 'yo\'l' in t_lower or 'benzin' in t_lower or 'taksi' in t_lower:
            category = 'expense'
            desc = "Yo'l xarajati (benzin/taksi)"
        elif 'usta' in t_lower or 'remont' in t_lower:
            category = 'expense'
            desc = "Usta / ta'mirlash xarajati"
        else:
            category = 'expense'
            desc = "Do'kon xarajati"

    # Toza izoh
    if not desc or desc == "Do'kon xarajati":
        desc = raw_text.capitalize()

    return {
        'transaction_type': tx_type,
        'amount': amount,
        'category': category,
        'supplier': matched_supplier,
        'description': desc,
        'raw_text': raw_text
    }

def execute_voice_cash_transaction(user, raw_text, custom_parsed=None):
    """
    Ovozli matn asosida haqiqiy tranzaksiyani bazaga yozish va kassa/ta'minotchi balansini yangilash.
    """
    parsed = custom_parsed or parse_voice_cash_intent(raw_text)
    amount = parsed.get('amount', Decimal('0.00'))
    
    if amount <= Decimal('0.00'):
        return {
            'success': False,
            'message': f"Ovozda aniq summa aniqlanmadi ('{raw_text}'). Iltimos, masalan: 'Tushlikka 45 ming chiqim' deb ayting.",
            'parsed': parsed
        }

    tx_type = parsed['transaction_type']
    category = parsed['category']
    supplier = parsed.get('supplier')
    desc = parsed['description']

    # 1. CashTransaction yaratish
    tx = CashTransaction.objects.create(
        transaction_type=tx_type,
        amount=amount,
        category=category,
        payment_method='naqd',
        description=desc,
        voice_raw_text=raw_text,
        created_by=user if user and user.is_authenticated else None,
        supplier=supplier
    )

    # 2. Agar ta'minotchi bo'lsa -> qarzini kamaytirish
    supplier_info = ""
    if supplier and tx_type == 'out':
        old_debt = supplier.our_debt
        supplier.our_debt = max(Decimal('0.00'), supplier.our_debt - amount)
        supplier.save(update_fields=['our_debt'])
        supplier_info = f" {supplier.first_name}dan qarzimiz: {supplier.our_debt:,.0f} so'm qoldi.".replace(",", " ")

    # 3. Kassadagi joriy kutilayotgan naqd pulni hisoblash
    active_shift = CashierShift.objects.filter(is_open=True).order_by('-opened_at').first()
    opening_cash = active_shift.opening_cash if active_shift else Decimal('0.00')
    
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    cash_sales = Sale.objects.filter(payment_method='naqd', created_at__gte=today_start).aggregate(
        t=Sum('total_amount')
    )['t'] or Decimal('0.00')
    
    cash_in = CashTransaction.objects.filter(transaction_type='in', payment_method='naqd', created_at__gte=today_start).aggregate(
        t=Sum('amount')
    )['t'] or Decimal('0.00')
    
    cash_out = CashTransaction.objects.filter(transaction_type='out', payment_method='naqd', created_at__gte=today_start).aggregate(
        t=Sum('amount')
    )['t'] or Decimal('0.00')

    expected_drawer = opening_cash + cash_sales + cash_in - cash_out
    drawer_str = f"{expected_drawer:,.0f} so'm".replace(",", " ")
    amount_str = f"{amount:,.0f} so'm".replace(",", " ")

    type_label = "Kirim" if tx_type == 'in' else "Chiqim"
    confirmation_text = (
        f"✅ {type_label} muvaffaqiyatli kiritildi: {amount_str} ({desc})."
        f"{supplier_info} Kassadagi kutilayotgan naqd pul: {drawer_str}."
    )

    return {
        'success': True,
        'message': confirmation_text,
        'transaction_id': tx.id,
        'transaction_type': tx_type,
        'amount': float(amount),
        'category': category,
        'supplier_name': f"{supplier.first_name} {supplier.last_name or ''}".strip() if supplier else None,
        'description': desc,
        'expected_drawer': float(expected_drawer),
        'created_at': tx.created_at.strftime('%H:%M:%S')
    }
