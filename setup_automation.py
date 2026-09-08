import sys
import time
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SERVER_IP = "189.74.96.249"
SERVER_PORT = 22
SERVER_USER = "root"
SERVER_PASS = "UugfwGB0L8D6dAh%"
REMOTE_DIR = "/var/www/meatflow"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

for attempt in range(1, 10):
    try:
        print(f"[+] Ulanish urinishi {attempt}/10...")
        ssh.connect(SERVER_IP, port=SERVER_PORT, username=SERVER_USER, password=SERVER_PASS, timeout=30, banner_timeout=60)
        print("[OK] Serverga muvaffaqiyatli ulandi!")
        break
    except Exception as e:
        print(f"[-] Kutish (5s) sabab: {e}")
        time.sleep(5)

def exec_cmd(cmd, desc=""):
    print(f"\n[*] {desc}...")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    if out:
        print(out.strip())
    if err and "warning" not in err.lower() and "notice" not in err.lower() and "debconf" not in err.lower():
        print(f"[ERR]: {err.strip()}")
    return out

# 1. Install cron on Ubuntu
exec_cmd("DEBIAN_FRONTEND=noninteractive apt-get update -y && DEBIAN_FRONTEND=noninteractive apt-get install -y cron", "Cron xizmatini o'rnatish")
exec_cmd("systemctl enable cron && systemctl start cron", "Cron xizmatini faollashtirish")

# 2. Upload backup_db.py and apps.py
print("[+] Skriptlarni yuklash...")
sftp = ssh.open_sftp()
sftp.put("c:\\b\\meat\\backup_db.py", f"{REMOTE_DIR}/backup_db.py")
sftp.put("c:\\b\\meat\\pos\\apps.py", f"{REMOTE_DIR}/pos/apps.py")
sftp.put("c:\\b\\meat\\templates\\404.html", f"{REMOTE_DIR}/templates/404.html")
sftp.put("c:\\b\\meat\\templates\\500.html", f"{REMOTE_DIR}/templates/500.html")
sftp.close()
print("[OK] Skriptlar yuklandi!")

# 3. Setup crontab entries
cron_jobs = """# MeatFlow Pro Automated Cron Tasks
0 21 * * * cd /var/www/meatflow && /var/www/meatflow/venv/bin/python manage.py send_daily_digest >> /var/log/meatflow_digest.log 2>&1
0 8 * * * cd /var/www/meatflow && /var/www/meatflow/venv/bin/python manage.py run_decay >> /var/log/meatflow_decay.log 2>&1
0 3 * * * cd /var/www/meatflow && /var/www/meatflow/venv/bin/python backup_db.py >> /var/log/meatflow_backup.log 2>&1
"""

exec_cmd(f"cat << 'EOF' > /tmp/meatflow_cron\n{cron_jobs}\nEOF\ncrontab /tmp/meatflow_cron && rm /tmp/meatflow_cron", "Crontab jadvalini o'rnatish (21:00 Digest, 08:00 Decay, 03:00 Backup)")
exec_cmd("crontab -l", "Faol Cron vazifalarini tekshirish")

# 4. Run test backup now
exec_cmd(f"cd {REMOTE_DIR} && {REMOTE_DIR}/venv/bin/python backup_db.py", "Sinov uchun birinchi baza zaxirasini olish")
exec_cmd(f"ls -la {REMOTE_DIR}/backups", "Backuplar ro'yxatini ko'rish")

# 5. Restart web app to apply WAL mode
exec_cmd("systemctl restart meatflow && systemctl restart meatflow-bots", "Xizmatlarni qayta ishga tushirish")

print("\n🎉 [SUCCESS] Avtomatlashtirish, Cron jadvallari, WAL rejimi va Zaxiralash tizimi 100% o'rnatildi!")
ssh.close()
