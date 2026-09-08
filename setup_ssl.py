import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import time

SERVER_IP = "189.74.96.249"
SERVER_PORT = 22
SERVER_USER = "root"
SERVER_PASS = "UugfwGB0L8D6dAh%"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

for attempt in range(1, 10):
    try:
        print(f"[+] Ulanish urinishi {attempt}/10...")
        ssh.connect(SERVER_IP, port=SERVER_PORT, username=SERVER_USER, password=SERVER_PASS, timeout=30, banner_timeout=60)
        print("[OK] Serverga muvaffaqiyatli ulandi!")
        break
    except Exception as e:
        print(f"[-] Kutish (10s) sabab: {e}")
        time.sleep(10)


def exec_cmd(cmd, desc=""):
    print(f"\n[*] {desc}...")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    if out:
        print(out.strip())
    if err and "warning" not in err.lower() and "notice" not in err.lower():
        print(f"[ERR]: {err.strip()}")
    return out

exec_cmd("DEBIAN_FRONTEND=noninteractive apt-get update -y && DEBIAN_FRONTEND=noninteractive apt-get install -y certbot python3-certbot-nginx", "Installing Certbot and Nginx plugin")
exec_cmd("certbot --nginx -d baxmalmeat.uz -d www.baxmalmeat.uz --non-interactive --agree-tos -m asilbeumarov007@gmail.com --redirect", "Issuing SSL Certificate for baxmalmeat.uz")
exec_cmd("systemctl reload nginx", "Reloading Nginx with SSL")
exec_cmd("curl -I https://baxmalmeat.uz", "Testing HTTPS connection")

print("\n[SUCCESS] SSL Setup Completed!")
ssh.close()
