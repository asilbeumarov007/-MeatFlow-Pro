import os
import sys
import time
import zipfile
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

SERVER_IP = os.environ.get("SERVER_IP", "189.74.96.249")
SERVER_PORT = int(os.environ.get("SERVER_PORT", 22))
SERVER_USER = os.environ.get("SERVER_USER", "root")
SERVER_PASS = os.environ.get("SERVER_PASS", "")
REMOTE_DIR = os.environ.get("REMOTE_DIR", "/var/www/meatflow")


def create_update_archive():
    zip_path = "c:\\b\\meat\\update.zip"
    print(f"📦 Yangilangan kodlarni arxivlash: {zip_path}...")
    
    exclude_dirs = {'.git', '.idea', '__pycache__', 'venv', '.agents', '.system_generated', 'node_modules', 'scratch', 'media', 'staticfiles', 'backups'}
    valid_exts = {'.py', '.html', '.css', '.js', '.jsx', '.json', '.md', '.txt', '.sh', '.bat', '.bin'}
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk("c:\\b\\meat"):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                if any(file.endswith(ext) for ext in valid_exts) and not file.startswith('meatflow_db'):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, "c:\\b\\meat")
                    zipf.write(file_path, arcname)
    
    print("[OK] Arxiv tayyor!")
    return zip_path

def deploy_update():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"[+] Serverga ulanish: {SERVER_IP}...")
    for attempt in range(1, 10):
        try:
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

    # 1. Upload update zip
    zip_path = create_update_archive()
    print("[+] Yangi kodlarni serverga yuklash...")
    sftp = ssh.open_sftp()
    remote_zip = f"{REMOTE_DIR}/update.zip"
    sftp.put(zip_path, remote_zip)
    sftp.close()
    print("[OK] Kodlar yuklandi!")
    
    # 2. Extract update & apply migrations
    exec_cmd(f"cd {REMOTE_DIR} && unzip -o update.zip && rm update.zip", "Yangi kodlarni o'rnatish")
    exec_cmd(f"cd {REMOTE_DIR} && {REMOTE_DIR}/venv/bin/python manage.py migrate", "Baza migratsiyalarini tekshirish")
    exec_cmd(f"cd {REMOTE_DIR} && {REMOTE_DIR}/venv/bin/python manage.py collectstatic --noinput", "Statik fayllarni yangilash")
    
    # 3. Reload services gracefully
    exec_cmd("systemctl restart meatflow && systemctl restart meatflow-bots && systemctl reload nginx", "Web va Bot xizmatlarini yangilash")
    
    # 4. Check status
    exec_cmd("systemctl status meatflow --no-pager -n 3 && systemctl status meatflow-bots --no-pager -n 3", "Xizmatlar holatini tekshirish")
    
    print("\n🎉 [SUCCESS] Barcha yangilanishlar serverga muvaffaqiyatli o'rnatildi!")
    ssh.close()

if __name__ == '__main__':
    deploy_update()
