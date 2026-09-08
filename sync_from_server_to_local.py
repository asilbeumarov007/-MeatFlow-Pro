import os
import sys
import paramiko
import tarfile
import subprocess
import shutil

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

SERVER_IP = "189.74.96.249"
SERVER_USER = "root"
SERVER_PASS = "UugfwGB0L8D6dAh%"
REMOTE_PATH = "/var/www/meatflow"
LOCAL_PATH = r"c:\b\meat"

def sync_from_server():
    print("=" * 60)
    print("🚀 ESKIZ.UZ SERVERIDAN TO'G'RIDAN-TO'G'RI BARCHA FAYLLARNI YUKLAB OLISH")
    print("=" * 60)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"[*] Serverga ulanmoqda ({SERVER_IP})...")
    ssh.connect(SERVER_IP, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    print("✅ Serverga ulandi!")

    # 1. Serverdagi bazani JSON formatda dump qilish (SQLite va har qanday muhit uchun)
    print("[*] Serverdagi PostgreSQL bazasidan barcha ma'lumotlarni dump qilinmoqda...")
    dump_cmd = "cd /var/www/meatflow && /var/www/meatflow/venv/bin/python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 2 > /tmp/server_dump.json"
    stdin, stdout, stderr = ssh.exec_command(dump_cmd)
    exit_status = stdout.channel.recv_exit_status()
    if exit_status == 0:
        print("✅ Server ma'lumotlari muvaffaqiyatli dump qilindi (/tmp/server_dump.json)")
    else:
        err = stderr.read().decode('utf-8')
        print(f"⚠️ Dump ogohlantirish: {err}")

    # 2. Serverdagi barcha loyiha fayllarini arxivlash (media, kodlar va barchasi)
    print("[*] Serverdagi loyiha fayllari arxivlanmoqda...")
    tar_cmd = "tar -czf /tmp/meatflow_backup.tar.gz -C /var/www/meatflow --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' ."
    stdin, stdout, stderr = ssh.exec_command(tar_cmd)
    exit_status = stdout.channel.recv_exit_status()
    if exit_status == 0:
        print("✅ Loyiha arxivi yaratildi (/tmp/meatflow_backup.tar.gz)")
    else:
        print("⚠️ Arxivlashda xatolik:", stderr.read().decode('utf-8'))

    # 3. SFTP orqali yuklab olish
    sftp = ssh.open_sftp()
    
    local_tar = os.path.join(LOCAL_PATH, "server_meatflow.tar.gz")
    local_dump = os.path.join(LOCAL_PATH, "server_dump.json")
    
    print(f"[*] Arxiv kompyuterga yuklab olinmoqda -> {local_tar}...")
    sftp.get("/tmp/meatflow_backup.tar.gz", local_tar)
    print("✅ Arxiv kompyuterga muvaffaqiyatli yuklab olindi!")
    
    print(f"[*] Baza dump fayli yuklab olinmoqda -> {local_dump}...")
    sftp.get("/tmp/server_dump.json", local_dump)
    print("✅ Baza dump fayli yuklab olindi!")
    
    sftp.close()
    ssh.close()
    
    # 4. Arxivni kompyuterga ochish
    print("[*] Arxiv kompyuterdagi papkaga yoyilmoqda...")
    with tarfile.open(local_tar, "r:gz") as tar:
        tar.extractall(LOCAL_PATH)
    print("✅ Barcha fayllar, media rasmlar va shablonlar kompyuterga yangilandi!")
    
    # Tozalash
    if os.path.exists(local_tar):
        os.remove(local_tar)

    # 5. Mahalliy SQLite bazasini yangilash
    print("[*] Mahalliy oflayn baza (db.sqlite3) tayyorlanmoqda...")
    try:
        # Migratsiyalarni mahalliy SQLite ga qo'llash
        env = os.environ.copy()
        env['DJANGO_SETTINGS_MODULE'] = 'config.settings'
        # DB_ENGINE sqlite bo'lishi uchun
        
        print("[*] Mahalliy migratsiyalar bajarilmoqda...")
        subprocess.run([sys.executable, "manage.py", "migrate"], cwd=LOCAL_PATH, check=True)
        
        print("[*] Serverdagi ma'lumotlar mahalliy bazaga tiklanmoqda...")
        subprocess.run([sys.executable, "manage.py", "loaddata", "server_dump.json"], cwd=LOCAL_PATH, check=True)
        print("✅ Barcha server ma'lumotlari mahalliy oflayn bazaga o'rnatildi!")
    except Exception as e:
        print(f"⚠️ Mahalliy bazaga yuklash jarayonida ogohlantirish: {e}")

    print("\n🎉 [TUGADI] Eskiz.uz serveridagi barcha loyiha to'liq kompyuterga ko'chirildi!")

if __name__ == "__main__":
    sync_from_server()
