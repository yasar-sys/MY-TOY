import threading
import time
import re
import os
import subprocess
import socket
import requests
import json
import webbrowser
from datetime import datetime
import tkinter as tk
import pywhatkit  # Add this import at the top with other imports
import random  # At the top
import psutil  # At the top (pip install psutil)

# Attempt to import optional packages for full functionality
try:
    import speech_recognition as sr
    import pyttsx3
    import pyautogui
    import pyperclip
    from youtubesearchpython import VideosSearch
except ImportError as e:
    print(f"Warning: A required package is not installed. {e}")
    print(
        "Please run 'pip install SpeechRecognition pyttsx3 pyautogui pyperclip youtube-search-python' for full functionality.")
    # Exit if core components are missing
    if 'pyttsx3' in str(e) or 'SpeechRecognition' in str(e):
        exit()

# ========== CONFIGURATION ==========
API_KEY = os.environ.get("OPENROUTER_API_KEY", "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")
API_URL = "https://openrouter.ai/api/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://your-site-or-project.com",  # Replace with your actual site
    "X-Title": "Jarvis Assistant"
}

# --- Command Definitions ---
WAKE_WORDS = ["jarvis", "জারভিস"]
EXIT_COMMANDS = ["exit", "quit", "stop", "bye", "বন্ধ কর"]
SHUTDOWN_COMMANDS = ["shutdown", "turn off"]
OPEN_APP_COMMANDS = ["open", "launch", "start"]
SEARCH_COMMANDS = ["search", "google", "look up"]
PLAY_COMMANDS = ["play", "stream"]
NOTE_COMMANDS = ["note", "make a note", "remember this"]

JOKES = [
    "Why did the computer show up at work late? It had a hard drive.",
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "Why did the programmer quit his job? Because he didn't get arrays."
]

# ========== CORE FUNCTIONS ==========

# Initialize speech engine safely
try:
    engine = pyttsx3.init()
    engine.setProperty("rate", 180)
    recognizer = sr.Recognizer()
except Exception as e:
    print(f"Could not initialize speech engine: {e}. Voice features will be disabled.")
    engine = None
    recognizer = None


def speak(text, face):
    """Convert text to speech and print to console, animating the face."""
    print(f"Jarvis: {text}")
    if engine and face:
        face.is_talking = True  # Signal the face to start talking animation
        engine.say(text)
        engine.runAndWait()
        face.is_talking = False  # Signal the face to stop
    else:  # Fallback if no engine or face
        print("Speech engine not available.")


def listen(timeout=7):
    """Listen for voice commands with error handling."""
    if not recognizer:
        print("Listening disabled. Please type your command:")
        return input("> ").lower()

    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("🎤 Listening...")
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=8)
            query = recognizer.recognize_google(audio, language="en-US")
            print(f"You said: {query}")
            return query.lower()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        print(f"Could not request results; {e}")
        return ""
    except Exception as e:
        print(f"An error occurred during listening: {e}")
        return ""


