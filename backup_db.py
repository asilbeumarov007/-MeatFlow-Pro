import os
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
DB_FILE = os.path.join(BASE_DIR, 'db.sqlite3')

os.makedirs(BACKUP_DIR, exist_ok=True)

today_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
backup_target = os.path.join(BACKUP_DIR, f'meatflow_db_{today_str}.sqlite3')

if os.path.exists(DB_FILE):
    shutil.copy2(DB_FILE, backup_target)
    print(f"[OK] Database backed up successfully: {backup_target}")

# 30 kundan eski backuplarni tozalash (disk to'lib ketmasligi uchun)
now = datetime.now().timestamp()
for f in os.listdir(BACKUP_DIR):
    f_path = os.path.join(BACKUP_DIR, f)
    if os.path.isfile(f_path) and (now - os.path.getmtime(f_path)) > (30 * 86400):
        os.remove(f_path)
        print(f"[CLEANUP] Removed old backup: {f}")
