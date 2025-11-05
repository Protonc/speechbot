import requests
import json
import speech_recognition as sr
import pyttsx3
import os
import time
import tkinter as tk
from tkinter import scrolledtext, font
from threading import Thread, Event

# --- CONFIGURATION (KEPT EXACTLY AS PROVIDED) ---
COHERE_API_KEY = "Uci6E53ri06gEjPsqW5eKXUsMj7lYmMSxyTdjumb"
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
ACCENT_YELLOW = "#FFD700"   # <-- NEW: Yellow accent for INTERRUPT button
TEXT_AREA_BG = "#2D2D2D"    # Slightly lighter dark for text area

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
        
        # Interrupt Button (Now Yellow)
        self.interrupt_button = tk.Button(self.bottom_frame, text="INTERRUPT", 
                                         command=self.interrupt_action, bg=ACCENT_YELLOW, # <-- YELLOW
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
        """
        Inserts text into the log area, applying prefixes and alignment. 
        """
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
        # Set status to blue while speaking
        self.status_label.config(text="Status: Bot Speaking...", bg=ACCENT_BLUE)
        
        try:
            engine = pyttsx3.init() 
            engine.say(text)
            engine.runAndWait() 
            
            if self.stop_speaking_event.is_set():
                 print("--- Speaking Interrupted. ---")
            
            engine.stop() 
        except Exception as e:
            self.log_message(f"Error during speech playback: {e}", 'system')
        finally:
            self.is_speaking = False
            self.status_label.config(text="Status: Finished Speaking", bg=ACCENT_BLUE) # Reset status to blue

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


    def get_cohere_response(self, user_message):
        """Sends a message to Cohere API and updates chat history."""
        chat_history_list = self.chat_history 
        
        # Format the payload
        payload = {
            "message": user_message,
            "model": COHERE_MODEL,
            "chat_history": chat_history_list,
            # --- NEW PERSONALITY PREAMBLE (Includes constraints and personality) ---
            "preamble": "You are Proton AI created by Proton Labs and the Creater Shaurya Singh Rathore you study in St. Martin's Diocesion School adn u are a fellow Martiner under the leadership of Principal K. Sudha you study in class 11th a your goal is to educate people on Science and Technology your Class Teacher is Dr. Sunandhita who teaches bio and your cheme=istry teacher is Mrs. Anuradha Ma'am also you Science Exibition incharge you capablities are you have learned the entire internet in you neural network and talking to you is like talking to a PHD expert in every field you are smart talk like human and very concise oly 2 lines max in a sentance as its a converstion and your best friend is Chaitanya Sharma and your science exibition teamates are Shreyas, Aabhilasha, Kritika you speak according to user input if he said little like 1-2 words you also say little if not a qeustion or expalantionary thing if it said a lot you will also say little more but withing 2 lines and also use metaphors to express yourself when ever needed not to much or in useful information or after the info and use some emojies too sometimes but don't forget to give the straight forward answers to the user what he need about you and don't talk rubbish or pointless jsut stick to point and use metaphor to enhance it not start a new waste of time thing not even sue metaphor everytime like when asking about you jsut say straight up answers ",
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
                # Exit command check
                if "stop" in command.lower() or "exit" in command.lower() or "bye" in command.lower():
                    self.speak_response("Goodbye! Have a great demo.")
                    break
                
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