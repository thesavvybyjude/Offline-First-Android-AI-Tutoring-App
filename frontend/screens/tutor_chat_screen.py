"""
Tutor Chat Screen
AI tutoring interface with streaming responses
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.properties import ObjectProperty
from kivy.clock import Clock
from backend.rag_pipeline import RAGPipeline
from backend.inference_engine import InferenceEngine


class TutorChatScreen(Screen):
    """Tutor chat screen with AI responses"""
    
    chat_layout = ObjectProperty(None)
    message_input = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'tutor_chat'
        self.rag = None
        self.inference = None
        self.messages = []
        self._build_ui()
    
    def on_enter(self):
        """Called when screen is entered"""
        # Initialize RAG and inference (lazy loading)
        try:
            self.rag = RAGPipeline()
            self.inference = InferenceEngine()
        except Exception as e:
            print(f"Error initializing AI: {e}")
    
    def _build_ui(self):
        """Build the chat UI"""
        # Main layout
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Header
        header = BoxLayout(orientation='horizontal', size_hint_y=0.08)
        header_label = Label(text='AI Tutor', font_size=24, bold=True)
        back_btn = Button(text='←', size_hint_x=0.1, font_size=24)
        back_btn.bind(on_press=self.go_back)
        header.add_widget(back_btn)
        header.add_widget(header_label)
        layout.add_widget(header)
        
        # Chat messages area
        scroll = ScrollView(size_hint_y=0.75)
        self.chat_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.chat_layout.bind(minimum_height=self.chat_layout.setter('height'))
        scroll.add_widget(self.chat_layout)
        layout.add_widget(scroll)
        
        # Input area
        input_layout = BoxLayout(orientation='horizontal', size_hint_y=0.12, spacing=10)
        
        self.message_input = TextInput(
            hint_text='Ask a question...',
            multiline=False,
            font_size=16
        )
        input_layout.add_widget(self.message_input)
        
        send_btn = Button(
            text='Send',
            size_hint_x=0.25,
            font_size=16,
            background_color=(0.2, 0.6, 0.8, 1)
        )
        send_btn.bind(on_press=self.send_message)
        input_layout.add_widget(send_btn)
        
        layout.add_widget(input_layout)
        
        self.add_widget(layout)
    
    def send_message(self, instance):
        """Send message and get AI response"""
        query = self.message_input.text.strip()
        if not query:
            return
        
        # Clear input
        self.message_input.text = ''
        
        # Add user message
        self._add_message(query, is_user=True)
        
        # Get AI response
        self._get_ai_response(query)
    
    def _add_message(self, text: str, is_user: bool = False):
        """Add a message to the chat"""
        msg_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            padding=10
        )
        
        # Message bubble
        bubble = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            padding=10
        )
        
        with bubble.canvas.before:
            if is_user:
                Color(0.2, 0.6, 0.8, 1)  # Blue for user
            else:
                Color(0.8, 0.8, 0.8, 1)  # Gray for AI
            bubble.rect = Rectangle(pos=bubble.pos, size=bubble.size)
        
        bubble.bind(pos=self._update_rect, size=self._update_rect)
        
        msg_label = Label(
            text=text,
            font_size=14,
            text_size=(340, None),
            halign='left',
            valign='top'
        )
        msg_label.bind(texture_size=msg_label.setter('size'))
        msg_label.height = msg_label.texture_size[1] + 20
        
        bubble.add_widget(msg_label)
        bubble.height = msg_label.height + 20
        
        msg_layout.add_widget(bubble)
        msg_layout.height = bubble.height
        
        self.chat_layout.add_widget(msg_layout)
    
    def _update_rect(self, instance, value):
        """Update rectangle position and size"""
        instance.rect.pos = instance.pos
        instance.rect.size = instance.size
    
    def _get_ai_response(self, query: str):
        """Get AI response using RAG + LLM"""
        try:
            # Retrieve context
            if self.rag:
                context = self.rag.retrieve_context(query, max_tokens=512)
            else:
                context = ""
            
            # Generate response
            if self.inference:
                response = self.inference.generate(
                    query=query,
                    context=context,
                    grade_level="SS1",
                    max_tokens=256
                )
            else:
                response = "AI not available. Please check model setup."
            
            # Add AI message
            self._add_message(response, is_user=False)
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self._add_message(error_msg, is_user=False)
    
    def go_back(self, instance):
        """Return to dashboard"""
        self.manager.current = 'dashboard'
