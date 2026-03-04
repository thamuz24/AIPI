import pickle
from pathlib import Path

import cv2
import numpy as np

try:
    from .face_encoder import FaceEncoder
except ImportError:
    from face_encoder import FaceEncoder


THRESHOLD = 0.8
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "face_db.pkl"

if not DB_PATH.exists():
    raise FileNotFoundError(f"Khong tim thay du lieu khuon mat: {DB_PATH}")

encoder = FaceEncoder()
with DB_PATH.open("rb") as f:
    stored_embedding = pickle.load(f)

cap = cv2.VideoCapture(0)
print("Tim kiem khuon mat...")

while True:
    ret, frame = cap.read()
    if not ret or frame is None:
        continue

    emb = encoder.get_embedding(frame)
    if emb is not None:
        dist = np.linalg.norm(stored_embedding - emb)
        if dist < THRESHOLD:
            print("Mo khoa thanh cong")
            break

    cv2.imshow("Auth", frame)
    if cv2.waitKey(1) == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()
