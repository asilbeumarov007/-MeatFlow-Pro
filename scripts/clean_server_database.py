import os
import sys
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

print("=" * 60)
print("SERVERDAGI BAZANI TOZALASH (FAQAT MIJOZLAR SAQLANADI)")
print("=" * 60)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_IP, port=SERVER_PORT, username=SERVER_USER, password=SERVER_PASS, timeout=30)

# 1. Upload the cleaner script to the server
sftp = ssh.open_sftp()
sftp.put(r"c:\b\meat\scripts\clean_database_keep_customers.py", f"{REMOTE_DIR}/clean_database.py")
sftp.close()

# 2. Execute cleaner script on server
cmd = f"cd {REMOTE_DIR} && {REMOTE_DIR}/venv/bin/python clean_database.py && rm clean_database.py"
stdin, stdout, stderr = ssh.exec_command(cmd)
out = stdout.read().decode('utf-8', errors='ignore')
err = stderr.read().decode('utf-8', errors='ignore')

if out:
    print(out)
if err and "warning" not in err.lower() and "notice" not in err.lower():
    print(f"[ERR]: {err}")

# 3. Restart services
ssh.exec_command("systemctl restart meatflow && systemctl restart meatflow-bots")
ssh.close()
print("=" * 60)
print("[OK] Serverdagi baza muvaffaqiyatli tozalandi!")
print("=" * 60)
