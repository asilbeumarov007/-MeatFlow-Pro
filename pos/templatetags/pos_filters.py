from django import template
from decimal import Decimal
import json

register = template.Library()

@register.filter(name='render_receipt')
def render_receipt(log):
    """
    CustomerLog dagi yangi JSON formatli details ma'lumotlarini o'qib,
    ularni chek ko'rinishidagi HTML shakliga o'tkazadi.
    Eski (HTML formatidagi) cheklar uchun log.message ni o'zini qaytaradi.
    """
    if not log:
        return ""

    message_str = getattr(log, 'message', '') or ''
    # Agar log.message allaqachon HTML chek bo'lsa (eski loglar), uni o'zini qaytaramiz
    if message_str.strip().startswith('<div'):
        return message_str

    details = getattr(log, 'details', None)
    if not details or not isinstance(details, dict) or 'items' not in details:
        # Fallback: Agar details bo'lmasa yoki unda items bo'lmasa, message dagi oddiy matnni qaytaramiz
        return message_str

    try:
        items = details.get('items', [])
        total = details.get('total', 0)
        discount = details.get('discount', 0)
        bonus_used = details.get('bonus_used', 0)
        debt_added = details.get('debt_added', 0)
        final_paid = details.get('final_paid', 0)
        payment_method = details.get('payment_method', 'naqd')
        sale_id = details.get('sale_id', '')

        # Mahsulotlarni formatlash
        receipt_items_html = ""
        for item in items:
            p_name = item.get('product_name', '')
            weight = item.get('weight', 0)
            price = item.get('price', 0)
            item_total = item.get('total', 0)

            item_fmt = "{:,}".format(int(item_total)).replace(',', ' ')
            receipt_items_html += (
                "<div style='display:flex;justify-content:space-between;"
                "font-size:14px;margin-bottom:4px;border-bottom:1px dashed "
                "rgba(0,0,0,0.1);padding-bottom:2px;'>"
                f"<span>• {p_name} ({float(weight):.3f} kg)</span>"
                f"<span style='font-weight:600'>{item_fmt} so'm</span>"
                "</div>"
            )

        fa_fmt = "{:,}".format(int(final_paid if final_paid > 0 else total)).replace(',', ' ')
        method_titles = {
            'naqd':   'Naqd Pul',
            'karta':  'Plastik Karta',
            'qr':     'Yagona QR',
            'nasiya': 'Nasiya (Qarz)',
        }
        current_method = method_titles.get(payment_method, payment_method)

        status_text = ""
        if payment_method == 'nasiya':
            status_text = (
                "<span style='color:#b71c1c;font-weight:bold'>"
                "Ushbu summa qarz hisobingizga yozildi."
                "</span>"
            )
        else:
            extra_lines = ""
            if discount > 0:
                if bonus_used > 0:
                    b_fmt = "{:,}".format(int(bonus_used)).replace(',', ' ')
                    extra_lines += (
                        f"<br><span style='color:#e65100'>"
                        f"💎 {b_fmt} so'm bonus balldan ayirildi.</span>"
                    )
                if debt_added > 0:
                    r_fmt = "{:,}".format(int(debt_added)).replace(',', ' ')
                    extra_lines += (
                        f"<br><span style='color:#b71c1c'>"
                        f"⚠️ {r_fmt} so'm qarzga yozildi.</span>"
                    )
            
            # Agar bonus ham, qarz ham qo'shilmagan bo'lsa (yoki cashback bo'lsa)
            status_text = (
                f"<span style='color:#1b5e20;font-weight:bold'>"
                f"To'lov qabul qilindi.{extra_lines}</span>"
            )

        # Chek sanasi va vaqti
        created_at_local = log.created_at
        try:
            from django.utils import timezone
            created_at_local = timezone.localtime(log.created_at)
        except Exception:
            pass
        date_str = created_at_local.strftime('%d-%m-%Y %H:%M')

        receipt_html = (
            "<div style='font-family:Courier New,monospace;background:#fff;"
            "border:1px solid #ccc;padding:12px;border-radius:8px;color:#111;'>"
            "<div style='text-align:center;font-weight:bold;font-size:16px;"
            "margin-bottom:10px;text-transform:uppercase;color:#1b5e20'>BAXMAL MEAT</div>"
            f"<div style='font-size:12px;color:#666;margin-bottom:8px;text-align:center'>"
            f"Xarid vaqti: {date_str}</div>"
            "<div style='border-top:2px dashed #333;margin-bottom:8px'></div>"
            f"{receipt_items_html}"
            "<div style='border-top:2px dashed #333;margin-top:8px;padding-top:6px'></div>"
            "<div style='display:flex;justify-content:space-between;"
            "font-size:16px;font-weight:bold;margin-bottom:4px'>"
            f"<span>JAMI:</span><span style='color:#000'>{fa_fmt} so'm</span></div>"
            "<div style='display:flex;justify-content:space-between;"
            "font-size:13px;color:#555;margin-bottom:8px'>"
            f"<span>To'lov turi:</span><span>{current_method}</span></div>"
            "<div style='border-top:1px solid #eee;padding-top:6px;"
            "font-size:12px;text-align:center;line-height:1.3'>"
            f"{status_text}<br>"
            "<span style='color:#888;font-style:italic'>"
            "Sog'lom go'sht — barakali xarid! Rahmat!</span>"
            "</div></div>"
        )
        return receipt_html
    except Exception as e:
        # Xatolik bo'lsa fallback sifatida oddiy message ni ko'rsatadi
        return message_str
