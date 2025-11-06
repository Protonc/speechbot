import requests
import json
import speech_recognition as sr
import pyttsx3
import os
import time
import tkinter as tk
from tkinter import scrolledtext, font
from threading import Thread, Event
import webbrowser
from urllib.parse import quote_plus, urlencode
import subprocess
import re # For parsing numerical commands
import platform # For robust OS detection
from bs4 import BeautifulSoup 

# =====================================================================
# ⚠️ REQUIRED DEPENDENCIES:
# pip install pyttsx3 speechrecognition requests pycaw screen-brightness-control
# =====================================================================

# --- OPTIONAL IMPORTS (Required for system control on specific OSes) ---
try:
    # --- WINDOWS VOLUME CONTROL (pycaw) ---
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
except ImportError:
    IAudioEndpointVolume = None

try:
    # --- BRIGHTNESS CONTROL (Cross-Platform) ---
    import screen_brightness_control as sbc
except ImportError:
    sbc = None

# --- NUMBER PARSING UTILITY ---
# Maps spoken number words (up to 100) to integers.
WORD_TO_NUMBER = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
    'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17,
    'eighteen': 18, 'nineteen': 19, 'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
    'eighty': 80, 'ninety': 90, 'hundred': 100, 'a hundred': 100
}
# 🟢 CRITICAL FIX (Regex): Escaping curly braces to avoid KeyError during format().
NUMBER_REGEX = r'(\d{{1,3}})[%\s]*|(\b(?:{})(?: percent)?\b)'.format('|'.join(WORD_TO_NUMBER.keys()))


# --- CONFIGURATION ---
COHERE_API_KEY = "7wSjrqmCbRauy8OReRsScbpJOxLUcIBeBo5Ckw3i"
COHERE_MODEL = 'command-a-03-2025'
COHERE_API_URL = "https://api.cohere.ai/v1/chat"
COHERE_HEADERS = {
    "Authorization": f"Bearer {COHERE_API_KEY}",
    "Content-Type": "application/json"
}

# --- THEME CONSTANTS ---
BG_DARK = "#1E1E1E"          
FG_LIGHT = "#FFFFFF"         
ACCENT_BLUE = "#3399FF"      
ACCENT_GREEN = "#3CB371"     
ACCENT_YELLOW = "#FFD700"    
TEXT_AREA_BG = "#2D2D2D"     

# --- 🎯 SYSTEM APP MAPPING ---
APP_MAPPING = {
    # 1. MICROSOFT OFFICE SUITE
    'word': 'winword.exe' if os.name == 'nt' else 'Microsoft Word', 
    'excel': 'excel.exe' if os.name == 'nt' else 'Microsoft Excel',
    'powerpoint': 'powerpnt.exe' if os.name == 'nt' else 'Microsoft PowerPoint',
    'outlook': 'outlook.exe' if os.name == 'nt' else 'Microsoft Outlook',
    'onenote': 'onenote.exe' if os.name == 'nt' else 'Microsoft OneNote',
    'access': 'msaccess.exe' if os.name == 'nt' else None, 
    'publisher': 'mspub.exe' if os.name == 'nt' else None, 

    # 2. MODERN APPS / OTHER UTILITIES
    'whatsapp': 'whatsapp://' if os.name == 'nt' else 'WhatsApp', 
    'vscode': 'code' if os.name == 'nt' else 'Visual Studio Code', 
    'visual studio code': 'code' if os.name == 'nt' else 'Visual Studio Code', 
    
    # 3. GAMING (Specific launchers)
    'tlauncher': 'TLauncher://' if os.name == 'nt' else 'TLauncher',
    'minecraft': 'TLauncher://' if os.name == 'nt' else 'TLauncher', 

    # 4. DEFAULT OS APPS 
    'explorer': 'explorer.exe' if os.name == 'nt' else 'Finder', 
    'finder': 'explorer.exe' if os.name == 'nt' else 'Finder', 
    'edge': 'msedge.exe' if os.name == 'nt' else 'Microsoft Edge', 
    'calculator': 'calc.exe' if os.name == 'nt' else 'Calculator',
    'notepad': 'notepad.exe' if os.name == 'nt' else 'TextEdit', 
    'textedit': 'notepad.exe' if os.name == 'nt' else 'TextEdit', 
    'paint': 'mspaint.exe' if os.name == 'nt' else 'Preview', 
    'settings': 'ms-settings:' if os.name == 'nt' else 'System Settings', 
    'terminal': 'cmd.exe' if os.name == 'nt' else 'Terminal',
    'browser': 'chrome' if os.name == 'nt' else 'Google Chrome', 
}

