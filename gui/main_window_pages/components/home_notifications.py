"""
HomeNotifications - Especializado en sistema de notificaciones

Responsabilidades:
- Polling de notificaciones en background thread
- Emisión de señales cuando hay nuevas notificaciones
- Gestión de ciclo de vida del worker
"""

import time
import requests
from PyQt5.QtCore import QThread, pyqtSignal

NOTIFICATION_POLL_INTERVAL_SECONDS = 45 * 60


class NotificationWorker(QThread):
    """Worker thread que hace polling de notificaciones sin bloquear UI.
    
    Características:
    - Corre en thread separado
    - Timeout corto para no "congelar"
    - Emisión de señales por nueva notificación
    - Parada limpia y elegante
    """
    
    # Señal emitida cuando llega notificación nueva
    notification_received = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.last_notification_id = 0
    
    def run(self):
        """Loop principal de polling (corre en thread separado)."""
        while self.running:
            try:
                # Timeout corto para que se pueda detener rápido
                response = requests.get(
                    "https://api.yhana.cloud/api/win/notis.php",
                    timeout=3
                )
                
                if response.status_code == 200:
                    data = response.json()
                    notif_list = (
                        data if isinstance(data, list)
                        else data.get("notificaciones", [])
                    )
                    
                    # Procesar cada notificación nueva
                    for notif in notif_list:
                        notif_id = notif.get('id', 0)
                        
                        # Si es nueva (mayor ID), emitir
                        if notif_id > self.last_notification_id and self.running:
                            self.last_notification_id = notif_id
                            self.notification_received.emit(notif)
            
            except (requests.RequestException, ValueError, KeyError):
                # Falló fetch o parsing - ignorar y reintentar
                pass
            
            # Espera fraccionada larga para no saturar el servidor y permitir cancelación rápida.
            for _ in range(int(NOTIFICATION_POLL_INTERVAL_SECONDS * 10)):
                if not self.running:
                    return
                time.sleep(0.1)
    
    def stop(self):
        """Detiene el worker de forma limpia.
        
        No bloquea - solo señala que debe parar y espera un poco.
        """
        self.running = False
        self.quit()
        self.wait(1000)  # Máximo 1 segundo esperando
