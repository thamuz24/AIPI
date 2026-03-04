import json
import queue
import unicodedata
from typing import Callable, Optional

import sounddevice as sd
from vosk import KaldiRecognizer, Model


class VoiceRecognizer:
    def __init__(self, model_path="model", sample_rate=16000, block_size=8000):
        self.model = Model(model_path)
        self.q = queue.Queue()
        self.rec = KaldiRecognizer(self.model, sample_rate)
        self.sample_rate = sample_rate
        self.block_size = block_size

        self.start_phrases = (
            "khoi dong nhap giong noi",
            "bat dau nhap giong noi",
            "khoi dong giong noi",
        )
        self.stop_phrases = (
            "ket thuc giong noi",
            "dung nhap giong noi",
            "tat giong noi",
        )

    def callback(self, indata, frames, time, status):
        self.q.put(bytes(indata))

    @staticmethod
    def _normalize_text(text):
        normalized = unicodedata.normalize("NFD", text.lower())
        normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
        return " ".join(normalized.split())

    def _is_start_command(self, normalized_text):
        return any(phrase in normalized_text for phrase in self.start_phrases)

    def _is_stop_command(self, normalized_text):
        return any(phrase in normalized_text for phrase in self.stop_phrases)

    def _iter_transcripts(self):
        with sd.RawInputStream(
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            dtype="int16",
            channels=1,
            callback=self.callback,
        ):
            print("Dang lang nghe...")

            while True:
                data = self.q.get()
                if self.rec.AcceptWaveform(data):
                    result = json.loads(self.rec.Result())
                    text = result.get("text", "").strip()
                    if text:
                        yield text

    def listen(self):
        for text in self._iter_transcripts():
            return text
        return ""

    def listen_forever(self, on_prompt: Optional[Callable[[str], None]] = None):
        is_listening_prompt = False
        print("Che do voice control dang bat.")
        print("Noi 'khoi dong nhap giong noi' de bat nhan prompt.")
        print("Noi 'ket thuc giong noi' de tat nhan prompt.")

        for text in self._iter_transcripts():
            normalized = self._normalize_text(text)

            if self._is_start_command(normalized):
                if not is_listening_prompt:
                    is_listening_prompt = True
                    print("Da bat nhan prompt bang giong noi.")
                continue

            if self._is_stop_command(normalized):
                if is_listening_prompt:
                    is_listening_prompt = False
                    print("Da tat nhan prompt bang giong noi.")
                continue

            if is_listening_prompt:
                if on_prompt:
                    on_prompt(text)
                else:
                    print(f"Prompt: {text}")
