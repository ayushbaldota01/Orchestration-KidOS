import pyttsx3
import time

print("Initializing engine...")
try:
    engine = pyttsx3.init()
    print("Engine initialized.")
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 0.9)
    print("Property set.")
    
    text = "Hello, this is a test of the KidOS voice system. If you hear this, then your local text to speech is working correctly."
    print(f"Saying: {text}")
    engine.say(text)
    print("Running and waiting...")
    engine.runAndWait()
    print("Done.")
except Exception as e:
    print(f"FAILED: {e}")
