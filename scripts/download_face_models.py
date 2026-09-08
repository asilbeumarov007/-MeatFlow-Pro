import os
import requests

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'public', 'models')
STATIC_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'models')

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(STATIC_MODEL_DIR, exist_ok=True)

BASE_URL = "https://raw.githubusercontent.com/vladmandic/face-api/master/model/"

FILES = [
    "tiny_face_detector_model-weights_manifest.json",
    "tiny_face_detector_model-shard1",
    "face_landmark_68_model-weights_manifest.json",
    "face_landmark_68_model-shard1",
    "face_recognition_model-weights_manifest.json",
    "face_recognition_model-shard1",
    "face_recognition_model-shard2"
]

print(f"Downloading face-api models to {MODEL_DIR} and {STATIC_MODEL_DIR}...")
for f in FILES:
    url = BASE_URL + f
    dest1 = os.path.join(MODEL_DIR, f)
    dest2 = os.path.join(STATIC_MODEL_DIR, f)
    
    if os.path.exists(dest1) and os.path.getsize(dest1) > 0:
        print(f"Already exists: {f}")
        continue
        
    print(f"Fetching {f}...")
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        with open(dest1, 'wb') as fp:
            fp.write(r.content)
        with open(dest2, 'wb') as fp:
            fp.write(r.content)
        print(f"Saved {f} ({len(r.content)} bytes)")
    except Exception as e:
        print(f"Error fetching {f}: {e}")

print("Done downloading models!")
