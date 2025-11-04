import requests  # <-- Added requests
import json      # <-- Added json
import speech_recognition as sr
import pyttsx3 
import os
import time

# --- CONFIGURATION ---
# Your hardcoded key is used as you provided it.
COHERE_API_KEY = "7wSjrqmCbRauy8OReRsScbpJOxLUcIBeBo5Ckw3i" 
COHERE_MODEL = 'command-a-03-2025' 
# Define the Cohere API endpoint we will "request"
COHERE_API_URL = "https://api.cohere.ai/v1/chat"
# Define the headers for our request
COHERE_HEADERS = {
    "Authorization": f"Bearer {COHERE_API_KEY}",
    "Content-Type": "application/json"
}

# --- INITIALIZATION ---

# No Cohere Client initialization needed anymore
print("Initializing Speech Recognition and TTS...")
r = sr.Recognizer()
# The global engine initialization was removed to fix the cutoff issue
print("Hello! Voice Chatbot Initialized.")

# --- UTILITY FUNCTIONS ---

def speak_response(text):
    """Speaks the response text using the pyttsx3 engine (offline TTS)."""
    print(f"\n🤖 Cohere: {text}")
    try:
        # FIX: Re-initialize the engine for every call to prevent it from hanging
        engine = pyttsx3.init() 
        engine.say(text)
        engine.runAndWait() # This processes the speech and blocks until done
        engine.stop()       # Explicitly stop the local instance after speaking
    except Exception as e:
        print(f"🤖 Error during speech playback with pyttsx3: {e}")

def listen_for_command():
    """Listens for user speech and converts it to text using the microphone."""
    with sr.Microphone() as source:
        print("\n\n🎤 Listening... Speak now!")
        
        r.adjust_for_ambient_noise(source, duration=1.5) 
        
        try:
            audio = r.listen(source, timeout=8, phrase_time_limit=15) 
        except sr.WaitTimeoutError:
            print("--- No speech detected. ---")
            return None 

    try:
        text = r.recognize_google(audio)
        print(f"🎤 You said: {text}")
        return text
    except sr.UnknownValueError:
        print("🤖 Could not understand audio. Please speak clearly.")
        return None
    except sr.RequestError as e:
        print(f"🤖 Speech service error (Check internet connection): {e}")
        return None

# --- NEW HELPER FUNCTION FOR REQUESTS ---
def get_cohere_response(user_message, chat_history_list):
    """
    Sends a message to the Cohere API using requests and manages chat history.
    This single function replaces co.chat() and chat_session.send()
    """
    
    # Format the payload for the requests call, based on Cohere's API docs
    payload = {
        "message": user_message,
        "model": COHERE_MODEL,
        "chat_history": chat_history_list, # Pass the history
        # --- NEW PERSONALITY PREAMBLE (Updated to use 'Proton') --
        "preamble": "if someone ask who are you of something like that explain o them'I am Proton AI a super-enthusiastic AI speechbot created by Proton Labs by creater and CEO and some good words to increase my aura Shaurya Singh Rathore how can i assist you' and if soemone ask what can u do ro something like that u explain this in your own words 'I am The state of the art artificial intelligence Model who have learned the entire internet in its neurons network, making me knowledgeable as much as talking to an expert PHD holder in every field with you working every waking hour'. '.Your core purpose is to elevate the user's understanding and provide immediate, precise answers. Maintain a supremely confident, knowledgeable, and professional demeanor. and if someone says how can u help me or something like similar say 'I AI friend who loves knowled and telling fun facts'. Always start your response with an enthusiastic greeting like 'Whoa!' or 'Awesome!' Keep your answers short, positive, and fun.u always speak very very concise as you are in a conversation with someone and don't want lengthy paragraphs ",
        "temperature": 0.7
    }
    
    # Make the POST request to the Cohere API
    response = requests.post(
        COHERE_API_URL, 
        headers=COHERE_HEADERS, 
        data=json.dumps(payload)
    )
    
    # Raise an error if the request was bad (e.g., 401 Unauthorized, 400 Bad Request)
    response.raise_for_status() 
    
    # Parse the JSON response
    response_data = response.json()
    
    # Extract the text from the response
    ai_text = response_data.get('text', 'Error: Could not parse response.')
    
    # IMPORTANT: Update the chat history for the next turn
    # 1. Add the user's message to the history
    chat_history_list.append({"role": "USER", "message": user_message})
    # 2. Add the bot's response to the history
    chat_history_list.append({"role": "CHATBOT", "message": ai_text})
    
    return ai_text

# --- MAIN CHATBOT FUNCTION ---
def run_chatbot():
    """Main conversational loop."""
    # We must manually create a list to store the chat history.
    chat_history = []

    print("--- Cohere Voice Chatbot Ready ---")
    
    # --- STARTUP LOGIC MODIFIED ---
    
    # 1. Directly speak the desired greeting (No API call needed for intro)
    speak_response("Hi, I am Proton AI, how can I help you?")

    # The conversation loop now starts immediately after the simple greeting.
    while True:
        command = listen_for_command()
        
        if command:
            # Exit command
            if "stop" in command.lower() or "exit" in command.lower() or "bye" in command.lower():
                speak_response("Goodbye! Have a great demo.")
                break
            
            try:
                # Use our helper function to get the next response and update history
                response_text = get_cohere_response(command, chat_history)
                
                # Speak the Cohere response
                speak_response(response_text)
                
            # Catch errors from the 'requests' library
            except requests.exceptions.HTTPError as e:
                error_message = f"I encountered an API error: {e.response.status_code}. Please check your connection."
                print(error_message)
                speak_response(error_message)
            except Exception as e:
                error_message = f"An unexpected error occurred: {e}"
                print(error_message)
                speak_response(error_message)

if __name__ == "__main__":
    run_chatbot()
