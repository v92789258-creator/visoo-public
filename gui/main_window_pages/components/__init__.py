"""
Components - Submódulos especializados de HomePage.

Se evita importar submódulos pesados aquí para no penalizar el arranque.
Cada consumidor debe importar el componente que necesite directamente.
"""

__all__ = [
    "HomeDataLoader",
    "HomeUIBuilder",
    "NotificationWorker",
]
