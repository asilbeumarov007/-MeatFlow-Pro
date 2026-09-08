import os
import sys
import time
import zipfile
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SERVER_IP = os.environ.get("SERVER_IP", "189.74.96.249")
SERVER_PORT = int(os.environ.get("SERVER_PORT", 22))
SERVER_USER = os.environ.get("SERVER_USER", "root")
SERVER_PASS = os.environ.get("SERVER_PASS", "")
REMOTE_DIR = os.environ.get("REMOTE_DIR", "/var/www/meatflow")


def create_archive():
    zip_path = "c:\\b\\meat\\project.zip"
    print(f"[+] Loyiha fayllarini arxivlash: {zip_path}...")
    exclude_dirs = {'.git', '.idea', '__pycache__', 'venv', '.agents', '.system_generated', 'node_modules', 'scratch'}
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk("c:\\b\\meat"):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                if file.endswith('.zip') or file.endswith('.log') or file.startswith('.env.bak'):
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, "c:\\b\\meat")
                zipf.write(file_path, arcname)
    
    print("[OK] Arxiv tayyor!")
    return zip_path

def run_remote():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"[+] Serverga ulanish: {SERVER_IP}...")
    ssh.connect(SERVER_IP, port=SERVER_PORT, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    print("[OK] SSH ulanish muvaffaqiyatli!")
    
    def exec_cmd(cmd, desc=""):
        if desc:
            print(f"\n[*] {desc}...")
        print(f"   [CMD]: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode('utf-8', errors='ignore')
        err = stderr.read().decode('utf-8', errors='ignore')
        if out:
            print(out.strip())
        if err and "warning" not in err.lower() and "notice" not in err.lower() and "debconf" not in err.lower():
            print(f"   [ERR]: {err.strip()}")
        return out

    # 1. Update OS & install dependencies
    exec_cmd("DEBIAN_FRONTEND=noninteractive apt update -y && DEBIAN_FRONTEND=noninteractive apt install -y python3-pip python3-venv python3-dev nginx unzip ufw curl", "Linux tizimini va kerakli dasturlarni (Nginx, Python, Unzip) yangilash")
    
    # 2. Setup project directory
    exec_cmd(f"mkdir -p {REMOTE_DIR}", "Loyiha papkasini yaratish")
    
    # 3. SFTP Upload
    zip_path = create_archive()
    print("[+] Arxivni serverga yuklash (SFTP)...")
    sftp = ssh.open_sftp()
    remote_zip = f"{REMOTE_DIR}/project.zip"
    sftp.put(zip_path, remote_zip)
    sftp.close()
    print("[OK] Fayllar serverga muvaffaqiyatli yuklandi!")
    
    # 4. Unzip project
    exec_cmd(f"cd {REMOTE_DIR} && unzip -o project.zip && rm project.zip", "Fayllarni serverda ochish")
    
    # 5. Create VirtualEnv & Install requirements
    exec_cmd(f"python3 -m venv {REMOTE_DIR}/venv", "Python virtual muhitini (venv) yaratish")
    exec_cmd(f"{REMOTE_DIR}/venv/bin/pip install --upgrade pip && {REMOTE_DIR}/venv/bin/pip install -r {REMOTE_DIR}/requirements.txt gunicorn", "Python kutubxonalari va Gunicorn o'rnatish")
    
    # 6. Django Migrations & Collectstatic
    exec_cmd(f"cd {REMOTE_DIR} && {REMOTE_DIR}/venv/bin/python manage.py migrate", "Ma'lumotlar bazasini yangilash (migrate)")
    exec_cmd(f"cd {REMOTE_DIR} && {REMOTE_DIR}/venv/bin/python manage.py collectstatic --noinput", "Statik fayllarni to'plash (collectstatic)")
    
    # 7. Create Gunicorn Service
    gunicorn_service = f"""[Unit]
Description=MeatFlow Pro Django Web App
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory={REMOTE_DIR}
ExecStart={REMOTE_DIR}/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 config.wsgi:application
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
    exec_cmd(f"cat << 'EOF' > /etc/systemd/system/meatflow.service\n{gunicorn_service}\nEOF", "Gunicorn xizmatini yaratish (meatflow.service)")
    
    # 8. Create Telegram Bots Service
    bots_service = f"""[Unit]
Description=MeatFlow Pro Telegram Bots (Admin & Customer + Voice AI)
After=network.target

[Service]
User=root
WorkingDirectory={REMOTE_DIR}
ExecStart={REMOTE_DIR}/venv/bin/python manage.py run_all_bots
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    exec_cmd(f"cat << 'EOF' > /etc/systemd/system/meatflow-bots.service\n{bots_service}\nEOF", "Telegram Botlar xizmatini yaratish (meatflow-bots.service)")

    # 9. Configure Nginx
    nginx_conf = f"""server {{
    listen 80;
    server_name baxmalmeat.uz www.baxmalmeat.uz 189.74.96.249;

    client_max_body_size 50M;

    location = /favicon.ico {{ access_log off; log_not_found off; }}
    
    location /static/ {{
        alias {REMOTE_DIR}/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }}

    location /media/ {{
        alias {REMOTE_DIR}/media/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }}

    location / {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
    exec_cmd(f"cat << 'EOF' > /etc/nginx/sites-available/meatflow\n{nginx_conf}\nEOF", "Nginx veb-serverini sozlash")
    exec_cmd("ln -sf /etc/nginx/sites-available/meatflow /etc/nginx/sites-enabled/ && rm -f /etc/nginx/sites-enabled/default", "Nginx saytini faollashtirish")
    exec_cmd("nginx -t", "Nginx sozlamalarini tekshirish")
    
    # 10. Enable and restart all services
    exec_cmd("systemctl daemon-reload", "Systemd xizmatlarini qayta yuklash")
    exec_cmd("systemctl enable meatflow && systemctl restart meatflow", "Veb-ilovasini ishga tushirish")
    exec_cmd("systemctl enable meatflow-bots && systemctl restart meatflow-bots", "Telegram Botlarni ishga tushirish")
    exec_cmd("systemctl restart nginx", "Nginx ni qayta ishga tushirish")
    
    # 11. Check statuses
    exec_cmd("systemctl status meatflow --no-pager -n 5", "Veb-ilova holatini tekshirish")
    exec_cmd("systemctl status meatflow-bots --no-pager -n 5", "Botlar holatini tekshirish")
    
    # 12. Setup firewall
    exec_cmd("ufw allow 'Nginx Full' && ufw allow OpenSSH && echo 'y' | ufw enable", "Xavfsizlik devori (Firewall) ni yoqish")
    
    print("\n[SUCCESS] MeatFlow Pro serverga to'liq o'rnatildi va 24/7 rejimda ishga tushirildi!")
    ssh.close()


if __name__ == '__main__':
    run_remote()
