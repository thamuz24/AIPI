import pickle
from pathlib import Path

import cv2

try:
    from .face_encoder import FaceEncoder
except ImportError:
    from face_encoder import FaceEncoder


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "face_db.pkl"

encoder = FaceEncoder()
cap = cv2.VideoCapture(0)

print("Nhan SPACE de dang ky khuon mat")

while True:
    ret, frame = cap.read()
    if not ret or frame is None:
        continue

    cv2.imshow("Dang ky khuon mat", frame)
    key = cv2.waitKey(1)

    if key == 32:  # SPACE
        emb = encoder.get_embedding(frame)

        if emb is not None:
            with DB_PATH.open("wb") as f:
                pickle.dump(emb, f)

            print("Dang ky khuon mat thanh cong")
            break

        print("Khong tim thay khuon mat")

    if key == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()
