import os
import sys
import paramiko
import zipfile
import subprocess
import shutil

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

SERVER_IP = "189.74.96.249"
SERVER_USER = "root"
SERVER_PASS = "UugfwGB0L8D6dAh%"
LOCAL_PATH = r"c:\b\meat"

def main():
    print("=" * 60)
    print("🚀 ESKIZ.UZ SERVERIDAN TO'G'RIDAN-TO'G'RI YUKLAB OLISH")
    print("=" * 60)
    
    # 0. Eski nosoz fayllarni tozalash
    old_tar = os.path.join(LOCAL_PATH, "server_meatflow.tar.gz")
    if os.path.exists(old_tar):
        os.remove(old_tar)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"[*] Serverga ulanmoqda ({SERVER_IP})...")
    ssh.connect(SERVER_IP, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    print("✅ Serverga ulandi!")

    # 1. Serverdagi bazani JSON formatda dump qilish
    print("[*] Serverdagi bazadan ma'lumotlar olinmoqda...")
    cmd_dump = "cd /var/www/meatflow && /var/www/meatflow/venv/bin/python manage.py dumpdata pos accounts articles pages --indent 2 > /tmp/pos_data.json"
    stdin, stdout, stderr = ssh.exec_command(cmd_dump)
    stdout.channel.recv_exit_status()
    print("✅ Baza ma'lumotlari tayyorlandi!")

    # 2. Serverdagi barcha fayllarni (media, shablonlar, kodlar) tar.gz qilish
    print("[*] Serverdagi loyiha fayllari arxivlanmoqda...")
    cmd_tar = "cd /var/www/meatflow && tar --exclude='./venv' --exclude='./.git' --exclude='*.pyc' --exclude='__pycache__' --exclude='*.zip' --exclude='*.tar.gz' --exclude='*.tar' --exclude='*.sql*' --exclude='staticfiles' -czf /tmp/meatflow_server_clean.tar.gz ."
    stdin, stdout, stderr = ssh.exec_command(cmd_tar)
    status = stdout.channel.recv_exit_status()
    if status != 0:
        print("Tar xatolik:", stderr.read().decode())
    print("✅ Loyiha arxivi yaratildi!")

    # 3. SFTP orqali yuklab olish
    sftp = ssh.open_sftp()
    
    local_tar = os.path.join(LOCAL_PATH, "meatflow_server_clean.tar.gz")
    local_json = os.path.join(LOCAL_PATH, "server_pos_data.json")
    
    print(f"[*] Loyiha arxivi yuklab olinmoqda -> {local_tar}...")
    sftp.get("/tmp/meatflow_server_clean.tar.gz", local_tar)
    print("✅ Loyiha arxivi to'liq yuklab olindi!")

    print(f"[*] Baza dump fayli yuklab olinmoqda -> {local_json}...")
    sftp.get("/tmp/pos_data.json", local_json)
    print("✅ Baza fayli to'liq yuklab olindi!")

    sftp.close()
    ssh.close()

    # 4. TAR.GZ arxivni kompyuterga yoyish
    print("[*] Loyiha fayllari kompyuter papkasiga yoyilmoqda...")
    with tarfile.open(local_tar, 'r:gz') as tar_ref:
        tar_ref.extractall(LOCAL_PATH)
    print("✅ Barcha fayllar, media rasmlar va shablonlar yangilandi!")
    
    if os.path.exists(local_tar):
        os.remove(local_tar)

    # 5. Mahalliy SQLite bazasini yangilash
    print("\n[*] Mahalliy oflayn SQLite bazasiga ma'lumotlarni o'rnatish...")
    subprocess.run([sys.executable, "manage.py", "migrate"], cwd=LOCAL_PATH, check=True)
    subprocess.run([sys.executable, "manage.py", "loaddata", "server_pos_data.json"], cwd=LOCAL_PATH, check=True)
    print("✅ Serverdagi barcha ma'lumotlar mahalliy oflayn bazaga to'liq tiklandi!")

    # 6. start_offline.bat yaratish
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
    print("🎉 BARCHASI TUGADI! DASTUR VA BAZA KOMPYUTERDA TO'LIQ OFLAYN ISHGA TAYYOR!")
    print("Ishga tushirish uchun 'start_offline.bat' faylini bosing.")
    print("=" * 60)

if __name__ == "__main__":
    main()
