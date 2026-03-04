import queue
import sounddevice as sd
import json
from vosk import Model, KaldiRecognizer

class VoiceRecognizer:
    def __init__(self, model_path="model"):
        self.model = Model(model_path)

        self.q = queue.Queue()
        self.rec = KaldiRecognizer(self.model, 16000)

    def callback(self,indata, frames, time, status):
        self.q.put(bytes(indata))

    def listen(self):
        with sd.RawInputStream(
                samplerate=16000,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=self.callback):

            print("Đang lắng nghe...")

            while True:
                data = self.q.get()

                if self.rec.AcceptWaveform(data):
                    result = json.loads(self.rec.Result())
                    text = result.get("text", "")
                    return text