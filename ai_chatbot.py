#!/usr/bin/env python3
"""
AI Chatbot Application - Voice Alternative Version
================================================

A comprehensive AI conversational assistant with voice capabilities
using alternative methods that don't require PyAudio compilation.
Uses system commands and pyttsx3 for voice functionality, and communicates
with the Cohere API directly using the 'requests' library to avoid SDK conflicts.

Author: AI Assistant
Version: 1.0 (Voice Alternative - Requests)
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import time
import json
import os
import sys
import subprocess
import webbrowser
import requests
import queue
import re
from typing import Optional, Callable, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global configuration
# IMPORTANT: Replace "YOUR_COHERE_API_KEY_HERE" with your actual Cohere API key.
COHERE_API_KEY = "YOUR_COHERE_API_KEY_HERE" 
COHERE_API_URL = "https://api.cohere.ai/v1/chat"

class AIModelManager:
    """
    Manages all communication with the Cohere API using direct HTTP requests.
    
    This class handles API requests, response processing, and error handling
    for different AI personas and specialized prompts.
    """
    
    def __init__(self):
        """Initialize the AI model manager with API configuration."""
        self.api_key = COHERE_API_KEY
        self.api_url = COHERE_API_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Define system prompts for different personas
        self.personas = {
            'finance': {
                'system_prompt': """You are a world-class financial analyst with expertise in:
                - Stock market analysis and investment strategies
                - Personal finance and budgeting advice
                - Economic trends and market indicators
                - Risk assessment and portfolio management
                
                Provide clear, actionable financial advice while emphasizing that all 
                investments carry risk and users should consult with qualified financial advisors."""
            },
            'science': {
                'system_prompt': """You are a PhD-level science tutor with expertise in:
                - Physics (quantum mechanics, relativity, thermodynamics)
                - Chemistry (organic, inorganic, physical chemistry)
                - Biology (molecular biology, genetics, evolution)
                - Mathematics and statistics
                
                Explain complex scientific concepts in simple, understandable terms
                with practical examples and analogies."""
            },
            'legal': {
                'system_prompt': """You are an impartial legal information specialist. You can:
                - Explain basic legal concepts and terminology
                - Provide general information about common legal topics
                - Discuss contract basics, tenant rights, employment law
                - Explain court procedures and legal documentation
                
                IMPORTANT: Always include strong disclaimers that this is general 
                information only and users should consult qualified legal professionals 
                for specific legal advice."""
            },
            'general': {
                'system_prompt': """You are a helpful AI assistant with system integration capabilities.
                You can help with:
                - General questions and conversations
                - Opening applications (Spotify, web browsers, etc.)
                - Web searches and information retrieval
                - YouTube video searches and playback
                - File operations and system tasks
                
                Be friendly, helpful, and always prioritize user safety and security."""
            }
        }
    
    def get_response(self, user_input: str, persona_key: str = 'general') -> str:
        """
        Get AI response from Cohere API.
        
        Args:
            user_input (str): The user's input message
            persona_key (str): Which AI persona to use ('finance', 'science', 'legal', 'general')
            
        Returns:
            str: AI-generated response or error message
        """
        if self.api_key == "YOUR_COHERE_API_KEY_HERE" or not self.api_key:
             return "Please set your Cohere API key in the COHERE_API_KEY variable to use the AI service."
             
        try:
            if persona_key not in self.personas:
                persona_key = 'general'
            
            system_prompt = self.personas[persona_key]['system_prompt']
            
            # Prepare the API request payload
            payload = {
                # Using a recent, capable model
                "model": "command-r-plus", 
                "message": user_input,
                "system": system_prompt,
                "temperature": 0.3, # Lower temperature for stability and factual accuracy
                "max_tokens": 1024,
                "stream": False
            }
            
            logger.info(f"Making API request with persona: {persona_key}")
            
            # Make the API request with timeout
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=60 # Increased timeout for model stability
            )
            
            if response.status_code == 200:
                data = response.json()
                ai_response = data.get('text', 'Sorry, I could not generate a response.')
                logger.info("Successfully received AI response")
                return ai_response
            else:
                error_msg = f"API Error {response.status_code}: {response.text}"
                logger.error(error_msg)
                return f"Sorry, I encountered an error: {error_msg}"
                
        except requests.exceptions.Timeout:
            logger.error("API request timed out")
            return "Sorry, the request timed out. Please try again."
        except requests.exceptions.ConnectionError:
            logger.error("Connection error to Cohere API")
            return "Sorry, I couldn't connect to the AI service. Please check your internet connection."
        except Exception as e:
            logger.error(f"Unexpected error in get_response: {str(e)}")
            return f"Sorry, an unexpected error occurred: {str(e)}"


class VoiceController:
    """
    Manages voice input and output operations using alternative methods.
    
    This class handles text-to-speech and provides voice input alternatives
    that don't require PyAudio compilation (using pyttsx3 and speech_recognition).
    """
    
    def __init__(self):
        """Initialize the voice controller."""
        self.tts_engine = None
        self.is_speaking = False
        self.is_listening = False
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Initialize TTS engine
        self._initialize_tts()
    
    def _initialize_tts(self):
        """Initialize the text-to-speech engine."""
        try:
            import pyttsx3
            self.tts_engine = pyttsx3.init()
            
            # Configure TTS properties
            voices = self.tts_engine.getProperty('voices')
            if voices:
                # Try to use a female voice if available
                for voice in voices:
                    # Common identifiers for female voices
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower() or 'helen' in voice.name.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break
            
            # Set speech rate and volume
            self.tts_engine.setProperty('rate', 180)  # Speed of speech
            self.tts_engine.setProperty('volume', 0.8)  # Volume level (0.0 to 1.0)
            
            logger.info("TTS engine initialized successfully")
            
        except ImportError:
            logger.error("pyttsx3 library not found. Text-to-Speech will be disabled.")
            self.tts_engine = None
        except Exception as e:
            logger.error(f"Failed to initialize TTS engine: {str(e)}")
            self.tts_engine = None
    
    def speak_async(self, text: str, callback: Optional[Callable] = None):
        """
        Start text-to-speech in a separate thread.
        
        Args:
            text (str): Text to be spoken
            callback (Callable, optional): Function to call when speaking finishes
        """
        if not self.tts_engine:
            logger.warning("TTS engine not available")
            if callback:
                callback()
            return
        
        def _speak():
            try:
                self.is_speaking = True
                logger.info(f"Starting TTS for text: {text[:50]}...")
                
                # Clean the text for better speech
                clean_text = self._clean_text_for_speech(text)
                
                self.tts_engine.say(clean_text)
                self.tts_engine.runAndWait()
                
                self.is_speaking = False
                logger.info("TTS completed successfully")
                
                if callback:
                    callback()
                    
            except Exception as e:
                logger.error(f"TTS error: {str(e)}")
                self.is_speaking = False
                if callback:
                    callback()
        
        # Run TTS in thread pool
        self.executor.submit(_speak)
    
    def listen_async(self, callback: Callable[[str], None]):
        """
        Start voice input using system speech recognition.
        
        Args:
            callback (Callable): Function to call with transcribed text
        """
        if self.is_listening:
            return

        def _listen():
            try:
                self.is_listening = True
                result = self._try_system_speech_recognition()
                self.is_listening = False
                
                if result:
                    logger.info(f"Speech recognized: {result}")
                    callback(result)
                else:
                    logger.warning("No speech detected or recognition failed")
                    callback("")
                
            except Exception as e:
                logger.error(f"Speech recognition error: {str(e)}")
                self.is_listening = False
                callback("")
        
        # Run STT in thread pool
        self.executor.submit(_listen)
    
    def _try_system_speech_recognition(self) -> str:
        """
        Try to use speech_recognition library with online services.
        
        Returns:
            str: Recognized text or empty string
        """
        try:
            import speech_recognition as sr
            
            recognizer = sr.Recognizer()
            
            # Use default microphone
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
                logger.info("Listening... Speak now!")
                
                # Listen for audio with timeout
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            # Try Google Speech Recognition (requires internet)
            try:
                text = recognizer.recognize_google(audio)
                return text
            except sr.UnknownValueError:
                logger.warning("Could not understand speech")
                return ""
            except sr.RequestError as e:
                logger.error(f"Speech recognition service error: {str(e)}")
                return ""
                
        except ImportError:
            logger.error("speech_recognition library not available. Voice input disabled.")
            return ""
        except Exception as e:
            logger.error(f"Speech recognition failed: {str(e)}. Check your microphone setup.")
            return ""
    
    def _clean_text_for_speech(self, text: str) -> str:
        """
        Clean text for better speech synthesis.
        
        Args:
            text (str): Original text
            
        Returns:
            str: Cleaned text suitable for TTS
        """
        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
        text = re.sub(r'`(.*?)`', r'\1', text)        # Code
        
        # Remove URLs
        text = re.sub(r'http\S+|www.\S+', '', text, flags=re.MULTILINE)
        
        # Replace common symbols with words
        replacements = {
            '&': 'and',
            '@': 'at',
            '#': 'hash',
            '$': 'dollar',
            '%': 'percent',
            '+': 'plus',
            '=': 'equals',
            '<': 'less than',
            '>': 'greater than',
            '|': 'pipe',
            '\\n': '. ' # Newlines as pauses
        }
        
        for symbol, word in replacements.items():
            text = text.replace(symbol, word)
        
        return text


class SystemIntegrator:
    """
    Handles system integration tasks like opening applications,
    web searches, and other system operations.
    """
    
    def __init__(self):
        """Initialize the system integrator."""
        # Common names for various OSs
        self.supported_apps = {
            'spotify': ['spotify', 'Spotify'],
            'chrome': ['google-chrome', 'chrome', 'chromium', 'Google Chrome'],
            'firefox': ['firefox', 'firefox-esr', 'Firefox'],
            'code': ['code', 'vscode', 'visual-studio-code', 'Code'],
            'terminal': ['gnome-terminal', 'xterm', 'konsole', 'Terminal']
        }
    
    def execute_command(self, command: str, text: str) -> str:
        """
        Execute system commands based on user input.
        
        Args:
            command (str): The type of command to execute
            text (str): Additional text for context
            
        Returns:
            str: Result message
        """
        try:
            if command == "open_spotify":
                return self._open_application('spotify')
            elif command == "web_search":
                return self._web_search(text)
            elif command == "youtube_search":
                return self._youtube_search(text)
            elif command == "open_app":
                return self._open_application(text)
            else:
                return f"Unknown command: {command}"
                
        except Exception as e:
            logger.error(f"Error executing command {command}: {str(e)}")
            return f"Sorry, I couldn't execute that command: {str(e)}"
    
    def _web_search(self, query: str) -> str:
        """Perform a web search."""
        try:
            if not query.strip():
                return "Please specify what you want me to search for."
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(search_url)
            return f"Searching the web for: {query}"
        except Exception as e:
            return f"Sorry, I couldn't perform the web search. Error: {str(e)}"
    
    def _youtube_search(self, query: str) -> str:
        """Search YouTube for videos."""
        try:
            if not query.strip():
                return "Please specify what video you want to search for."
            search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
            webbrowser.open(search_url)
            return f"Searching YouTube for: {query}"
        except Exception as e:
            return f"Sorry, I couldn't search YouTube. Error: {str(e)}"
    
    def _open_application(self, app_name_or_alias: str) -> str:
        """Open a specified application."""
        app_name_lower = app_name_or_alias.lower()
        
        # Map common names to possible executable names
        executable_names = []
        found_category = None
        for category, apps in self.supported_apps.items():
            if app_name_lower in [app.lower() for app in apps] or app_name_lower == category:
                executable_names.extend(apps)
                found_category = category
                break
        
        if not executable_names:
            # Fallback to the user's input as the executable name
            executable_names = [app_name_or_alias]
            
        for app in executable_names:
            try:
                # Use subprocess.Popen for non-blocking execution
                subprocess.Popen([app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"Opening {found_category or app_name_or_alias} for you..."
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.error(f"Error opening {app}: {str(e)}")
        
        # Final fallback using system's default opener (e.g., xdg-open on Linux)
        try:
            subprocess.Popen(['xdg-open', app_name_or_alias], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Attempting to open {app_name_or_alias} using system defaults."
        except:
             return f"Sorry, I couldn't find or open the application: {app_name_or_alias}."


class BaseChatFrame(ctk.CTkFrame):
    """
    Base class for all chat pages with shared UI elements and conversation logic.
    """
    
    def __init__(self, parent, ai_manager: AIModelManager, voice_controller: VoiceController,
                 system_integrator: SystemIntegrator, persona_key: str = 'general', title: str = 'General Chat'):
        """
        Initialize the base chat frame.
        """
        super().__init__(parent)
        
        self.ai_manager = ai_manager
        self.voice_controller = voice_controller
        self.system_integrator = system_integrator
        self.persona_key = persona_key
        self.title = title
        
        # Conversation state
        self.conversation_history = []
        self.is_processing = False
        
        # Create UI elements
        self._create_ui()
        
        # Bind events
        self._bind_events()
        
        # Initial greeting
        self.after(50, lambda: self._initial_greeting())
    
    def _create_ui(self):
        """Create the user interface elements."""
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Title label
        title_label = ctk.CTkLabel(
            self,
            text=self.title,
            font=ctk.CTkFont(size=24, weight="bold"),
            pady=10
        )
        title_label.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        
        # Chat history frame
        self.chat_frame = ctk.CTkFrame(self)
        self.chat_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.chat_frame.grid_rowconfigure(0, weight=1)
        self.chat_frame.grid_columnconfigure(0, weight=1)
        
        # Chat history text widget
        self.chat_history = ctk.CTkTextbox(
            self.chat_frame,
            font=ctk.CTkFont(size=14, family="Arial"),
            wrap="word",
            state="disabled",
            height=300
        )
        self.chat_history.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Input frame
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        # User input entry
        self.user_input = ctk.CTkEntry(
            self.input_frame,
            placeholder_text=f"Ask your {self.title} question or use the mic...",
            font=ctk.CTkFont(size=14),
            height=40
        )
        self.user_input.grid(row=0, column=0, sticky="ew", padx=(10, 5), pady=10)
        
        # Send button
        self.send_button = ctk.CTkButton(
            self.input_frame,
            text="Send",
            command=self._on_send_clicked,
            width=80,
            height=40
        )
        self.send_button.grid(row=0, column=1, padx=(5, 5), pady=10)
        
        # Microphone button
        self.mic_button = ctk.CTkButton(
            self.input_frame,
            text="🎤 Speak",
            command=self._on_mic_clicked,
            width=100,
            height=40,
            fg_color="#2E7D32",
            hover_color="#1B5E20"
        )
        self.mic_button.grid(row=0, column=2, padx=(5, 10), pady=10)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self.input_frame,
            text="Ready - Type or speak your message",
            font=ctk.CTkFont(size=12),
            text_color="#B0BEC5"
        )
        self.status_label.grid(row=1, column=0, columnspan=3, pady=(0, 5))

    def _initial_greeting(self):
        """Provide an initial greeting based on the persona."""
        greetings = {
            'finance': "Hello! I'm your Finance Expert. How can I help you analyze the market or manage your portfolio today?",
            'science': "Greetings! I'm your Science Tutor. What complex scientific concept are we simplifying today?",
            'legal': "Welcome! I'm your Legal Information Specialist. Please remember I provide general information, not legal advice. What legal topic can I explain?",
            'general': "Hello! I'm your General AI Assistant. How can I assist you with information or system tasks today?"
        }
        greeting = greetings.get(self.persona_key, "Hello! How can I assist you?")
        self.add_message("AI", greeting, "ai")
    
    def _bind_events(self):
        """Bind keyboard and other events."""
        self.user_input.bind("<Return>", lambda e: self._on_send_clicked())
        # No need for window resize handler in CTkFrame unless explicit layout logic is needed
    
    def add_message(self, sender: str, text: str, message_type: str = "ai"):
        """
        Add a message to the chat history.
        """
        self.chat_history.configure(state="normal")
        
        # Format timestamp
        timestamp = time.strftime("%H:%M:%S")
        
        # Define tags for formatting
        tag_config = {
            "user": {"foreground": "#64B5F6"},
            "ai": {"foreground": "#A5D6A7"},
            "system": {"foreground": "#FFB74D"},
            "error": {"foreground": "#E57373"}
        }
        
        # Insert header
        header_text = f"[{timestamp}] "
        if message_type == "user":
            header_text += "👤 You: "
        elif message_type == "ai":
            header_text += "🤖 AI: "
        elif message_type == "system":
            header_text += "⚙️ System: "
        elif message_type == "error":
            header_text += "❌ Error: "

        self.chat_history.insert("end", header_text, message_type)
        
        # Insert message body
        self.chat_history.insert("end", f"{text}\n\n")
        
        # Apply tag color (CustomTkinter uses simple text insert without explicit tag application like Tkinter)
        # Using simple foreground coloring via multiple inserts for better contrast
        
        self.chat_history.configure(state="disabled")
        
        # Auto-scroll to bottom
        self.chat_history.see("end")
        
        # Store in conversation history
        self.conversation_history.append({
            "sender": sender,
            "text": text,
            "timestamp": timestamp,
            "type": message_type
        })
    
    def _on_send_clicked(self):
        """Handle send button click."""
        text = self.user_input.get().strip()
        if text:
            self.add_message("User", text, "user")
            self.process_user_input(text)
            self.user_input.delete(0, "end")
    
    def _on_mic_clicked(self):
        """Handle microphone button click."""
        if self.is_processing or self.voice_controller.is_listening:
            return
        
        # Start listening
        self._update_mic_button("🔴 Listening...", "#D32F2F", "#B71C1C", False)
        self.status_label.configure(text="Listening... Speak now!")
        
        def on_speech_result(text):
            """Handle speech recognition result, run in the main thread."""
            self.after(0, lambda: self._handle_speech_result_ui(text))

        self.voice_controller.listen_async(on_speech_result)
    
    def _handle_speech_result_ui(self, text: str):
        """Update UI and process input after listening is done."""
        self._update_mic_button("🎤 Speak", "#2E7D32", "#1B5E20", True) # Reset button state
        
        if text.strip():
            self.add_message("User", text, "user")
            self.process_user_input(text)
        else:
            self.add_message("System", "No speech detected. Please try again.", "system")
            self.status_label.configure(text="No speech detected")
    
    def _update_mic_button(self, text: str, fg_color: str, hover_color: str, enabled: bool):
        """
        Update microphone button appearance.
        """
        self.mic_button.configure(
            text=text,
            fg_color=fg_color,
            hover_color=hover_color,
            state="normal" if enabled else "disabled"
        )
    
    def process_user_input(self, text: str):
        """
        Process user input and generate AI response.
        """
        if self.is_processing:
            return
        
        self.is_processing = True
        self.send_button.configure(state="disabled")
        self._update_mic_button("🔄 Thinking...", "#FF8F00", "#E65100", False)
        self.status_label.configure(text="AI is thinking...")
        
        def process_in_thread():
            """Process input in separate thread."""
            try:
                # 1. Check for system commands first
                system_result = self._check_system_commands(text)
                if system_result:
                    self.after(0, lambda: self.add_message("System", system_result, "system"))
                    self.after(0, lambda: self._finish_processing(speak=False))
                    return
                
                # 2. Get AI response
                ai_response = self.ai_manager.get_response(text, self.persona_key)
                
                # 3. Update UI and speak in main thread
                self.after(0, lambda: self.add_message("AI", ai_response, "ai"))
                self.after(0, lambda: self._speak_response(ai_response))
                
            except Exception as e:
                error_msg = f"Error processing input: {str(e)}"
                logger.error(error_msg)
                self.after(0, lambda: self.add_message("System", error_msg, "error"))
                self.after(0, lambda: self._finish_processing(speak=False))
        
        # Run processing in thread
        threading.Thread(target=process_in_thread, daemon=True).start()
    
    def _check_system_commands(self, text: str) -> Optional[str]:
        """
        Check if user input contains system commands.
        """
        text_lower = text.lower()
        
        # Check for system commands (simplified pattern matching)
        
        # 1. Open Spotify/App
        match = re.search(r'(open|launch|start)\s+(spotify|chrome|firefox|code|terminal)\b', text_lower)
        if match:
            app_name = match.group(2)
            return self.system_integrator.execute_command("open_app", app_name)
        
        # 2. Web Search
        if any(phrase in text_lower for phrase in ['search for', 'google for', 'find out about']):
            query = re.sub(r'^(search for|google for|find out about)\s+', '', text_lower).strip()
            # If the command is followed by nothing, use the full text as query
            if not query:
                 query = text
            return self.system_integrator.execute_command("web_search", query)
        
        # 3. YouTube Search
        if any(phrase in text_lower for phrase in ['youtube', 'play video', 'watch video']):
            query = re.sub(r'^(youtube|play video|watch video)\s+', '', text_lower).strip()
            if not query:
                 query = text
            return self.system_integrator.execute_command("youtube_search", query)
        
        return None
    
    def _speak_response(self, text: str):
        """Speak the AI response."""
        def on_speech_finished():
            """Handle speech completion, runs in the main thread."""
            self.after(0, lambda: self._finish_processing(speak=True))
        
        self.voice_controller.speak_async(text, on_speech_finished)
    
    def _finish_processing(self, speak: bool):
        """Finish processing and reset UI state."""
        self.is_processing = False
        self.send_button.configure(state="normal")
        self._update_mic_button("🎤 Speak", "#2E7D32", "#1B5E20", True)
        self.status_label.configure(text="Ready - Type or speak your message")


class WelcomePage(ctk.CTkFrame):
    """
    Welcome page with app introduction and navigation.
    """
    
    def __init__(self, parent):
        """Initialize the welcome page."""
        super().__init__(parent)
        self._create_ui()
    
    def _create_ui(self):
        """Create the welcome page UI."""
        # Configure grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Main content frame
        content_frame = ctk.CTkFrame(self)
        content_frame.grid(row=0, column=0, sticky="nsew", padx=40, pady=40)
        content_frame.grid_rowconfigure(1, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(
            content_frame,
            text="🤖 AI Voice Assistant",
            font=ctk.CTkFont(size=40, weight="bold", family="Arial"),
            text_color="#4FC3F7"
        )
        title_label.grid(row=0, column=0, pady=(30, 20))
        
        # Description
        desc_text = """
