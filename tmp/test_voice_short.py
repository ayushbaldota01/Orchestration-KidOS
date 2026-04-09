import pyttsx3

try:
    engine = pyttsx3.init()
    engine.say("Testing voice system.")
    engine.runAndWait()
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
