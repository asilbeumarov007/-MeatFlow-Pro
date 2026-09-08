import paramiko

SERVER_IP = "189.74.96.249"
SERVER_USER = "root"
SERVER_PASS = "UugfwGB0L8D6dAh%"
REMOTE_DIR = "/var/www/meatflow"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_IP, port=22, username=SERVER_USER, password=SERVER_PASS, timeout=20)

commands = [
    # Reset user password in PostgreSQL
    "sudo -u postgres psql -c \"ALTER USER meatflow_user WITH ENCRYPTED PASSWORD 'MeatFlowPass2026!';\"",
    "sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE meatflow_db TO meatflow_user;\"",
    "sudo -u postgres psql -d meatflow_db -c \"GRANT ALL ON SCHEMA public TO meatflow_user;\"",
    # Test psql connection
    "PGPASSWORD='MeatFlowPass2026!' psql -U meatflow_user -h 127.0.0.1 -d meatflow_db -c 'SELECT current_user, current_database();'",
    # Run migrations
    f"cd {REMOTE_DIR} && {REMOTE_DIR}/venv/bin/python manage.py migrate",
    # Run seed
    f"cd {REMOTE_DIR} && {REMOTE_DIR}/venv/bin/python seed_data.py && rm -f seed_data.py",
    # Restart services
    "systemctl restart meatflow && systemctl restart meatflow-bots"
]

for cmd in commands:
    print(f"\n[*] Running: {cmd[:60]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(f"[OUT]: {out}")
    if err:
        print(f"[ERR]: {err}")

ssh.close()
