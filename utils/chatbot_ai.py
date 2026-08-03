"""
Chatbot implementation using Claude Sonnet 3.5

This module provides AI assistance through Anthropic's Claude Sonnet 3.5 model.
All clients have access to this feature by default.
"""

import os
import anthropic
from anthropic import Anthropic

def predecir_genero_por_nombre(nombre):
    """Returns non-specified since we want to be inclusive."""
    return 'No especificado'


class ClaudeChatbot:
    """Claude Sonnet 3.5 chatbot implementation.
    
    Provides intelligent responses using Anthropic's latest model.
    """
    def __init__(self, api_key=None):
        self.client = Anthropic(api_key=api_key or os.getenv('ANTHROPIC_API_KEY'))
        self.model = "claude-3-sonnet"
        self.context = []

    def get_response(self, user_input, **kwargs):
        """Get AI response from Claude Sonnet."""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.7,
                system="Eres un asistente experto en optometría y manejo de clínicas oftalmológicas. Responde de manera profesional y precisa.",
                messages=[
                    *[{"role": "user" if i%2==0 else "assistant", "content": msg} 
                      for i, msg in enumerate(self.context)],
                    {"role": "user", "content": user_input}
                ]
            )
            response = message.content[0].text
            self.context.extend([user_input, response])
            if len(self.context) > 10:  # Keep context window manageable
                self.context = self.context[-10:]
            return response
        except Exception as e:
            return f"Lo siento, hubo un error al procesar tu consulta: {str(e)}"

# Alias for compatibility
MistralChatbot = ClaudeChatbot