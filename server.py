import os
import re
import sys
import json
import time
import webbrowser
import subprocess
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

# === TTS ===
import pyttsx3

# === Gemini ===
import google.generativeai as genai

# Try to load .env if present
def load_env_file():
    env_path = Path(__file__).with_name('.env')
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            if '=' in line and not line.strip().startswith('#'):
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env_file()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
if not GEMINI_API_KEY:
    print("[WARN] GEMINI_API_KEY missing. Edit .env to add it.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)
CORS(app)

engine = pyttsx3.init()
engine.setProperty('rate', 165)

def speak(text: str):
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print("TTS error:", e)

# ---------- Command Parsing ----------
def open_youtube():
    webbrowser.open("https://www.youtube.com")
    return "यूट्यूब खोल रहा हूँ।"

def open_browser():
    webbrowser.open("https://www.google.com")
    return "ब्राउज़र खोल दिया।"

def play_on_youtube(q: str):
    q = q.strip()
    if not q:
        return "कौन सा गाना या वीडियो?"
    try:
        import pywhatkit
        pywhatkit.playonyt(q)
        return f"{q} YouTube पर चला रहा हूँ।"
    except Exception:
        webbrowser.open("https://www.youtube.com/results?search_query=" + q.replace(' ', '+'))
        return "YouTube search खोल दिया।"
    
def system_shutdown(confirm: bool):
    if not confirm:
        return "कृपया पुष्टि करें: 'shutdown confirm' बोलें/लिखें।"
    if sys.platform.startswith("win"):
        os.system("shutdown /s /t 5")
    elif sys.platform == "darwin":
        os.system("osascript -e 'tell app \"System Events\" to shut down'")
    else:
        os.system("shutdown -h now")
    return "सिस्टम शटडाउन कमांड भेज दी गई।"

def system_restart(confirm: bool):
    if not confirm:
        return "कृपया पुष्टि करें: 'restart confirm' बोलें/लिखें।"
    if sys.platform.startswith("win"):
        os.system("shutdown /r /t 5")
    elif sys.platform == "darwin":
        os.system("osascript -e 'tell app \"System Events\" to restart'")
    else:
        os.system("shutdown -r now")
    return "सिस्टम रीस्टार्ट कमांड भेज दी गई।"

def open_file_explorer():
    try:
        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer"])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "."])
        else:
            subprocess.Popen(["xdg-open", "."])
        return "फ़ाइल एक्सप्लोरर खोल रहा हूँ।"
    except Exception as e:
        return f"फ़ाइल एक्सप्लोरर में समस्या: {e}"

def gemini_answer(prompt: str) -> str:
    if not GEMINI_API_KEY:
        return "Gemini API key सेट नहीं है। .env फ़ाइल में GEMINI_API_KEY जोड़ें।"
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(prompt)
        return (resp.text or "").strip() or "कोई उत्तर नहीं मिला।"
    except Exception as e:
        return f"Gemini से उत्तर प्राप्त करने में समस्या: {e}"

COMMAND_PATTERNS = [
    (re.compile(r"youtube|यूट्यूब|www\.youtube\.com", re.I), lambda t: open_youtube()),
    (re.compile(r"browser|ब्राउज़र|वेब", re.I), lambda t: open_browser()),
    (re.compile(r"(play|चल[ा-]ओ|गाना|song)(.*)", re.I), lambda t: play_on_youtube(re.sub(r'^(play|चल[ा-]ओ|गाना|song)\s*', '', t, flags=re.I))),
    (re.compile(r"shutdown(.*)", re.I), lambda t: system_shutdown('confirm' in t.lower() or 'पुष्टि' in t.lower())),
    (re.compile(r"restart|रीस्टार्ट|reboot", re.I), lambda t: system_restart('confirm' in t.lower() or 'पुष्टि' in t.lower())),
    (re.compile(r"file|फ़ाइल|explorer", re.I), lambda t: open_file_explorer()),
]

def dispatch_command(text: str) -> str:
    for pat, fn in COMMAND_PATTERNS:
        if pat.search(text):
            return fn(text)
    # else fallback to Gemini Q/A
    return gemini_answer(text)

# ---------- Routes ----------
@app.route("/command", methods=["POST"])
def command():
    data = request.get_json(force=True) or {}
    user_text = str(data.get("text", "")).strip()
    if not user_text:
        return jsonify({"reply": "कृपया कोई कमांड या सवाल लिखें/बोलें।"})
    reply = dispatch_command(user_text.lower())
    # also speak on server side
    try:
        speak(reply)
    except:
        pass
    return jsonify({"reply": reply})

@app.route("/say", methods=["POST"])
def say():
    data = request.get_json(force=True) or {}
    text = str(data.get("text", ""))
    speak(text)
    return jsonify({"ok": True})

if __name__ == "__main__":
    print("YugGPT-Jarvis backend चल रहा है: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
