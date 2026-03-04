import torch
import cv2
import numpy as np
from facenet_pytorch import MTCNN, InceptionResnetV1


class FaceEncoder:
    def __init__(self):
        self.device = 'cpu'

        # Nhận diện khuôn mặt
        self.mtcnn = MTCNN(keep_all=False, device=self.device)

        # chuyển đổi thành vector
        self.resnet = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)

    def get_embedding(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        face = self.mtcnn(rgb)

        if face is None:
            return None

        face = face.unsqueeze(0).to(self.device)

        embedding = self.resnet(face).detach().cpu().numpy()[0]

        return embedding