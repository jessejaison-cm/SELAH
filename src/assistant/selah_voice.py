import speech_recognition as sr
import pyttsx3
from datetime import datetime

# Import SELAH brain
from selah_brain import handle_command

# ----------------------------
# Initialize voice engine
# ----------------------------
engine = pyttsx3.init()
engine.setProperty('rate', 170)

def speak(text):
    engine.say(text)
    engine.runAndWait()

# ----------------------------
# Listen from microphone
# ----------------------------
def listen():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤 SELAH is listening...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        command = recognizer.recognize_google(audio)
        print("🗣️ You:", command)
        return command.lower()
    except sr.UnknownValueError:
        speak("Sorry, I did not understand that.")
        return ""
    except sr.RequestError:
        speak("Speech service is unavailable.")
        return ""

# ----------------------------
# Process user commands
# ----------------------------
def process_command(command):
    if "stop" in command or "exit" in command or "bye" in command:
        speak("Goodbye. I will be here when you need me.")
        print("🤖 SELAH: Shutting down.")
        exit()
    else:
        handle_command(command)

# ----------------------------
# Main Loop
# ----------------------------
if __name__ == "__main__":
    speak("SELAH online. Memory and intelligence activated.")

    while True:
        user_command = listen()
        if user_command:
            process_command(user_command)