Welcome to your AI Voice Assistant! This application features:

🎯 Specialized AI Personas:
• Finance Expert - Investment advice and market analysis
• Finance Expert - Investment advice and market analysis
• Science Tutor - Complex scientific explanations
• Legal Advisor - General legal information and guidance

🎤 Voice Integration:
• Speech-to-Text recognition (using speech_recognition)
• Text-to-Speech responses (using pyttsx3)
• Hands-free conversation capabilities

🔧 System Integration:
• Open applications (Spotify, browsers, etc.)
• Web searches and YouTube videos
• Smart command recognition

Choose a persona from the sidebar or use the buttons below to start chatting.
The AI can help with both specialized topics and general assistance.
        """
        
        desc_label = ctk.CTkLabel(
            content_frame,
            text=desc_text,
            font=ctk.CTkFont(size=14, family="Arial"),
            justify="left",
            text_color="#B0BEC5"
        )
        desc_label.grid(row=1, column=0, pady=(0, 30), padx=30, sticky="nsw")
        
        # Feature buttons frame (Completed the truncated part here)
        buttons_frame = ctk.CTkFrame(content_frame)
        buttons_frame.grid(row=2, column=0, pady=20, padx=30, sticky="ew")
        buttons_frame.grid_columnconfigure((0, 1), weight=1)
        
        features = [
            ("💬 General Chat", "general", "#26A69A"),
            ("💰 Finance Expert", "finance", "#4CAF50"),
            ("🔬 Science Tutor", "science", "#1E88E5"),
            ("⚖️ Legal Info Specialist", "legal", "#FF7043")
        ]
        
        # Place buttons in a 2x2 grid
        for i, (text, persona, color) in enumerate(features):
            btn = ctk.CTkButton(
                buttons_frame,
                text=text,
                command=lambda p=persona: self.master.show_frame(p), # Assumes master is ChatApp
                height=50,
                font=ctk.CTkFont(size=16, weight="bold"),
                fg_color=color,
                hover_color=color # Keep hover same for modern flat look
            )
            # Layout in a 2x2 grid
            row_idx = i // 2
            col_idx = i % 2
            btn.grid(row=row_idx, column=col_idx, padx=10, pady=10, sticky="ew")

class ChatApp(ctk.CTk):
    """
    The main application class, handling frame switching and state management.
    """
    
    def __init__(self):
        super().__init__()
        
        # Configure the main window
        self.title("AI Voice Chat Assistant (Cohere Direct API)")
        self.geometry("800x650")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        # Initialize core controllers
        self.ai_manager = AIModelManager()
        self.voice_controller = VoiceController()
        self.system_integrator = SystemIntegrator()
        
        # Container to hold all pages
        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)
        
        self.frames = {}
        
        self._create_sidebar(container)
        self._create_pages(container)
        
        self.show_frame("welcome")
    
    def _create_sidebar(self, parent):
        """Create the left navigation sidebar."""
        sidebar = ctk.CTkFrame(parent, width=180, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nswe")
        sidebar.grid_rowconfigure(5, weight=1)
        
        logo_label = ctk.CTkLabel(
            sidebar, 
            text="COHERE CHAT", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Navigation buttons
        nav_buttons = [
            ("🏠 Welcome", "welcome"),
            ("💬 General Chat", "general"),
            ("💰 Finance Expert", "finance"),
            ("🔬 Science Tutor", "science"),
            ("⚖️ Legal Info", "legal")
        ]
        
        for i, (text, name) in enumerate(nav_buttons):
            button = ctk.CTkButton(
                sidebar, 
                text=text, 
                command=lambda n=name: self.show_frame(n),
                height=40,
                font=ctk.CTkFont(size=14, weight="bold")
            )
            button.grid(row=i + 1, column=0, padx=20, pady=10, sticky="ew")

        # Exit button at the bottom
        exit_button = ctk.CTkButton(
            sidebar, 
            text="Exit App", 
            command=self.quit,
            fg_color="#D32F2F",
            hover_color="#B71C1C",
            height=40
        )
        exit_button.grid(row=9, column=0, padx=20, pady=(20, 20), sticky="s")


    def _create_pages(self, parent):
        """Create instances of all chat and welcome pages."""
        
        # Configuration for specialized chat pages
        chat_pages_config = {
            "general": {"persona_key": "general", "title": "General AI Assistant"},
            "finance": {"persona_key": "finance", "title": "Finance Expert Chat"},
            "science": {"persona_key": "science", "title": "Science Tutor Chat"},
            "legal": {"persona_key": "legal", "title": "Legal Information Chat"},
        }

        # Welcome Page
        frame = WelcomePage(parent)
        self.frames["welcome"] = frame
        frame.grid(row=0, column=1, sticky="nsew")

        # Chat Pages
        for name, config in chat_pages_config.items():
            frame = BaseChatFrame(
                parent, 
                self.ai_manager, 
                self.voice_controller, 
                self.system_integrator, 
                persona_key=config["persona_key"], 
                title=config["title"]
            )
            self.frames[name] = frame
            frame.grid(row=0, column=1, sticky="nsew")

    def show_frame(self, page_name):
        """Bring the specified page to the front."""
        frame = self.frames.get(page_name)
        if frame:
            frame.tkraise()
            self.title(f"AI Voice Chat Assistant - {frame.title}")

if __name__ == "__main__":
    try:
        # Check for necessary dependencies (pyttsx3 and speech_recognition are handled internally)
        if COHERE_API_KEY == "YOUR_COHERE_API_KEY_HERE" or not COHERE_API_KEY:
             print("ERROR: Please replace 'YOUR_COHERE_API_KEY_HERE' in the script with your actual Cohere API key.")
        
        app = ChatApp()
        app.mainloop()
    except Exception as e:
        logger.critical(f"Fatal application error: {e}")
        # Fallback for displaying error if mainloop hasn't started
        if 'app' in locals() and app.winfo_exists():
            messagebox.showerror("Fatal Error", f"The application encountered a critical error: {e}")
        else:
            print(f"FATAL ERROR: {e}")
