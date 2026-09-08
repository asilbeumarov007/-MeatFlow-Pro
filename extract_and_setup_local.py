import os
import sys
import tarfile
import subprocess

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

LOCAL_PATH = r"c:\b\meat"

def main():
    print("=" * 60)
    print("🚀 SERVERDAN YUKLAB OLINGAN FAYLLARNI O'RNATISH")
    print("=" * 60)

    local_tar = os.path.join(LOCAL_PATH, "meatflow_server_clean.tar.gz")
    local_json = os.path.join(LOCAL_PATH, "server_pos_data.json")

    if os.path.exists(local_tar):
        print(f"[*] Loyiha arxivi ({os.path.getsize(local_tar):,} bayt) ochilmoqda...")
        with tarfile.open(local_tar, 'r:gz') as tar_ref:
            tar_ref.extractall(LOCAL_PATH)
        print("✅ Barcha server fayllari, rasmlar va shablonlar kompyuterga joylashtirildi!")
        os.remove(local_tar)

    print("\n[*] Mahalliy oflayn SQLite bazasi (db.sqlite3) sozlanmoqda...")
    subprocess.run([sys.executable, "manage.py", "migrate"], cwd=LOCAL_PATH, check=True)

    if os.path.exists(local_json):
        print(f"[*] Server ma'lumotlari bazaga yuklanmoqda ({local_json})...")
        subprocess.run([sys.executable, "manage.py", "loaddata", "server_pos_data.json"], cwd=LOCAL_PATH, check=True)
        print("✅ Serverdagi barcha mahsulotlar, ta'minotchilar va sozlamalar mahalliy bazaga yuklandi!")

    print("\n[*] Oflayn ishga tushirish faylini yaratish (start_offline.bat)...")
    bat_content = """@echo off
title Baxmal Meat Boutique - Oflayn Tizim (MeatFlow Pro)
color 0A
echo ======================================================
echo    BAXMAL MEAT BOUTIQUE - OFLAYN DASTURI ISHGA TUSHMOQDA
echo ======================================================
echo.
echo [1] Dastur ishga tushirilmoqda: http://127.0.0.1:8000
echo [2] Brauzer avtomatik ochiladi...
echo.
start http://127.0.0.1:8000
python manage.py runserver 0.0.0.0:8000
pause
"""
    bat_path = os.path.join(LOCAL_PATH, "start_offline.bat")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)
    print(f"✅ Oflayn ishga tushirish fayli yaratildi: {bat_path}")

    print("\n" + "=" * 60)
    print("🎉 BARCHASI 100% TUGADI! DASTUR VA BAZA KOMPYUTERDA TO'LIQ OFLAYN ISHGA TAYYOR!")
    print("=" * 60)

if __name__ == "__main__":
    main()
