"""Chatbot dialog implementation

Interactive dialog for Claude Sonnet 3.5 AI assistant.
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QTextEdit, QScrollArea, QWidget)
from PyQt5.QtCore import Qt
from utils.chatbot_ai import ClaudeChatbot
import os

class ChatMessage(QWidget):
    def __init__(self, text, is_user=True, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        msg = QLabel(text)
        msg.setWordWrap(True)
        msg.setStyleSheet(
            "background: #e3f2fd;" if is_user else "background: #f5f5f5;"
            "padding: 10px; border-radius: 5px;"
        )
        if is_user:
            layout.addStretch()
        layout.addWidget(msg)
        if not is_user:
            layout.addStretch()


class ChatbotDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Asistente IA - Claude Sonnet 3.5')
        self.resize(600, 800)
        self.setup_ui()
        self.chatbot = ClaudeChatbot()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Chat history area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.addStretch()
        
        self.scroll.setWidget(self.chat_container)
        layout.addWidget(self.scroll)
        
        # Input area
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        
        self.input_field = QTextEdit()
        self.input_field.setMaximumHeight(100)
        self.input_field.setPlaceholderText("Escribe tu mensaje aquí...")
        input_layout.addWidget(self.input_field)
        
        send_btn = QPushButton("Enviar")
        send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(send_btn)
        
        layout.addWidget(input_container)
        
    def send_message(self):
        user_text = self.input_field.toPlainText().strip()
        if not user_text:
            return
            
        # Add user message
        self.add_message(user_text, True)
        self.input_field.clear()
        
        # Get and display AI response
        response = self.chatbot.get_response(user_text)
        self.add_message(response, False)
        
    def add_message(self, text, is_user):
        msg = ChatMessage(text, is_user)
        self.chat_layout.insertWidget(self.chat_layout.count()-1, msg)
        self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        )