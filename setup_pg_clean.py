import paramiko

SERVER_IP = "189.74.96.249"
SERVER_USER = "root"
SERVER_PASS = "UugfwGB0L8D6dAh%"
REMOTE_DIR = "/var/www/meatflow"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_IP, port=22, username=SERVER_USER, password=SERVER_PASS, timeout=20)

commands = [
    # 1. Create role and database from /tmp (no /root perm issue)
    "cd /tmp && sudo -u postgres psql -c \"DROP DATABASE IF EXISTS meatflow_db;\"",
    "cd /tmp && sudo -u postgres psql -c \"DROP USER IF EXISTS meatflow_user;\"",
    "cd /tmp && sudo -u postgres psql -c \"CREATE USER meatflow_user WITH ENCRYPTED PASSWORD 'MeatFlowPass2026!';\"",
    "cd /tmp && sudo -u postgres psql -c \"CREATE DATABASE meatflow_db OWNER meatflow_user;\"",
    "cd /tmp && sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE meatflow_db TO meatflow_user;\"",
    "cd /tmp && sudo -u postgres psql -d meatflow_db -c \"GRANT ALL ON SCHEMA public TO meatflow_user;\"",
    
    # 2. Test PostgreSQL direct login
    "PGPASSWORD='MeatFlowPass2026!' psql -U meatflow_user -h 127.0.0.1 -d meatflow_db -c 'SELECT current_user, current_database();'",
    
    # 3. Write .env
    f"echo 'DB_NAME=meatflow_db\nDB_USER=meatflow_user\nDB_PASSWORD=MeatFlowPass2026!\nDB_HOST=127.0.0.1\nDB_PORT=5432' > {REMOTE_DIR}/.env",
    
    # 4. Migrate database
    f"cd {REMOTE_DIR} && {REMOTE_DIR}/venv/bin/python manage.py makemigrations",
    f"cd {REMOTE_DIR} && {REMOTE_DIR}/venv/bin/python manage.py migrate",
]

for cmd in commands:
    print(f"\n[*] Running: {cmd[:60]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(f"[OUT]: {out}")
    if err and "warning" not in err.lower() and "notice" not in err.lower():
        print(f"[ERR]: {err}")

# 5. Create Seed Data
seed_code = """
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from pos.models import StoreSetting, Product, Stock
from decimal import Decimal

User = get_user_model()

# 1. Admin Users
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@baxmalmeat.uz', 'admin12345')
    print('Superuser [admin] yaratildi')

if not User.objects.filter(username='guljahon').exists():
    User.objects.create_superuser('guljahon', 'guljahon@baxmalmeat.uz', 'guljahon2026')
    print('Superuser [guljahon] yaratildi')

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

# 3. Clean Products
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

print('Initial mahsulotlar va zaxiralar PostgreSQL bazasiga muvaffaqiyatli saqlandi!')
"""

sftp = ssh.open_sftp()
with sftp.file(f"{REMOTE_DIR}/seed_clean.py", "w") as f:
    f.write(seed_code)
sftp.close()

stdin, stdout, stderr = ssh.exec_command(f"cd {REMOTE_DIR} && {REMOTE_DIR}/venv/bin/python seed_clean.py && rm -f seed_clean.py")
print("\n[SEED]:", stdout.read().decode())
print("[SEED ERR]:", stderr.read().decode())

# 6. Restart Services
ssh.exec_command("systemctl restart meatflow && systemctl restart meatflow-bots && systemctl reload nginx")
print("[OK] Web va Bot xizmatlari qayta ishga tushirildi!")

ssh.close()
