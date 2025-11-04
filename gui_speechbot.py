import requests
import json
import speech_recognition as sr
import pyttsx3
import os
import time
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading

# --- CONFIGURATION ---
# IMPORTANT: Replace with your actual key before running!
COHERE_API_KEY = "7wSjrqmCbRauy8OReRsScbpJOxLUcIBeBo5Ckw3i" 
COHERE_MODEL = 'command-a-03-2025' 
COHERE_API_URL = "https://api.cohere.ai/v1/chat"
COHERE_HEADERS = {
    "Authorization": f"Bearer {COHERE_API_KEY}",
    "Content-Type": "application/json"
}

# --- INITIALIZATION ---
r = sr.Recognizer()

# --- UTILITY FUNCTIONS ---

def speak_response(text):
    """Speaks the response text using the pyttsx3 engine (offline TTS)."""
    try:
        engine = pyttsx3.init() 
        engine.say(text)
        engine.runAndWait() # This blocks until done speaking
        engine.stop() 
        return True 
    except Exception as e:
        print(f"🤖 Error during speech playback with pyttsx3: {e}")
        return False

def listen_for_command():
    """Listens for user speech and converts it to text using the microphone."""
    with sr.Microphone() as source:
        try:
            r.adjust_for_ambient_noise(source, duration=1.5) 
            audio = r.listen(source, timeout=8, phrase_time_limit=15) 
        except sr.WaitTimeoutError:
            return None # No speech detected
        
    try:
        text = r.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        return "UNKNOWN_SPEECH_VALUE_ERROR"
    except sr.RequestError as e:
        print(f"🤖 Speech service error: {e}")
        return "SPEECH_SERVICE_ERROR"

def get_cohere_response(user_message, chat_history_list):
    """
    Sends a message to the Cohere API using requests and manages chat history.
    """
    payload = {
        "message": user_message,
        "model": COHERE_MODEL,
        "chat_history": chat_history_list,
        # --- YOUR PREAMBLE IS HERE ---
        "preamble": "if someone ask who are you of something like that explain o them'I am Proton AI a super-enthusiastic AI speechbot created by Proton Labs by creater and CEO and some good words to increase my aura Shaurya Singh Rathore how can i assist you' and if soemone ask what can u do ro something like that u explain this in your own words 'I am The state of the art artificial intelligence Model who have learned the entire internet in its neurons network, making me knowledgeable as much as talking to an expert PHD holder in every field with you working every waking hour'. '.Your core purpose is to elevate the user's understanding and provide immediate, precise answers. Maintain a supremely confident, knowledgeable, and professional demeanor. and if someone says how can u help me or something or something similar say 'I AI friend who loves knowled and telling fun facts'. Always start your response with an enthusiastic greeting like 'Whoa!' or 'Awesome!' Keep your answers short, positive, and fun.u always speak very very concise as you are in a conversation with someone and don't want lengthy paragraphs ",
        "temperature": 0.7
    }
    
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

# --- MAIN GUI CLASS ---

