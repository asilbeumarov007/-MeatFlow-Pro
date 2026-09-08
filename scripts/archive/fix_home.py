import sys
import re

def fix_garbled_text(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines):
        if "MeatFlow Pro" in line and "Analitika & Boshqaruv" in line and "{%" not in line:
            lines[i] = "    🛡️ MeatFlow Pro 📊 Analitika & Boshqaruv\n"
        elif "{{ store.name" in line and "Baxmal Meat Boutique" in line:
            lines[i] = "    🥩 {{ store.name|default:\"MeatFlow Pro | Baxmal Meat Boutique\" }}\n"
        elif "MEATFLOW PRO: MANAGER DASHBOARD" in line:
            lines[i] = "     MEATFLOW PRO: MANAGER DASHBOARD\n"
        elif "Bosh sahifa reklama va sarlavhalarini admin panel orqali 1-clickda o'zgartirishingiz mumkin" in line:
            lines[i] = "    <span>💡 Bosh sahifa reklama va sarlavhalarini admin panel orqali 1-clickda o'zgartirishingiz mumkin.</span>\n"
        elif "Bosh Sahifani Tahrirlash" in line and "btn" not in line:
            lines[i] = "    ⚙️ Bosh Sahifani Tahrirlash\n"
        elif "Haftalik Nasiya & Qarz Risk dinamikasi" in line:
            lines[i] = "            📊 Haftalik Nasiya & Qarz Risk dinamikasi\n"

        # Fix the decorative lines
        if "РЎвЂљР ТђР В" in line or "РЎвЂљР Тђ" in line:
            lines[i] = "     ========================================================================\n"

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Fixed home.html")

if __name__ == '__main__':
    fix_garbled_text('templates/home.html')
