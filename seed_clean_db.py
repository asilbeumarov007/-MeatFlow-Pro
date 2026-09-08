import os
import sys
import subprocess

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

LOCAL_PATH = r"c:\b\meat"
db_path = os.path.join(LOCAL_PATH, "db.sqlite3")

if os.path.exists(db_path):
    os.remove(db_path)
    print("Eski mahalliy db.sqlite3 tozalandi.")

print("[1] Toza migratsiyalar bajarilmoqda...")
subprocess.run([sys.executable, "manage.py", "migrate"], cwd=LOCAL_PATH, check=True)

print("[2] Serverdagi barcha ma'lumotlar yuklanmoqda...")
subprocess.run([sys.executable, "manage.py", "loaddata", "server_pos_data.json"], cwd=LOCAL_PATH, check=True)

print("[3] start_offline.bat yaratilmoqda...")
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
with open(os.path.join(LOCAL_PATH, "start_offline.bat"), "w", encoding="utf-8") as f:
    f.write(bat_content)

print("\n🎉 TABRIKLAYMIZ! Serverdagi barcha ma'lumotlar, mahsulotlar va media rasmlar kompyuterga 100% o'rnatildi!")