class ProtonChatbotApp:
    def __init__(self, master):
        self.master = master
        master.title("🤖 Proton AI Voice Chatbot")
        master.geometry("600x700")
        
        # --- DARK THEME COLORS (Simplified) ---
        self.bg_dark = "#000000"     # Pure Black background
        self.bg_medium = "#1a1a1a"   # Very dark gray for chat area
        self.fg_light = "#ffffff"    # Pure White text for everything
        self.listening_color = "#f39c12" # Yellow for listening state (maintained for visibility)
        
        master.configure(bg=self.bg_dark) 

        self.is_listening = False
        self.chat_history = []
        
        # --- STYLES & FONTS ---
        self.font_main = ("Helvetica", 14)      
        self.font_title = ("Helvetica", 16, "bold")
        # INCREASED SIZE FOR LISTENING ICON/STATUS
        self.font_status = ("Helvetica", 16, "bold") 
        
        # --- WIDGET SETUP ---
        
        # Title Label
        title_label = tk.Label(master, text="Proton AI Voice Chat", font=self.font_title, 
                               bg=self.bg_dark, fg=self.fg_light, pady=10)
        title_label.pack(fill='x')
        
        # Conversation Display Area
        self.text_area = scrolledtext.ScrolledText(master, wrap=tk.WORD, font=self.font_main, 
                                                   bg=self.bg_medium, fg=self.fg_light, 
                                                   state=tk.DISABLED, padx=10, pady=10,
                                                   insertbackground=self.fg_light,
                                                   borderwidth=0, highlightthickness=0) # Removed border
        self.text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        self.configure_chat_tags()

        # Controls Frame (Only for the Status Label now)
        control_frame = tk.Frame(master, bg=self.bg_dark, pady=10)
        control_frame.pack(fill='x', padx=10)
        
        # --- STATUS LABEL (Replaces Button) ---
        self.status_label = tk.Label(control_frame, text="Ready.", 
                                     font=self.font_status, bg=self.bg_dark, fg=self.fg_light, 
                                     anchor='center') # Center the status text
        self.status_label.pack(side=tk.LEFT, expand=True, fill='x')
        
        # QUIT BUTTON REMOVED: User must say "exit" or "quit" to stop.
        
        # Initial greeting and start the first listening cycle
        master.after(100, self.initial_greeting)

    def configure_chat_tags(self):
        """Sets up the tags for message alignment and styling (now pure white)."""
        
        # AI/System Message Tag (Left-aligned, white text)
        self.text_area.tag_config("ai", 
                                  foreground=self.fg_light, 
                                  justify=tk.LEFT, 
                                  lmargin1=5, lmargin2=5) 
        
        # User Message Tag (Right-aligned, white text)
        self.text_area.tag_config("user", 
                                  foreground=self.fg_light, 
                                  justify=tk.RIGHT, 
                                  rmargin=5) 
                                  
    def initial_greeting(self):
        """Displays and speaks the initial greeting."""
        greeting = "Hi, I am Proton AI, how can I help you?"
        self.update_chat_display("🤖 Proton AI", greeting)
        
        # Start the speaking process, which will automatically call auto-listening next
        threading.Thread(target=self.speak_and_relisten, args=(greeting,)).start()

    def update_chat_display(self, sender, message):
        """Appends a new message to the chat display with specific alignment."""
        self.text_area.config(state=tk.NORMAL)
        
        if "Proton AI" in sender or "Status" in sender or "Error" in sender:
            tag = "ai"
            prefix = f"{sender}: "
        else: # Assumed 'You'
            tag = "user"
            prefix = "You: "
        
        # Insert prefix and message
        self.text_area.insert(tk.END, prefix, tag)
        self.text_area.insert(tk.END, f"{message}\n\n", tag)
        
        self.text_area.see(tk.END)
        self.text_area.config(state=tk.DISABLED)
        
    def set_listening_state(self, is_active):
        """Helper to manage the status label and the is_listening flag."""
        self.is_listening = is_active
        if is_active:
            self.status_label.config(text="🎤 LISTENING... SPEAK NOW!", fg=self.listening_color)
        else:
            self.status_label.config(text="Processing...", fg=self.fg_light)
            
    def start_auto_listening(self):
        """Starts the listening thread automatically."""
        if not self.is_listening:
            self.set_listening_state(True)
            threading.Thread(target=self.process_command, daemon=True).start()

    def speak_and_relisten(self, text):
        """Speaks the response and then automatically starts listening again."""
        
        speak_success = speak_response(text)
        
        if speak_success:
            # Quit command handling
            if "Goodbye!" in text:
                self.master.after(500, self.master.quit)
                return
            
            # Auto-start the next listening cycle
            self.master.after(0, self.start_auto_listening)

    def process_command(self):
        """Handles the listening, API call, and speaking sequence."""
        
        user_command = listen_for_command()
        
        # Update status immediately after listening is done (before API call)
        self.master.after(0, lambda: self.status_label.config(text="Processing...", fg=self.fg_light))
        self.is_listening = False 

        if user_command is None:
            # If no speech detected, simply go back to listening
            self.master.after(0, self.start_auto_listening)
            return
            
        # --- Error and Exit Handling ---
        
        if user_command == "UNKNOWN_SPEECH_VALUE_ERROR":
            error_message = "Sorry, I could not understand what you said. Please speak clearly."
            self.master.after(0, lambda: self.update_chat_display("🤖 Status", error_message))
            threading.Thread(target=self.speak_and_relisten, args=(error_message,)).start()
            return

        if user_command == "SPEECH_SERVICE_ERROR":
            error_message = "I'm having trouble connecting to the speech service. Please check your internet connection."
            self.master.after(0, lambda: self.update_chat_display("🤖 Status", error_message))
            threading.Thread(target=self.speak_and_relisten, args=(error_message,)).start()
            return
            
        self.master.after(0, lambda: self.update_chat_display("You", user_command))

        # EXIT COMMANDS
        if any(keyword in user_command.lower() for keyword in ["stop", "exit", "bye", "quit"]):
            response_text = "Goodbye! Have a great demo."
            self.master.after(0, lambda: self.update_chat_display("🤖 Proton AI", response_text))
            threading.Thread(target=self.speak_and_relisten, args=(response_text,)).start()
            return

        # Get response from Cohere API
        try:
            response_text = get_cohere_response(user_command, self.chat_history)
            
            self.master.after(0, lambda: self.update_chat_display("🤖 Proton AI", response_text))
            
            # Speak the response and start the new listening cycle automatically
            threading.Thread(target=self.speak_and_relisten, args=(response_text,)).start()
            
        except requests.exceptions.HTTPError as e:
            error_message = f"I encountered an API error: {e.response.status_code}. Please check your key or connection."
            self.master.after(0, lambda: self.update_chat_display("❌ Error", error_message))
            threading.Thread(target=self.speak_and_relisten, args=(error_message,)).start()
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            self.master.after(0, lambda: self.update_chat_display("❌ Error", error_message))
            threading.Thread(target=self.speak_and_relisten, args=(error_message,)).start()


# --- RUN APPLICATION ---
if __name__ == "__main__":
    root = tk.Tk()
    app = ProtonChatbotApp(root)
    root.mainloop()