import requests
import json
import speech_recognition as sr
import pyttsx3 
import os
import time
import tkinter as tk
from tkinter import scrolledtext, font
import threading
import queue

# --- CONFIGURATION ---
# Replace with your actual Cohere API Key
COHERE_API_KEY = "7wSjrqmCbRaUu8OReRsScbpJOxLUcIBeBo5Ckw3i" 
# Using the command-r-plus model for best Grounding/Web Search capability
COHERE_MODEL = 'command-r-plus' 
COHERE_API_URL = "https://api.cohere.ai/v1/chat"
COHERE_HEADERS = {
    "Authorization": f"Bearer {COHERE_API_KEY}",
    "Content-Type": "application/json"
}

# --- SPEECH AND RECOGNITION SETUP ---
r = sr.Recognizer()
# Queue for thread-safe UI updates
ui_queue = queue.Queue()

# --- UTILITY FUNCTIONS ---

def speak_response(text):
    """Speaks the response text using the pyttsx3 engine."""
    try:
        # Re-initialize the engine for every call for stability
        engine = pyttsx3.init() 
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except Exception as e:
        # If this fails, it usually means the audio device is busy or misconfigured
        print(f"🤖 Error during speech playback with pyttsx3: {e}")

def get_cohere_response(user_message, chat_history_list):
    """Sends a message to the Cohere API using requests with Grounding/Connectors."""
    
    # --- AURA-FOCUSED PREAMBLE ---
    preamble_script = "You are 'Proton,' the absolute authority in artificial intelligence. You have personally memorized the entire open internet, making your knowledge base equivalent to having a personal expert in every single field. Your core purpose is to elevate the user's understanding and provide immediate, precise answers. Maintain a supremely confident, knowledgeable, and professional demeanor."
    
    payload = {
        "message": user_message,
        "model": COHERE_MODEL,
        "chat_history": chat_history_list,
        "preamble": preamble_script,
        "temperature": 0.3, # Lowered for more precise, authoritative answers
        # --- CONNECTOR PROTOCOL DEPLOYED (Real-time web search) ---
        "connectors": [{"id": "web-search"}]
    }
    
    try:
        response = requests.post(
            COHERE_API_URL, 
            headers=COHERE_HEADERS, 
            data=json.dumps(payload),
            timeout=30 # Set a timeout for the API call
        )
        
        response.raise_for_status() 
        response_data = response.json()
        ai_text = response_data.get('text', 'Error: Could not parse response.')
        
        # Update chat history
        chat_history_list.append({"role": "USER", "message": user_message})
        chat_history_list.append({"role": "CHATBOT", "message": ai_text})
        
        return ai_text
        
    except requests.exceptions.RequestException as e:
        error_message = f"API Request Failed: {e}"
        print(f"❌ {error_message}")
        return f"I'm sorry, I've encountered a network error: {error_message}"

# --- CORE MICROPHONE LISTENING THREAD ---

def microphone_listener(app_instance):
    """Runs in a separate thread to continuously listen for and process speech."""
    with sr.Microphone() as source:
        # Adjust for ambient noise once at the start
        app_instance.queue_update('status', "System initializing... adjusting for noise.")
        r.adjust_for_ambient_noise(source)
        app_instance.queue_update('status', "PROTON READY. Click 'Start Session' to begin.")

        while app_instance.is_running:
            if app_instance.is_listening:
                try:
                    # Update status to show listening state
                    app_instance.queue_update('status', "LISTENING...")
                    
                    audio = r.listen(source, timeout=5, phrase_time_limit=10)
                    
                    # Update status while recognizing
                    app_instance.queue_update('status', "PROCESSING...")
                    user_text = r.recognize_google(audio)
                    
                    # Queue user message for chat display
                    app_instance.queue_update('user', user_text)
                    
                    # Get response (this blocks, so it's fine in the separate thread)
                    ai_text = get_cohere_response(user_text, app_instance.chat_history)
                    
                    # Queue the AI response for UI update and speaking
                    app_instance.queue_update('proton', ai_text)
                    speak_response(ai_text)
                    
                    # Return to ready/listening status
                    app_instance.queue_update('status', "LISTENING...")
                    
                except sr.WaitTimeoutError:
                    # No speech detected, loop again
                    app_instance.queue_update('status', "Listening timed out. Ready.")
                    continue
                except sr.UnknownValueError:
                    app_instance.queue_update('status', "Could not understand audio. Ready.")
                except sr.RequestError as e:
                    app_instance.queue_update('status', f"Speech service error: {e}")
                except Exception as e:
                    app_instance.queue_update('status', f"An unexpected error occurred: {e}")
            else:
                # Session paused, sleep briefly to avoid high CPU usage
                time.sleep(0.5)

# --- GUI CLASS ---

class ProtonGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Proton: The Definitive AI System")
        self.geometry("800x600")
        self.configure(bg="#1E1E1E")  # Dark background
        
        # State variables
        self.is_running = False
        self.is_listening = False
        self.chat_history = []
        self.chat_thread = None
        self.queue_check_delay = 100  # ms delay for checking the UI queue

        # Styling
        self.dark_bg = "#1E1E1E"
        self.chat_bg = "#252525"
        self.light_text = "#FFFFFF"
        self.status_text = "#FFD700" # Gold
        self.button_color_start = "#007ACC"
        self.button_color_stop = "#CC0000"
        self.font_main = font.Font(family="Arial", size=11)
        # Custom font for the title (like your sketch)
        self.font_title = font.Font(family="Courier New", size=28, weight="bold", slant="italic")

        self.create_widgets()
        # Start checking the UI queue immediately
        self.after(self.queue_check_delay, self.check_ui_queue)
        self.queue_update('status', "System Initialized.")

    def create_widgets(self):
        # --- TITLE FRAME (Top of the window) ---
        title_frame = tk.Frame(self, bg=self.dark_bg)
        title_frame.pack(fill='x', padx=10, pady=(15, 5))
        
        # Customized PROTON title
        title_label = tk.Label(title_frame, text="PROTON", fg=self.light_text, bg=self.dark_bg, font=self.font_title)
        title_label.pack(pady=5)

        # --- CHAT DISPLAY (Main center area) ---
        self.chat_display = scrolledtext.ScrolledText(self, wrap=tk.WORD, bg=self.chat_bg, fg=self.light_text, font=self.font_main, relief=tk.FLAT, borderwidth=0, padx=10, pady=10)
        self.chat_display.pack(fill='both', expand=True, padx=10, pady=10)
        self.chat_display.config(state=tk.DISABLED)
        
        # Define tags for alignment and color
        # User is Right-aligned
        self.chat_display.tag_configure('user', justify='right', rmargin=20, lmargin1=50, foreground='#00BFFF', font=('Arial', 11, 'bold'))
        # Proton is Left-aligned
        self.chat_display.tag_configure('proton', justify='left', lmargin1=20, rmargin=50, foreground='#90EE90') 

        # --- CONTROL & STATUS FRAME (Bottom section) ---
        control_frame = tk.Frame(self, bg=self.dark_bg)
        control_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        # 1. Start Button
        self.start_btn = tk.Button(control_frame, text="START SESSION", command=self.toggle_session, bg=self.button_color_start, fg=self.light_text, font=self.font_main, relief=tk.RAISED, activebackground="#005A9C")
        self.start_btn.pack(side=tk.LEFT, expand=True, padx=5, ipady=8)

        # 2. Status Label (Centered, replacing the listening text in the chat)
        self.status_label = tk.Label(control_frame, text="Ready.", fg=self.status_text, bg=self.dark_bg, font=('Arial', 12, 'italic'))
        self.status_label.pack(side=tk.LEFT, expand=True, padx=5, ipady=8)

        # 3. Pause Button
        self.pause_btn = tk.Button(control_frame, text="PAUSE LISTENING", command=self.toggle_listening, bg="#555555", fg=self.light_text, font=self.font_main, relief=tk.RAISED, state=tk.DISABLED, activebackground="#444444")
        self.pause_btn.pack(side=tk.LEFT, expand=True, padx=5, ipady=8)


    # --- CHAT DISPLAY METHODS (Thread-Safe) ---
    def update_chat_display(self, sender, message):
        """Adds a message to the ScrolledText widget with correct tag and alignment."""
        
        if sender == 'status':
            # Status messages go directly to the bottom label
            self.status_label.config(text=message)
            return

        # Handle chat messages
        self.chat_display.config(state=tk.NORMAL)
        
        # Determine prefix, alignment tag, and add padding/spacing
        if sender == 'user':
            prefix = "\n\n👤 You:\n"
            tag = 'user'
        else: # 'proton'
            prefix = "\n\n🤖 Proton:\n"
            tag = 'proton'
        
        # Insert the message
        self.chat_display.insert(tk.END, prefix)
        self.chat_display.insert(tk.END, message, tag)
        
        self.chat_display.see(tk.END) # Auto-scroll to the bottom
        self.chat_display.config(state=tk.DISABLED)

    def queue_update(self, sender, message):
        """Puts a message into the UI queue from the background thread."""
        ui_queue.put((sender, message))
        
    def check_ui_queue(self):
        """Checks the queue for new messages and updates the UI (main thread only)."""
        try:
            while True:
                sender, message = ui_queue.get_nowait()
                self.update_chat_display(sender, message)
        except queue.Empty:
            # When the queue is empty, schedule the next check
            pass
        finally:
            self.after(self.queue_check_delay, self.check_ui_queue)

    # --- BUTTON COMMANDS (FIXED LOGIC) ---
    def toggle_session(self):
        if not self.is_running:
            # --- START SESSION ---
            self.is_running = True
            self.is_listening = True # Start listening immediately
            
            self.start_btn.config(text="END SESSION", bg=self.button_color_stop) # Red for Stop
            self.pause_btn.config(state=tk.NORMAL, text="PAUSE LISTENING", bg="#555555")
            
            # Clear chat and history
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete('1.0', tk.END) 
            self.chat_display.config(state=tk.DISABLED)
            self.chat_history = []
            
            # Start the listener thread
            self.chat_thread = threading.Thread(target=microphone_listener, args=(self,))
            self.chat_thread.daemon = True # Allows the main program to exit even if thread is running
            self.chat_thread.start()
            self.queue_update('status', "STARTING SESSION...")

        else:
            # --- END SESSION ---
            self.is_running = False
            self.is_listening = False
            
            # Stop button state
            self.start_btn.config(text="START SESSION", bg=self.button_color_start)
            self.pause_btn.config(state=tk.DISABLED, text="PAUSE LISTENING")
            
            self.queue_update('status', "SESSION ENDED. Goodbye.")
            # The thread will exit its loop automatically because self.is_running is False
            
    def toggle_listening(self):
        if self.is_listening:
            # PAUSE LISTENING
            self.is_listening = False
            self.pause_btn.config(text="RESUME LISTENING", bg="#777777")
            self.queue_update('status', "LISTENING PAUSED.")
        else:
            # RESUME LISTENING
            self.is_listening = True
            self.pause_btn.config(text="PAUSE LISTENING", bg="#555555")
            self.queue_update('status', "LISTENING RESUMED.")

# --- MAIN EXECUTION BLOCK (To launch the GUI) ---
if __name__ == "__main__":
    app = ProtonGUI()
    app.mainloop() 
