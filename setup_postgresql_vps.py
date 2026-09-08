import os
import sys
import time
import zipfile
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
DB_NAME = "meatflow_db"
DB_USER = "meatflow_user"
DB_PASS = "MeatFlowPass2026!"

def create_update_archive():
    zip_path = "c:\\b\\meat\\update.zip"
    print(f"📦 Yangilangan kodlarni arxivlash: {zip_path}...")
    
    exclude_dirs = {'.git', '.idea', '__pycache__', 'venv', '.agents', '.system_generated', 'node_modules', 'scratch', 'media', 'staticfiles', 'backups'}
    valid_exts = {'.py', '.html', '.css', '.js', '.json', '.md', '.txt', '.sh', '.bat'}
    
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

def setup_postgresql():
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
            print(f"[LOG]: {err.strip()[:300]}")
        return out

    # 1. Install PostgreSQL & libpq-dev
    exec_cmd("export DEBIAN_FRONTEND=noninteractive; apt-get update -y && apt-get install -y postgresql postgresql-contrib libpq-dev", "PostgreSQL paketlarini o'rnatish")
    exec_cmd("systemctl enable postgresql && systemctl start postgresql", "PostgreSQL xizmatini yoqish")

    # 2. Configure Database & User
    psql_setup_sql = f"""
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{DB_USER}') THEN
        CREATE USER {DB_USER} WITH PASSWORD '{DB_PASS}';
      ELSE
        ALTER USER {DB_USER} WITH PASSWORD '{DB_PASS}';
      END IF;
    END
    $$;
    ALTER USER {DB_USER} CREATEDB;
    DROP DATABASE IF EXISTS {DB_NAME};
    CREATE DATABASE {DB_NAME} OWNER {DB_USER};
    GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER};
    """
    exec_cmd(f'sudo -u postgres psql -c "{psql_setup_sql}"', "PostgreSQL baza va foydalanuvchisini yaratish")

    # 3. Create .env on server
    env_content = f"""DB_NAME={DB_NAME}
DB_USER={DB_USER}
DB_PASSWORD={DB_PASS}
DB_HOST=127.0.0.1
DB_PORT=5432
"""
    sftp = ssh.open_sftp()
    with sftp.file(f"{REMOTE_DIR}/.env", "w") as f:
        f.write(env_content)
    print("[OK] .env konfiguratsiyasi PostgreSQL uchun saqlandi!")

    # 4. Upload update.zip
    zip_path = create_update_archive()
    remote_zip = f"{REMOTE_DIR}/update.zip"
    sftp.put(zip_path, remote_zip)
    sftp.close()
    print("[OK] Yangi kodlar serverga yuklandi!")

    # 5. Extract & Install psycopg2-binary
    exec_cmd(f"cd {REMOTE_DIR} && unzip -o update.zip && rm update.zip", "Yangi kodlarni ochish")
    exec_cmd(f"{REMOTE_DIR}/venv/bin/pip install psycopg2-binary openpyxl", "PostgreSQL drayverini (psycopg2) o'rnatish")

    # 6. Apply Migrations to PostgreSQL
    exec_cmd(f"cd {REMOTE_DIR} && {REMOTE_DIR}/venv/bin/python manage.py makemigrations", "Django migratsiyalarni tayyorlash")
    exec_cmd(f"cd {REMOTE_DIR} && {REMOTE_DIR}/venv/bin/python manage.py migrate", "PostgreSQL bazasiga jadvallarni qurish")

    # 7. Seed Clean Data (Store Settings, Admin & Default Products)
    seed_script = """
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from pos.models import StoreSetting, Product, Stock
from decimal import Decimal

User = get_user_model()

# 1. Admin user
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@baxmalmeat.uz', 'admin12345')
    print('Superuser [admin] yaratildi (parol: admin12345)')

if not User.objects.filter(username='guljahon').exists():
    User.objects.create_superuser('guljahon', 'guljahon@baxmalmeat.uz', 'guljahon2026')
    print('Superuser [guljahon] yaratildi (parol: guljahon2026)')

# 2. Store Setting
store, created = StoreSetting.objects.get_or_create(
    id=1,
    defaults={
        'name': "Baxmal Meat Do'koni",
        'phone_number': "+998 77 082 4477",
        'address': "Toshkent shahri, Chilonzor tumani",
        'announcement_text': "🔥 Mol va Qo'y go'shtidan buyurtma bering — Toshkent bo'ylab yetkazib berish va halol kafolat!",
        'hero_title': "Sarxil Go'sht & Raqamli MeatFlow Pro Texnologiyasi",
        'hero_subtitle': "Baxmal Meat — Fermadan dasturxongacha laboratoriya nazorati, IoT smart tarozilar, shaffof hisob-kitob va tezkor kuryerlik xizmati.",
        'promo_banner_text': "500,000 so'mdan yuqori buyurtmalar uchun Toshkent shahri bo'ylab yetkazib berish BEPUL!",
        'latitude': 41.2995,
        'longitude': 69.2401,
        'base_delivery_fee': Decimal('10000.00'),
        'fee_per_km': Decimal('3000.00'),
        'min_free_delivery_amount': Decimal('500000.00'),
        'cashback_percent': Decimal('2.00'),
        'is_active': True
    }
)
if created:
    print("StoreSetting yaratildi")

# 3. Clean Standard Products
sample_products = [
    ("Mol Lahm Go'shti (Saralangan)", Decimal("85000.00"), Decimal("50.000")),
    ("Mermer Mol Steak (Ribeye)", Decimal("95000.00"), Decimal("30.000")),
    ("Baxmal Qo'y Qovurg'asi", Decimal("80000.00"), Decimal("40.000")),
    ("Qo'y Lahm Go'shti", Decimal("85000.00"), Decimal("35.000")),
    ("Qiyma Go'sht (Yog'siz)", Decimal("80000.00"), Decimal("25.000")),
    ("Dumg'aza", Decimal("70000.00"), Decimal("20.000")),
    ("Saralangan Jigar & Yurak", Decimal("50000.00"), Decimal("15.000")),
]

for name, price, qty in sample_products:
    p, _ = Product.objects.get_or_create(name=name, defaults={'price_per_kg': price, 'is_active': True})
    s, _ = Stock.objects.get_or_create(product=p, defaults={'quantity': qty})
    s.quantity = qty
    s.save()

print('Initial mahsulotlar va zaxiralar PostgreSQL bazasiga yuklandi!')
"""
    exec_cmd(f"cd {REMOTE_DIR} && {REMOTE_DIR}/venv/bin/python -c \"{seed_script}\"", "PostgreSQL-ga toza boshlang'ich ma'lumotlarni kiritish")

    # 8. Collectstatic
    exec_cmd(f"cd {REMOTE_DIR} && {REMOTE_DIR}/venv/bin/python manage.py collectstatic --noinput", "Statik fayllarni to'plash")

    # 9. Setup Crontab for Daily 03:00 Telegram Backup
    cron_cmd = f'(crontab -l 2>/dev/null | grep -v "run_daily_backup"; echo "0 3 * * * cd {REMOTE_DIR} && {REMOTE_DIR}/venv/bin/python manage.py run_daily_backup >> /var/log/meatflow_backup.log 2>&1") | crontab -'
    exec_cmd(cron_cmd, "Har kuni 03:00 da Telegramga avtomatik zaxira yuborish rejasini (Cron) o'rnatish")

    # 10. Restart services
    exec_cmd("systemctl restart meatflow && systemctl restart meatflow-bots && systemctl reload nginx", "Web va Bot xizmatlarini qayta ishga tushirish")
    exec_cmd("systemctl status meatflow --no-pager -n 3 && systemctl status meatflow-bots --no-pager -n 3", "Xizmatlar holatini tekshirish")

    print("\n🎉 [MUVAFFAQIYATLI] MeatFlow Pro to'liq PostgreSQL bazasiga o'tkazildi va avtomatik zaxira tizimi ishga tushirildi!")
    ssh.close()

if __name__ == '__main__':
    setup_postgresql()