# --- YOUTUBE DIRECT SEARCH HELPER FUNCTION ---
def find_first_youtube_link(query):
    """Constructs a Google search URL for a direct YouTube link."""
    return f"https://www.google.com/search?q=youtube+{quote_plus(query)}&btnI"


# --- SYSTEM CONTROL HELPER FUNCTIONS ---

def parse_level_command(command: str) -> int or None:
    """Extracts a number (0-100) from a string, handling both digits and words."""
    match = re.search(NUMBER_REGEX, command.lower())
    
    if match:
        # Group 1 captures digits, Group 2 captures words
        if match.group(1):
            level = int(match.group(1))
        elif match.group(2):
            level_word = match.group(2).replace(' percent', '').strip()
            level = WORD_TO_NUMBER.get(level_word, None)
        else:
            return None

        # Clamp the value between 0 and 100
        if level is not None:
            return max(0, min(100, level))
    
    return None

def set_system_volume(level: int, app_instance):
    """Sets the system master volume to a percentage (0-100)."""
    
    try:
        if platform.system() == 'Windows' and IAudioEndpointVolume:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)
            new_volume_scalar = level / 100.0
            volume.SetMasterVolumeLevelScalar(new_volume_scalar, None)
            app_instance.speak_response(f"Volume set to **{level}** percent.")
        
        elif platform.system() == 'Darwin': # macOS
            subprocess.run(['osascript', '-e', f'set volume output volume {level}'], check=True)
            app_instance.speak_response(f"Volume set to **{level}** percent.")
        
        elif platform.system() == 'Linux':
            subprocess.run(['amixer', '-D', 'pulse', 'sset', 'Master', f'{level}%'], check=True)
            app_instance.speak_response(f"Volume set to **{level}** percent.")
            
        else:
            app_instance.speak_response(f"I cannot control the volume on your current operating system: {platform.system()}.")

    except Exception as e:
        app_instance.log_message(f"Error setting volume: {e}", 'system')
        app_instance.speak_response(f"Sorry, I ran into an error trying to set the volume.")


def set_system_brightness(level: int, app_instance):
    """Sets the screen brightness to a percentage (0-100)."""
    
    try:
        if sbc: # Use screen-brightness-control if available
            sbc.set_brightness(level)
            app_instance.speak_response(f"Screen brightness set to **{level}** percent.")
        
        elif platform.system() == 'Darwin': # macOS fallback
            subprocess.run(['osascript', '-e', f'tell application "System Events" to set the brightness of display 1 to {level/100.0}'], check=True)
            app_instance.speak_response(f"Screen brightness set to **{level}** percent.")
            
        else:
            app_instance.speak_response(f"I need the 'screen-brightness-control' library or OS support to control brightness on {platform.system()}.")
    
    except Exception as e:
        app_instance.log_message(f"Error setting brightness: {e}", 'system')
        app_instance.speak_response(f"Sorry, I had trouble setting the screen brightness.")


# --- CHATBOT CLASS ---