def check_internet():
    """Check internet connectivity."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False


def clean_response(text):
    """Clean up AI response text by removing markdown and extra spaces."""
    text = re.sub(r'[*_`~#>\[\]{}|]', '', text)
    return ' '.join(text.split())


def chat_with_ai(prompt, face=None):
    """Communicate with AI, updating face expression if provided."""
    models_to_try = [
        "openai/gpt-3.5-turbo",
        "mistralai/mistral-7b-instruct",
        "google/gemini-pro",
        "meta-llama/llama-3-70b-instruct"
    ]

    if face:
        face.update_expression("processing")

    for model in models_to_try:
        try:
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are Jarvis, an intelligent AI assistant. Respond helpfully."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }

            response = requests.post(API_URL, headers=HEADERS, json=data, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if "choices" in result and result["choices"]:
                    raw_answer = result["choices"][0]["message"]["content"]
                    print("🧠 AI Raw Response:", raw_answer)
                    return raw_answer
            else:
                print(f"⚠️ Model {model} failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error with model {model}: {e}")

    if face:
        face.update_expression("error")
    return "Sorry, I couldn't connect to any AI services at the moment."


# ========== ACTION FUNCTIONS ==========

def shutdown_computer(face):
    """Safely shuts down the computer after confirmation.

    Args:
        face: The GUI face object for visual feedback

    Returns:
        bool: True if shutdown was initiated, False if cancelled
    """
    try:
        # Ask for confirmation
        speak("Are you sure you want to shut down the computer? Say 'yes' to confirm.", face)
        face.update_expression("processing")

        # Listen for confirmation with 7 second timeout
        confirmation = listen(7)

        if confirmation and any(word in confirmation for word in ["yes", "confirm", "shutdown"]):
            speak("Initiating shutdown. Goodbye!", face)
            face.update_expression("neutral")

            # Platform-specific shutdown commands
            if os.name == 'nt':  # Windows
                os.system('shutdown /s /t 1')
            elif os.name == 'posix':  # Linux/Mac
                if os.geteuid() == 0:  # If already root
                    os.system('shutdown now')
                else:
                    os.system('sudo shutdown now')
            else:
                raise OSError("Unsupported operating system")

            return True
        else:
            speak("Shutdown cancelled.", face)
            face.update_expression("neutral")
            return False

    except Exception as e:
        error_msg = f"Shutdown failed: {str(e)}"
        print(error_msg)
        speak("I couldn't complete the shutdown.", face)
        face.update_expression("error")
        return False

def open_application(command, face):
    """Parses command to open an application, folder, or file."""
    app_name = re.sub(r'\b(?:' + '|'.join(OPEN_APP_COMMANDS) + r')\b', '', command).replace("app", "").strip()
    if not app_name:
        speak("Which application or folder should I open?", face)
        return
    try:
        speak(f"Opening {app_name}.", face)
        if os.name == 'nt':
            # Try to open as folder/file first
            if os.path.exists(app_name):
                os.startfile(app_name)
            else:
                os.startfile(app_name)  # Will try as app name
        elif 'darwin' in os.sys.platform:
            subprocess.Popen(['open', app_name])
        else:
            subprocess.Popen(['xdg-open', app_name])
    except Exception as e:
        speak(f"Sorry, I couldn't open {app_name}. Error: {e}", face)


def search_google(command, face):
    """Search Google with the given query."""
    query = re.sub(r'\b(?:' + '|'.join(SEARCH_COMMANDS) + r')\b', '', command).strip()
    if query:
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        try:
            webbrowser.open(url)
            speak(f"Here are the search results for {query}", face)
        except Exception as e:
            speak(f"Could not open browser: {e}", face)
    else:
        speak("What should I search for?", face)


def play_youtube_video(command, face):
    """Play a YouTube video based on a search query."""
    query = re.sub(r'\b(?:' + '|'.join(PLAY_COMMANDS) + r')\b', '', command).replace("song", "").replace("video",
                                                                                                         "").strip()
    if not query:
        speak("What video or song should I play?", face)
        return
    try:
        speak(f"Searching YouTube for {query}", face)
        videos_search = VideosSearch(query, limit=1)
        results = videos_search.result()
        if results and results['result']:
            video_url = results['result'][0]['link']
            webbrowser.open(video_url)
            speak(f"Playing {results['result'][0]['title']}", face)
        else:
            speak("Sorry, I couldn't find any videos for that search.", face)
    except Exception as e:
        speak(f"I ran into an error trying to search YouTube: {e}", face)


def take_screenshot(face):
    """Take and save a screenshot."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        pyautogui.screenshot(filename)
        speak(f"Screenshot saved as {filename}", face)
    except Exception as e:
        speak(f"Failed to take screenshot: {e}", face)


