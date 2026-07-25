import serial
import requests
import time
import re

# === SOZLAMALAR ===
SERIAL_PORT = 'COM5'  # Sening tarozing ulangan port
BAUD_RATE = 115200  # NodeMCU tezligi
# tarozi_bridge.py ichida:
DJANGO_URL = 'http://127.0.0.1:8000/pos/api/receive-weight/'

print("==================================================")
print("       BAXMAL MEAT: WI-FI TAROZI KO'PRIK v1.0     ")
print("==================================================")

# Serial portni ochishga urinish
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"[OK] {SERIAL_PORT} porti muvaffaqiyatli ochildi.")
    print("Tarozidan tugma bosilishini kutmoqdaman...\n")
except Exception as e:
    print(f"[XATO] {SERIAL_PORT} portiga ulanib bo'lmadi!")
    print(f"Sababi: {e}")
    print("NodeMCU kompyuterga ulanganmi va port nomi to'g'rimi? Tekshiring.")
    exit()

# Portni doimiy eshitib turish (Loop)
while True:
    try:
        if ser.in_waiting > 0:
            # Serial portdan kelgan ma'lumot qatorini o'qiymiz
            line = ser.readline().decode('utf-8', errors='ignore').strip()

            # Agar datchikdan vazn haqida ma'lumot kelsa
            if "VAZN:" in line:
                print(f"[NodeMCU dan keldi]: {line}")

                # "VAZN:0.987 kg" ichidan faqat 0.987 raqamini ajratib olamiz
                match = re.search(r"VAZN:([\d\.-]+)", line)
                if match:
                    toza_vazn = match.group(1)

                    # Django saytingga JSON formatda POST so'rov yuboramiz
                    # tarozi_bridge.py ichidagi payload qismini top va shunday yoz:
                    payload = {
                        'vazn': toza_vazn,
                        'scale_id': '2',  # 2-tarozi ekanligini djangoga bildiramiz
                        'button_pressed': True  # Tugma bosilgan deb hisoblaydi
                    }
                    headers = {'Content-Type': 'application/json'}

                    try:
                        response = requests.post(DJANGO_URL, json=payload, headers=headers)
                        if response.status_code == 200:
                            print(f"--> [OK] {toza_vazn} kg Django saytga muvaffaqiyatli uzatildi! ✅\n")
                        else:
                            print(f"--> [XATO] Sayt qabul qilmadi. Status kod: {response.status_code}\n")
                    except requests.exceptions.ConnectionError:
                        print("--> [XATO] Django sayt o'chiq! Avval Djangoni (runserver) ishga tushiring.\n")

    except KeyboardInterrupt:
        print("\nDastur foydalanuvchi tomonidan to'xtatildi.")
        ser.close()
        break
    except Exception as e:
        print(f"Kutilmagan xatolik yuz berdi: {e}")
        time.sleep(1)