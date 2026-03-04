from speech.vosk_recognizer import VoiceRecognizer

def main():
    recognizer = VoiceRecognizer("model")

    while True:
        command = recognizer.listen()

        if command:
            print("You said:", command)

if __name__ == "__main__":
    main()