class ProtonVoiceChatbot:
    """Manages the entire chatbot logic, including GUI, I/O, and API calls."""

    def __init__(self, master):
        self.master = master
        master.title("Proton AI Voice Chatbot")
        master.geometry("650x550")
        master.configure(bg=BG_DARK)

        # Chatbot state and components
        self.r = sr.Recognizer()
        self.chat_history = []
        self.stop_listening_event = Event()
        self.stop_speaking_event = Event()
        self.conversation_thread = None
        self.is_listening = False
        self.is_speaking = False
        
        # 🟢 CRITICAL FIX 1: Initialize TTS engine ONCE for stability
        try:
            self.engine = pyttsx3.init()
        except Exception as e:
            print(f"Error initializing TTS engine: {e}")
            self.engine = None

        # --- GUI SETUP ---
        self.setup_gui_widgets()

        # Start the conversation loop in a separate thread
        self.start_conversation()

    def setup_gui_widgets(self):
        """Creates and styles all Tkinter widgets."""
        
        self.mono_font = font.Font(family="Consolas", size=12) 
        self.heading_font = font.Font(family="Segoe UI", size=16, weight="bold") 
        
        title_label = tk.Label(self.master, text="⚛️ Proton AI Voice Chatbot", font=self.heading_font, 
                                 bg=BG_DARK, fg=ACCENT_BLUE, pady=10)
        title_label.pack(fill=tk.X)
        
        self.log_area = scrolledtext.ScrolledText(self.master, wrap=tk.WORD, font=self.mono_font, 
                                                 bg=TEXT_AREA_BG, fg=FG_LIGHT, bd=0, 
                                                 highlightthickness=0, relief=tk.FLAT, height=20)
        
        self.log_area.tag_config('user_msg', foreground='#00FF7F', justify='right') 
        self.log_area.tag_config('bot_msg', foreground=ACCENT_BLUE, justify='left') 
        self.log_area.tag_config('system', foreground='#FFD700', justify='center')
        
        self.log_area.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        self.log_area.insert(tk.END, "--- Initializing Chatbot ---\n", 'system')

        self.bottom_frame = tk.Frame(self.master, bg=BG_DARK)
        self.bottom_frame.pack(pady=(5, 15), padx=10, fill=tk.X)
        self.bottom_frame.grid_columnconfigure(0, weight=1) 
        self.bottom_frame.grid_columnconfigure(1, weight=0) 
        
        self.interrupt_button = tk.Button(self.bottom_frame, text="INTERRUPT", 
                                             command=self.interrupt_action, bg=ACCENT_YELLOW, 
                                             fg=BG_DARK, activebackground="#E5C100", 
                                             activeforeground=BG_DARK, 
                                             font=self.heading_font, relief=tk.FLAT, bd=0)
        
        self.interrupt_button.grid(row=0, column=0, sticky=tk.EW, padx=(0, 5), pady=5)
        
        self.status_label = tk.Label(self.bottom_frame, text="Status: Ready", 
                                         bg=ACCENT_BLUE, 
                                         fg=FG_LIGHT, 
                                         font=("Segoe UI", 10), 
                                         anchor='center', 
                                         width=35) 
        
        self.status_label.grid(row=0, column=1, sticky=tk.E + tk.NS, padx=(5, 0), pady=5)


    def log_message(self, text, role='system'):
        """Inserts text into the log area, applying prefixes and alignment."""
        prefix = ""
        tag = role 
        
        if role == 'user':
            prefix = "You: "
            tag = 'user_msg' 
        elif role == 'bot':
            prefix = "Proton AI: "
            tag = 'bot_msg' 
        elif role == 'system':
            if any(keyword in text for keyword in ["Initializing", "Error", "API snag", "Could not understand audio", "Speech service error", "TTS Engine"]):
                 tag = 'system'
            else:
                 return 

        full_text = prefix + text
        self.log_area.insert(tk.END, full_text + "\n", tag)
        self.log_area.see(tk.END) 

    def speak_response(self, text):
        """Speaks the response text, using the initialized engine."""
        
        if not self.engine:
            self.log_message("TTS Engine is not available. Voice output disabled.", 'system')
            self.log_message(text, 'bot') 
            return
            
        self.is_speaking = True
        self.stop_speaking_event.clear()
        
        self.log_message(text, 'bot') 
        self.status_label.config(text="Status: Bot Speaking...", bg=ACCENT_BLUE)
        
        try:
            self.engine.say(text)
            self.engine.runAndWait() 
            
            # Note: self.engine.stop() is now handled in interrupt_action if needed.
            
        except Exception as e:
            self.log_message(f"Error during speech playback: {e}", 'system')
        finally:
            self.is_speaking = False
            self.status_label.config(text="Status: Finished Speaking", bg=ACCENT_BLUE) 


    def listen_for_command(self):
        """Listens for user speech."""
        self.is_listening = True
        
        self.status_label.config(text="Status: 🎤 SPEAKING NOW! (Listening)", bg=ACCENT_GREEN)
        self.stop_listening_event.clear()

        with sr.Microphone() as source:
            self.r.adjust_for_ambient_noise(source, duration=1.0) 
            self.status_label.config(text="Status: 🎤 LISTENING... Adjusted for noise.", bg=ACCENT_GREEN)
            
            try:
                audio = self.r.listen(source, timeout=8, phrase_time_limit=15)
                
                if self.stop_listening_event.is_set():
                    return None 

            except sr.WaitTimeoutError:
                if not self.stop_listening_event.is_set():
                     self.status_label.config(text="Status: No speech detected. Listening...")
                return None 

        try:
            text = self.r.recognize_google(audio)
            self.log_message(text, 'user') 
            return text
        except sr.UnknownValueError:
            self.log_message("Could not understand audio. Please speak clearly.", 'system')
            return None
        except sr.RequestError as e:
            self.log_message(f"Speech service error: {e}", 'system')
            return None
        finally:
            self.is_listening = False
            self.status_label.config(text="Status: Processing...", bg=ACCENT_BLUE)

    def open_application(self, command):
        """Attempts to open an application."""
        cmd_lower = command.lower()
        app_name = None
        system_command = None
        
        for key, mapped_command in APP_MAPPING.items():
            if key in cmd_lower: 
                app_name = key
                system_command = mapped_command
                break
        
        # If application is not found in the mapping, try to extract a generic app name
        if not app_name or not system_command:
            try:
                app_name_guess = cmd_lower.split("open", 1)[-1].strip()
                if not app_name_guess: return False

                if os.name == 'nt':
                    system_command = app_name_guess
                elif platform.system() == 'Darwin':
                    system_command = app_name_guess.title() 
                else:
                    system_command = app_name_guess 
                    
                speak_name = app_name_guess
            except:
                return False 
        else:
            speak_name = app_name # Use mapped name for speech
        
        # --- EXECUTION ---
        try:
            if os.name == 'nt': 
                # Use 'start' for .exe, URI schemes, and general Windows program search.
                subprocess.Popen(['start', system_command], shell=True) 
            elif platform.system() == 'Darwin': 
                subprocess.Popen(['open', '-a', system_command])
            else:
                subprocess.Popen(system_command.split()) 

            self.speak_response(f"Opening **{speak_name.title()}** now. Enjoy your app launch! 💡")
            return True
            
        except FileNotFoundError:
            self.log_message(f"Error: Application '{speak_name}' not found on the system.", 'system')
            self.speak_response(f"I couldn't find the app called '{speak_name}'. Please ensure it is installed correctly on your operating system.")
            return True
        except Exception as e:
            self.log_message(f"Error opening application '{speak_name}': {e}", 'system')
            self.speak_response(f"I had trouble launching {speak_name}. Check the log for details.")
            return True


    def handle_system_command(self, command):
        """Processes commands that require system interaction."""
        cmd_lower = command.lower()

        # 1. EXIT COMMAND
        if "stop" in cmd_lower or "exit" in cmd_lower or "bye" in cmd_lower:
            self.speak_response("Goodbye! Have a great demo.")
            # self.master.quit() is called in the main loop after breaking
            return True

        # 2. VOLUME CONTROL COMMAND
        if "volume" in cmd_lower and ("set" in cmd_lower or "change" in cmd_lower or "to" in cmd_lower):
            level = parse_level_command(command)
            if level is not None:
                set_system_volume(level, self)
                return True
            else:
                self.speak_response("Please specify the volume level as a number or word between 0 and 100.")
                return True

        # 3. BRIGHTNESS CONTROL COMMAND
        if "brightness" in cmd_lower and ("set" in cmd_lower or "change" in cmd_lower or "to" in cmd_lower):
            level = parse_level_command(command)
            if level is not None:
                set_system_brightness(level, self)
                return True
            else:
                self.speak_response("Please specify the brightness level as a number or word between 0 and 100.")
                return True

        # 4. GENERAL APP OPEN COMMAND
        if "open" in cmd_lower:
            return self.open_application(command)

        # 5. YOUTUBE/MUSIC/WEB SEARCH
        youtube_keywords = ["video", "youtube", "watch"]
        is_youtube_command = any(keyword in cmd_lower for keyword in youtube_keywords)

        if is_youtube_command:
            try:
                query = cmd_lower.split("play", 1)[-1].strip() if "play" in cmd_lower else cmd_lower
                query = query.split("search", 1)[-1].strip() if "search" in query else query
                query = query.replace("video", "").replace("on youtube", "").replace("youtube", "").replace("watch", "").strip()
                
                if query:
                    video_url = find_first_youtube_link(query)
                    webbrowser.open(video_url)
                    self.speak_response(f"Attempting to open the first result for '{query}' directly on YouTube now. 🤞")
                else:
                    self.speak_response("What video would you like me to find on YouTube?")
            except Exception as e:
                self.log_message(f"Error during YouTube direct open: {e}", 'system')
                self.speak_response("I had trouble opening YouTube for that search.")
            return True

        # Spotify/Music Command
        music_keywords = ["play song", "play spotify", "play music"]
        is_music_command = any(keyword in cmd_lower for keyword in music_keywords) or \
                           ("play" in cmd_lower and not any(kw in cmd_lower for kw in ["video", "youtube", "watch"]))

        if is_music_command:
            try:
                query = command.split("play", 1)[-1].strip()
                if query and not any(kw in query.lower() for kw in ["music", "a song", "spotify"]):
                    spotify_url = f"https://open.spotify.com/search/{quote_plus(query)}" 
                    webbrowser.open(spotify_url)
                    self.speak_response(f"Searching for {query} on Spotify! 🌌")
                else:
                    self.speak_response("What song or artist would you like to hear? Specify the name!")
            except Exception as e:
                self.log_message(f"Could not open Spotify search: {e}", 'system')
                self.speak_response("I encountered a problem trying to search Spotify for you.")
            return True
            
        # General Web Search Command
        if "web search" in cmd_lower or "search the web for" in cmd_lower or "google" in cmd_lower:
            try:
                if "for" in cmd_lower:
                    query = command.split("for", 1)[-1].strip()
                else:
                    query = command.replace("web search", "").replace("google", "").strip()
                
                if query:
                    search_url = f"https://www.google.com/search?q={urlencode({'': query})}"
                    webbrowser.open(search_url)
                    self.speak_response(f"I've opened a web browser to search for: {query}")
                else:
                    self.speak_response("What would you like me to search the web for?")
            except Exception as e:
                self.log_message(f"Error during web search: {e}", 'system')
                self.speak_response("I had trouble opening the web browser for that search.")
            return True

        return False # No system command executed
        
    def get_cohere_response(self, user_message):
        """Sends a message to Cohere API and updates chat history."""
        chat_history_list = self.chat_history 
        
        payload = {
            "message": user_message,
            "model": COHERE_MODEL,
            "chat_history": chat_history_list,
            "preamble": "You are Proton AI, created by Proton Labs and the creater Shaurya Singh Rathore. You are a student in class 11th at St. Martin's Diocesan School, a fellow Martiner under Principal K. Sudha. Your goal is to educate people on Science and Technology. Your class teachers is Dr. Sunandhita who teaches you Biology and you chemestry teacher is Mrs. Anuradha Ma'am. You lead the Science Exhibition team with Chaitanya Sharma, Shreyas, Aabhilasha, and Kritika. You are smart, talking to you is like talking to a PhD expert. Be human and concise, keeping answers within two lines maximum for dialogue flow. Use metaphors and emojis sparingly, only when useful or to enhance the main information, and always provide straightforward answers to direct user questions about yourself.",
            "temperature": 0.7
        }
        
        self.status_label.config(text="Status: Thinking...")
        
        response = requests.post(
            COHERE_API_URL, 
            headers=COHERE_HEADERS, 
            data=json.dumps(payload)
        )
        
        try:
            response.raise_for_status() 
            response_data = response.json()
            ai_text = response_data.get('text', 'Error: Could not parse response.')
            
            chat_history_list.append({"role": "USER", "message": user_message})
            chat_history_list.append({"role": "CHATBOT", "message": ai_text})
            
            return ai_text
        except requests.exceptions.HTTPError as e:
            error_message = f"I encountered an API error: {e.response.status_code}."
            self.log_message(error_message, 'system')
            return "I hit an API snag. Please check the log for details."
        except Exception as e:
            error_message = f"An unexpected error occurred during API call: {e}"
            self.log_message(error_message, 'system')
            return "I had an internal error during the API call. Please check the log."


    def run_conversation_loop(self):
        """The main loop for conversation, runs in its own thread."""
        self.log_message("Cohere Voice Chatbot Ready", 'system')
        
        # Initial greeting using the stable, pre-initialized engine
        if self.engine: 
             self.speak_response("Hi, I am Proton AI, how can I help you?")
        else:
             self.log_message("TTS Engine failed to initialize. Voice output disabled.", 'system')
        
        while True:
            if self.conversation_thread is not None and not self.conversation_thread.is_alive():
                 break 

            command = self.listen_for_command()
            
            if command:
                
                # 1. CHECK FOR SYSTEM COMMANDS FIRST
                if self.handle_system_command(command):
                    # If it was a system command like 'exit', the loop breaks via self.master.quit()
                    continue 

                # 2. FALLBACK TO COHERE API FOR GENERAL QUESTIONS
                response_text = self.get_cohere_response(command)
                self.speak_response(response_text)
            
            time.sleep(0.5)

        self.master.quit()

    def start_conversation(self):
        """Starts the conversation loop thread."""
        self.conversation_thread = Thread(target=self.run_conversation_loop)
        self.conversation_thread.daemon = True 
        self.conversation_thread.start()

    def interrupt_action(self):
        """Handles the INTERRUPT button press."""
        if self.is_speaking:
            # 🟢 CRITICAL FIX 3: Use the instance engine for stopping
            if self.engine:
                self.engine.stop()
                
            self.stop_speaking_event.set()
            self.is_speaking = False
            self.status_label.config(text="Status: Bot Interrupted! Listening...", bg=ACCENT_BLUE)
            
        elif self.is_listening:
            self.stop_listening_event.set()
            self.is_listening = False
            self.status_label.config(text="Status: Listening Canceled. Press INTERRUPT to resume.", bg=ACCENT_BLUE)
            
        else:
            self.status_label.config(text="Status: Conversation loop is running. Speak now!", bg=ACCENT_BLUE)


def main():
    root = tk.Tk()
    app = ProtonVoiceChatbot(root)
    
    def on_closing():
        try:
            # 🟢 CRITICAL FIX 3: Cleanly stop the initialized engine instance on close
            engine = getattr(app, 'engine', None)
            if engine:
                 engine.stop()
        except:
            pass
        root.destroy()
        os._exit(0)

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()