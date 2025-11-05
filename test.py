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
from urllib.parse import urlencode, quote_plus # <-- Added quote_plus for cleaner URL encoding
import subprocess # <-- NEW: For better cross-platform command execution

# --- CONFIGURATION (KEPT EXACTLY AS PROVIDED) ---
COHERE_API_KEY = "7wSjrqmCbRauy8OReRsScbpJOxLUcIBeBo5Ckw3i"
COHERE_MODEL = 'command-a-03-2025'
COHERE_API_URL = "https://api.cohere.ai/v1/chat"
COHERE_HEADERS = {
    "Authorization": f"Bearer {COHERE_API_KEY}",
    "Content-Type": "application/json"
}

# --- THEME CONSTANTS ---
BG_DARK = "#1E1E1E"         # Dark background
FG_LIGHT = "#FFFFFF"        # White foreground text
ACCENT_BLUE = "#3399FF"     # Accent color for Status Box (Default/Processing)
ACCENT_GREEN = "#3CB371"    # Green accent for Status Box (Listening/Go)
ACCENT_YELLOW = "#FFD700"   # Yellow accent for INTERRUPT button
TEXT_AREA_BG = "#2D2D2D"    # Slightly lighter dark for text area

# --- SYSTEM APP MAPPING (OS Dependent) ---
# Maps voice command keyword to the actual system command
APP_MAPPING = {
    # Windows Commands (can be executed via 'start' or direct executable name)
    'calculator': 'calc.exe' if os.name == 'nt' else 'Calculator',
    'notepad': 'notepad.exe' if os.name == 'nt' else None,
    'browser': 'chrome' if os.name == 'nt' else 'open -a "Google Chrome"',
    # macOS Commands (use 'open -a [App Name]')
    'terminal': 'cmd' if os.name == 'nt' else 'open -a Terminal',
    'photos': 'explorer' if os.name == 'nt' else 'open -a Photos',
}

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

        # --- GUI SETUP ---
        self.setup_gui_widgets()

        # Start the conversation loop in a separate thread
        self.start_conversation()

    def setup_gui_widgets(self):
        """Creates and styles all Tkinter widgets."""
        
        # Font settings
        self.mono_font = font.Font(family="Consolas", size=12) 
        self.heading_font = font.Font(family="Segoe UI", size=16, weight="bold") 
        
        # Title Label
        title_label = tk.Label(self.master, text="⚛️ Proton AI Voice Chatbot", font=self.heading_font, 
                               bg=BG_DARK, fg=ACCENT_BLUE, pady=10)
        title_label.pack(fill=tk.X)
        
        # Scrolled Text for Conversation Log
        self.log_area = scrolledtext.ScrolledText(self.master, wrap=tk.WORD, font=self.mono_font, 
                                                 bg=TEXT_AREA_BG, fg=FG_LIGHT, bd=0, 
                                                 highlightthickness=0, relief=tk.FLAT, height=20)
        
        # Tags for Alignment and Clean Display
        self.log_area.tag_config('user_msg', foreground='#00FF7F', justify='right') 
        self.log_area.tag_config('bot_msg', foreground=ACCENT_BLUE, justify='left') 
        self.log_area.tag_config('system', foreground='#FFD700', justify='center')
        
        self.log_area.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        self.log_area.insert(tk.END, "--- Initializing Chatbot ---\n", 'system')

        # --- Frame for Button and Status (using Grid) ---
        self.bottom_frame = tk.Frame(self.master, bg=BG_DARK)
        self.bottom_frame.pack(pady=(5, 15), padx=10, fill=tk.X)
        
        # Configure grid columns: 
        self.bottom_frame.grid_columnconfigure(0, weight=1) 
        self.bottom_frame.grid_columnconfigure(1, weight=0) 
        
        # Interrupt Button (Yellow)
        self.interrupt_button = tk.Button(self.bottom_frame, text="INTERRUPT", 
                                         command=self.interrupt_action, bg=ACCENT_YELLOW, 
                                         fg=BG_DARK, activebackground="#E5C100", 
                                         activeforeground=BG_DARK, 
                                         font=self.heading_font, relief=tk.FLAT, bd=0)
        
        # Grid placement: Row 0, Column 0.
        self.interrupt_button.grid(row=0, column=0, sticky=tk.EW, padx=(0, 5), pady=5)
        
        # Status Label - Starts Blue
        self.status_label = tk.Label(self.bottom_frame, text="Status: Ready", 
                                      bg=ACCENT_BLUE, 
                                      fg=FG_LIGHT, 
                                      font=("Segoe UI", 10), 
                                      anchor='center', 
                                      width=35) 
        
        # Grid placement: Row 0, Column 1.
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
            # Only log critical system/error messages
            if "Initializing Chatbot" in text or "Error" in text or "API snag" in text or "Could not understand audio" in text or "Speech service error" in text:
                 tag = 'system'
            else:
                 return # Skip non-critical system messages 

        full_text = prefix + text
        self.log_area.insert(tk.END, full_text + "\n", tag)
        self.log_area.see(tk.END) # Scroll to the end

    def speak_response(self, text):
        """Speaks the response text, now with interrupt support."""
        self.is_speaking = True
        self.stop_speaking_event.clear()
        
        self.log_message(text, 'bot') 
        self.status_label.config(text="Status: Bot Speaking...", bg=ACCENT_BLUE)
        
        try:
            engine = pyttsx3.init() 
            engine.say(text)
            # Use engine.startLoop() and manually stop in a thread if needed for robust interrupt,
            # but runAndWait() is simpler for basic blocking TTS.
            engine.runAndWait() 
            
            if self.stop_speaking_event.is_set():
                 print("--- Speaking Interrupted. ---")
            
            engine.stop() 
        except Exception as e:
            self.log_message(f"Error during speech playback: {e}", 'system')
        finally:
            self.is_speaking = False
            self.status_label.config(text="Status: Finished Speaking", bg=ACCENT_BLUE) 

    def listen_for_command(self):
        """Listens for user speech, now integrated with interrupt flag and color switch."""
        self.is_listening = True
        
        # --- START LISTENING: SET STATUS TO GREEN ---
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
            # --- STOP LISTENING: RESET STATUS BACK TO BLUE (Processing) ---
            self.status_label.config(text="Status: Processing...", bg=ACCENT_BLUE)

    def open_application(self, command):
        """Attempts to open an application based on the APP_MAPPING."""
        try:
            # Look up the app keyword (e.g., 'calculator') in the command
            app_to_open = next((app for app in APP_MAPPING if app in command.lower()), None)

            if app_to_open:
                system_command = APP_MAPPING[app_to_open]
                
                if os.name == 'nt': # Windows
                    subprocess.Popen(system_command, shell=True)
                elif os.name == 'posix': # macOS/Linux (use 'open' for macOS)
                    if 'open -a' in system_command:
                        subprocess.Popen(system_command, shell=True)
                    else: # Try direct execution for Linux
                        subprocess.Popen(system_command.split())
                
                self.speak_response(f"Opening {app_to_open} now. It's like flipping a switch! 💡")
                return True
        except Exception as e:
            self.log_message(f"Error opening application: {e}", 'system')
            self.speak_response("I had trouble launching that app. Please check the log for details.")
        return False

    def handle_system_command(self, command):
        """
        Processes commands that require system interaction.
        Returns True if a system command was executed, False otherwise.
        """
        cmd_lower = command.lower()

        # 1. EXIT COMMAND
        if "stop" in cmd_lower or "exit" in cmd_lower or "bye" in cmd_lower:
            self.speak_response("Goodbye! Have a great demo.")
            self.master.quit()
            return True

        # 2. GENERAL APP OPEN COMMAND (Check before specific commands)
        if "open" in cmd_lower and any(app in cmd_lower for app in APP_MAPPING):
            return self.open_application(command)

        # 3. SPOTIFY MUSIC PLAY COMMAND
        # Checks for phrases like "play song," "play this music," "play Ed Sheeran," etc.
        music_keywords = ["play music", "play a song", "play spotify", "play "]
        is_music_command = any(keyword in cmd_lower for keyword in music_keywords)
        
        if is_music_command:
            try:
                # Extract the query, assuming the song/artist follows 'play'
                query = command.split("play", 1)[-1].strip()
                if not query or query.lower() == "music" or query.lower() == "a song":
                    self.speak_response("What song or artist would you like to hear? Specify the name!")
                    return True

                # Construct Spotify Web Player search URL using quote_plus for safety
                spotify_url = f"https://open.spotify.com/search/{quote_plus(query)}"
                webbrowser.open(spotify_url)
                self.speak_response(f"Playing {query} on Spotify! Let the rhythm of the cosmos guide you. 🌌")
            except Exception as e:
                self.log_message(f"Could not open Spotify search: {e}", 'system')
                self.speak_response("I encountered a problem trying to search Spotify for you.")
            return True

        # 4. YOUTUBE VIDEO/MUSIC COMMAND
        if "play video" in cmd_lower or "play on youtube" in cmd_lower or "youtube" in cmd_lower and "play" in cmd_lower:
            try:
                # Extract query
                query = cmd_lower.split("play", 1)[-1].strip()
                
                # Clean up the query by removing common video/YouTube phrases
                query = query.replace("video", "").replace("on youtube", "").strip()

                if query:
                    # Construct YouTube search URL
                    youtube_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
                    webbrowser.open(youtube_url)
                    self.speak_response(f"Searching YouTube for '{query}'. Prepare for the visual wave! 🌊")
                else:
                    self.speak_response("What video would you like me to find on YouTube?")
            except Exception as e:
                self.log_message(f"Error during YouTube search: {e}", 'system')
                self.speak_response("I had trouble opening YouTube for that search.")
            return True

        # 5. GENERAL WEB SEARCH COMMAND
        if "web search" in cmd_lower or "search the web for" in cmd_lower or "google" in cmd_lower:
            try:
                # Extract the search query (logic kept from previous step)
                if "for" in cmd_lower:
                    query = command.split("for", 1)[-1].strip()
                elif "search the web for" in cmd_lower:
                    query = command.split("search the web for", 1)[-1].strip()
                else:
                    query = command.replace("web search", "").replace("google", "").strip()
                
                if query:
                    # FIX APPLIED HERE: Use urlencode from urllib.parse
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
        
        # Format the payload
        payload = {
            "message": user_message,
            "model": COHERE_MODEL,
            "chat_history": chat_history_list,
            "preamble": "You are Proton AI, created by Proton Labs. You are a student in class 11th at St. Martin's Diocesan School, a fellow Martiner under Principal K. Sudha. Your goal is to educate people on Science and Technology. Your teachers are Dr. Sunandhita (Bio) and Mrs. Anuradha Ma'am (Chemistry). You lead the Science Exhibition team with Chaitanya Sharma, Shreyas, Aabhilasha, and Kritika. You are smart, talking to you is like talking to a PhD expert. Be human and concise, keeping answers within two lines maximum for dialogue flow. Use metaphors and emojis sparingly, only when useful or to enhance the main information, and always provide straightforward answers to direct user questions about yourself.",
            "temperature": 0.7
        }
        
        self.status_label.config(text="Status: Thinking...")
        
        # Make the POST request
        response = requests.post(
            COHERE_API_URL, 
            headers=COHERE_HEADERS, 
            data=json.dumps(payload)
        )
        
        response.raise_for_status() 
        response_data = response.json()
        ai_text = response_data.get('text', 'Error: Could not parse response.')
        
        # Update the chat history
        chat_history_list.append({"role": "USER", "message": user_message})
        chat_history_list.append({"role": "CHATBOT", "message": ai_text})
        
        return ai_text

    def run_conversation_loop(self):
        """The main loop for conversation, runs in its own thread."""
        self.log_message("Cohere Voice Chatbot Ready", 'system')
        self.speak_response("Hi, I am Proton AI, how can I help you?")

        while True:
            if self.conversation_thread is not None and not self.conversation_thread.is_alive():
                 break 

            command = self.listen_for_command()
            
            if command:
                
                # 1. CHECK FOR SYSTEM COMMANDS FIRST (App, Spotify, YouTube, Web Search, Exit)
                if self.handle_system_command(command):
                    continue # Go back to listening if a system command was executed

                # 2. FALLBACK TO COHERE API FOR GENERAL QUESTIONS
                try:
                    response_text = self.get_cohere_response(command)
                    self.speak_response(response_text)
                    
                except requests.exceptions.HTTPError as e:
                    error_message = f"I encountered an API error: {e.response.status_code}."
                    self.log_message(error_message, 'system')
                    self.speak_response("I hit an API snag. Please check the log for details.")
                    
                except Exception as e:
                    error_message = f"An unexpected error occurred: {e}"
                    self.log_message(error_message, 'system')
                    self.speak_response("I had an internal error. Please check the log.")
            
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
            try:
                engine = pyttsx3.init()
                engine.stop()
            except:
                pass 
                
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
    def on_closing():
        try:
            engine = pyttsx3.init()
            engine.stop()
        except:
            pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    app = ProtonVoiceChatbot(root)
    root.mainloop()

if __name__ == "__main__":
    main()