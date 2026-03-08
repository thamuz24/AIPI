from speech.vosk_recognizer import VoiceRecognizer


def handle_prompt(text):
    print("You said:", text)


def main():
    recognizer = VoiceRecognizer("model")
    recognizer.listen_forever(on_prompt=handle_prompt)


if __name__ == "__main__":
    main()
