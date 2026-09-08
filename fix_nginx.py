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

nginx_conf = """server {
    listen 80;
    listen [::]:80;
    server_name baxmalmeat.uz www.baxmalmeat.uz 189.74.96.249;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name baxmalmeat.uz www.baxmalmeat.uz 189.74.96.249;

    ssl_certificate /etc/letsencrypt/live/baxmalmeat.uz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/baxmalmeat.uz/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    client_max_body_size 50M;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        alias /var/www/meatflow/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location /media/ {
        alias /var/www/meatflow/media/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
"""

stdin, stdout, stderr = ssh.exec_command(f"cat << 'EOF' > /etc/nginx/sites-available/meatflow\n{nginx_conf}\nEOF\nnginx -t && systemctl reload nginx")
print(stdout.read().decode('utf-8'))
print(stderr.read().decode('utf-8'))
print("[OK] Nginx reloaded successfully!")
ssh.close()