def make_note(command, face):
    """Create a text note with a timestamp."""
    content = re.sub(r'\b(?:' + '|'.join(NOTE_COMMANDS) + r')\b', '', command).strip()
    if not content:
        speak("What should I write in the note?", face)
        content = listen(10)

    if content:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("jarvis_notes.txt", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {content}\n")
        speak("Note saved successfully.", face)
    else:
        speak("I didn't hear anything to note down.", face)


def get_weather(city):
    api_key = "your_openweathermap_api_key"  # Replace with your real API key
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        response = requests.get(url)
        data = response.json()
        if data["cod"] != 200:
            return "City not found."
        weather = data["weather"][0]["description"]
        temp = data["main"]["temp"]
        return f"The current weather in {city} is {weather} with temperature {temp}°C."
    except Exception as e:
        return "Sorry, I couldn't fetch the weather right now."


# ========== VIRTUAL FACE CLASS ==========

class JarvisFace:
    """A simple 2D cyber sci-fi face for Jarvis using Tkinter."""

    def __init__(self):
        self.expression = "neutral"
        self.is_talking = False
        self.root = None

    def run(self):
        self.root = tk.Tk()
        self.root.title("Jarvis")
        self.root.geometry("320x340")
        self.root.configure(bg='black')

        self.canvas = tk.Canvas(self.root, width=320, height=340, bg='black', highlightthickness=0)
        self.canvas.pack()

        # Face outline (cyber style)
        self.face_oval = self.canvas.create_oval(40, 40, 280, 300, fill='#181f2a', outline='#00ffff', width=3)

        # Eyes (glowing blue)
        self.eye_left = self.canvas.create_oval(100, 120, 140, 160, fill='#00eaff', outline='#b3f0ff', width=3)
        self.eye_right = self.canvas.create_oval(180, 120, 220, 160, fill='#00eaff', outline='#b3f0ff', width=3)

        # Futuristic mouth (simple arc)
        self.mouth = self.canvas.create_arc(120, 200, 200, 260, start=200, extent=140, style=tk.ARC, outline='#00eaff', width=4)

        # Cheek lights (small glowing dots)
        self.cheek_left = self.canvas.create_oval(85, 180, 95, 190, fill='#00eaff', outline='')
        self.cheek_right = self.canvas.create_oval(225, 180, 235, 190, fill='#00eaff', outline='')

        self._animate()
        self.root.mainloop()

    def update_expression(self, expr):
        self.expression = expr
        print(f"[Face Updated: {self.expression.upper()}]")

    def _animate(self):
        # Eyes: animate color for different expressions
        if self.expression == "listening":
            self.canvas.itemconfig(self.eye_left, fill='#00ffff')
            self.canvas.itemconfig(self.eye_right, fill='#00ffff')
        elif self.expression == "processing":
            self.canvas.itemconfig(self.eye_left, fill='#ffff00')
            self.canvas.itemconfig(self.eye_right, fill='#ffff00')
        elif self.expression == "error":
            self.canvas.itemconfig(self.eye_left, fill='#ff3333')
            self.canvas.itemconfig(self.eye_right, fill='#ff3333')
        else:  # Neutral
            self.canvas.itemconfig(self.eye_left, fill='#00eaff')
            self.canvas.itemconfig(self.eye_right, fill='#00eaff')

        # Mouth: animate for talking or change shape for error
        if self.is_talking:
            y_offset = 10 * (1 + abs(time.time() % 0.5 - 0.25) * 2)
            self.canvas.coords(self.mouth, 120, 200 + y_offset, 200, 260 + y_offset)
        elif self.expression == "error":
            self.canvas.coords(self.mouth, 130, 250, 190, 210)
        elif self.expression == "listening":
            self.canvas.coords(self.mouth, 120, 220, 200, 250)
        elif self.expression == "processing":
            self.canvas.coords(self.mouth, 130, 240, 190, 240)
        else:
            self.canvas.coords(self.mouth, 120, 200, 200, 260)

        if self.root:
            self.root.after(50, self._animate)


# ========== MAIN PROCESSING LOGIC ==========

def process_command(command, face):
    """Processes the user's command and calls the appropriate function."""
    if not command:
        return False

    command_lower = command.lower()

    if any(word in command_lower for word in EXIT_COMMANDS):
        speak("Goodbye! Have a nice day.", face)
        return True
    elif any(word in command_lower for word in SHUTDOWN_COMMANDS):
        return shutdown_computer(face)
    elif any(word in command_lower for word in OPEN_APP_COMMANDS):
        open_application(command, face)
    elif any(word in command_lower for word in SEARCH_COMMANDS):
        search_google(command, face)
    elif any(word in command_lower for word in PLAY_COMMANDS):
        play_youtube_video(command, face)
    elif any(word in command_lower for word in NOTE_COMMANDS):
        make_note(command, face)
    elif "screenshot" in command_lower:
        take_screenshot(face)
    elif "search for" in command_lower or "google" in command_lower:
        search_query = command_lower.replace("search for", "").replace("google", "").strip()
        if not search_query:
            speak("What should I search for?", face)
            search_query = listen()
        if search_query:
            speak("Searching on Google...", face)
            pywhatkit.search(search_query)
    elif "time" in command_lower:
        now = datetime.now().strftime("%I:%M %p")
        speak(f"The current time is {now}.", face)
    elif "date" in command_lower:
        today = datetime.now().strftime("%A, %B %d, %Y")
        speak(f"Today is {today}.", face)
    elif "joke" in command_lower:
        joke = random.choice(JOKES)
        speak(joke, face)
    elif "battery" in command_lower:
        battery = psutil.sensors_battery()
        if battery:
            percent = battery.percent
            plugged = "plugged in" if battery.power_plugged else "not plugged in"
            speak(f"Battery is at {percent} percent and is {plugged}.", face)
        else:
            speak("Couldn't get battery information.", face)
    elif "calculate" in command_lower:
        expr = command_lower.replace("calculate", "").strip()
        try:
            result = eval(expr)
            speak(f"The result is {result}", face)
        except Exception:
            speak("Sorry, I couldn't calculate that.", face)
    else:
        response = chat_with_ai(command, face)
        speak(response, face)

    return False


def main():
    """The main function to run the Jarvis assistant."""
    if not check_internet():
        print("No internet connection. Some features may be limited.")

    face = JarvisFace()
    face_thread = threading.Thread(target=face.run, daemon=True)
    face_thread.start()

    # Give Tkinter a moment to initialize
    time.sleep(1)
    speak("Hello, I am Jarvis. Say my name to activate me.", face)

    while True:
        try:
            face.update_expression("listening")
            wake_command = listen(timeout=None)

            if wake_command and any(word in wake_command for word in WAKE_WORDS):
                speak("Yes, how can I help?", face)
                command = listen(10)

                if process_command(command, face):
                    break

                face.update_expression("neutral")

        except KeyboardInterrupt:
            speak("Goodbye!", face)
            break
        except Exception as e:
            print(f"An unexpected error occurred in the main loop: {e}")
            speak("I've encountered an error. Resetting.", face)

    print("Jarvis has shut down.")
    if face.root:
        face.root.quit()


if __name__ == "__main__":
    print("Loaded API KEY:", API_KEY)
    main()