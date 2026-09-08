import paramiko

SERVER_IP = "189.74.96.249"
SERVER_USER = "root"
SERVER_PASS = "UugfwGB0L8D6dAh%"
REMOTE_DIR = "/var/www/meatflow"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_IP, port=22, username=SERVER_USER, password=SERVER_PASS, timeout=20)

env_content = """DB_NAME=meatflow_db
DB_USER=meatflow_user
DB_PASSWORD=MeatFlowPass2026!
DB_HOST=127.0.0.1
DB_PORT=5432
TELEGRAM_BOT_TOKEN=8898055369:AAFbUW9nLVRXwG-xd0oP1ftQ5vZpTjcL4x8
CUSTOMER_BOT_TOKEN=8740627731:AAEtdO4x7eni9jmUPfnbQB3rb-qk2B87t3U
TELEGRAM_CHAT_ID=-1004312267841
SITE_URL=https://baxmalmeat.uz
"""

sftp = ssh.open_sftp()
with sftp.file(f"{REMOTE_DIR}/.env", "w") as f:
    f.write(env_content)
sftp.close()

# Test run daily backup
stdin, stdout, stderr = ssh.exec_command(f"cd {REMOTE_DIR} && {REMOTE_DIR}/venv/bin/python manage.py run_daily_backup")
print("[BACKUP TEST]:", stdout.read().decode())
print("[BACKUP ERR]:", stderr.read().decode())

# Restart services
ssh.exec_command("systemctl restart meatflow && systemctl restart meatflow-bots")
print("[OK] Services restarted!")

ssh.close()
