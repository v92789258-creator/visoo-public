"""
Sistema de recordatorios automáticos para citas en VISO.
Envía notificaciones por WhatsApp antes de las citas.
"""

import json
import datetime
import threading
import time
from typing import List, Dict, Optional, Callable
from pathlib import Path
from utils.appointments_model import Appointment, AppointmentStatus, ReminderType
from utils.whatsapp_handler import send_whatsapp_message
from utils.data_cache_manager import get_global_cache


class ReminderLog:
    """Registro de recordatorios enviados"""
    
    def __init__(self, username: str, base_path: str = "VISO"):
        self.username = username
        self.log_path = Path(base_path) / username / "data" / "reminder_log.json"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.logs: List[Dict] = []
        self.load()
    
    def load(self):
        """Carga el registro de recordatorios"""
        try:
            if self.log_path.exists():
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    self.logs = json.load(f)
            else:
                self.logs = []
        except Exception as e:
            print(f"Error cargando log de recordatorios: {e}")
            self.logs = []
    
    def save(self):
        """Guarda el registro"""
        try:
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump(self.logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error guardando log: {e}")
    
    def agregar(self, cita_id: str, tipo_recordatorio: str, exito: bool, mensaje: str = ""):
        """Registra un recordatorio enviado"""
        self.logs.append({
            "cita_id": cita_id,
            "tipo_recordatorio": tipo_recordatorio,
            "fecha_envio": datetime.datetime.now().isoformat(),
            "exito": exito,
            "mensaje": mensaje
        })
        self.save()
    
    def ya_enviado(self, cita_id: str, tipo_recordatorio: str) -> bool:
        """Verifica si ya se envió un recordatorio"""
        return any(
            log["cita_id"] == cita_id and 
            log["tipo_recordatorio"] == tipo_recordatorio and
            log["exito"]
            for log in self.logs
        )


class ReminderManager:
    """Gestor de recordatorios"""
    
    def __init__(self, username: str, base_path: str = "VISO"):
        """
        Inicializa el gestor de recordatorios.
        
        Args:
            username: Nombre de usuario
            base_path: Ruta base
        """
        self.username = username
        self.base_path = base_path
        self.log = ReminderLog(username, base_path)
        self.citas_procesadas = set()
        self.is_running = False
        self.reminder_thread: Optional[threading.Thread] = None
    
    def puede_enviar_recordatorio_24h(self, cita: Appointment) -> bool:
        """Verifica si se puede enviar recordatorio 24h antes"""
        try:
            fecha_hora = datetime.datetime.strptime(
                f"{cita.fecha} {cita.hora}",
                "%Y-%m-%d %H:%M"
            )
            ahora = datetime.datetime.now()
            horas_hasta = (fecha_hora - ahora).total_seconds() / 3600
            
            # Enviar entre 24 y 23.5 horas antes (para evitar duplicados)
            return 23.5 <= horas_hasta <= 24.5
        except ValueError:
            return False
    
    def puede_enviar_recordatorio_1h(self, cita: Appointment) -> bool:
        """Verifica si se puede enviar recordatorio 1h antes"""
        try:
            fecha_hora = datetime.datetime.strptime(
                f"{cita.fecha} {cita.hora}",
                "%Y-%m-%d %H:%M"
            )
            ahora = datetime.datetime.now()
            horas_hasta = (fecha_hora - ahora).total_seconds() / 3600
            
            # Enviar entre 1 y 0.9 horas antes
            return 0.9 <= horas_hasta <= 1.1
        except ValueError:
            return False
    
    def obtener_numero_paciente(self, dni: str) -> Optional[str]:
        """Obtiene el número de teléfono del paciente"""
        try:
            cache = get_global_cache()
            pacientes = cache.get_pacientes(self.username)
            paciente = next((p for p in pacientes if p.get('dni') == dni), None)
            return paciente.get('telefono') if paciente else None
        except Exception as e:
            print(f"Error obteniendo teléfono: {e}")
            return None
    
    def construir_mensaje_recordatorio(self, cita: Appointment, tipo: ReminderType) -> str:
        """Construye el mensaje de recordatorio"""
        try:
            cache = get_global_cache()
            pacientes = cache.get_pacientes(self.username)
            paciente = next((p for p in pacientes if p.get('dni') == cita.dni), None)
            nombre_paciente = paciente.get('nombre', 'cliente') if paciente else 'cliente'
            
            if tipo == ReminderType.WHATSAPP_24H:
                return f"Hola {nombre_paciente},\n\nTe recordamos que tienes una cita de {cita.tipo.value} mañana a las {cita.hora}. ¡No olvides venir!"
            
            elif tipo == ReminderType.WHATSAPP_1H:
                return f"Hola {nombre_paciente},\n\n¡Te recordamos que tu cita es en 1 hora! A las {cita.hora} te esperamos."
            
            else:
                return f"Recordatorio de cita para {nombre_paciente} a las {cita.hora}"
        
        except Exception as e:
            print(f"Error construyendo mensaje: {e}")
            return "Recordatorio de cita"
    
    def enviar_recordatorio(self, cita: Appointment, tipo: ReminderType) -> bool:
        """Envía un recordatorio para una cita"""
        
        # Verificar si ya se envió
        if self.log.ya_enviado(cita.cita_id, tipo.value):
            return True
        
        # Obtener teléfono del paciente
        telefono = self.obtener_numero_paciente(cita.dni)
        if not telefono:
            self.log.agregar(cita.cita_id, tipo.value, False, "Sin número de teléfono")
            return False
        
        # Construir mensaje
        mensaje = self.construir_mensaje_recordatorio(cita, tipo)
        
        # Enviar por WhatsApp
        try:
            exito = send_whatsapp_message(telefono, mensaje)
            self.log.agregar(cita.cita_id, tipo.value, exito, "Enviado" if exito else "Falló")
            return exito
        except Exception as e:
            self.log.agregar(cita.cita_id, tipo.value, False, f"Error: {str(e)}")
            return False
    
    def procesar_citas_pendientes(self, citas: List[Appointment]) -> Dict[str, int]:
        """
        Procesa citas pendientes y envía recordatorios necesarios.
        
        Args:
            citas: Lista de citas a procesar
        
        Returns:
            Diccionario con estadísticas de recordatorios enviados
        """
        estadisticas = {
            "recordatorios_24h_enviados": 0,
            "recordatorios_1h_enviados": 0,
            "errores": 0
        }
        
        for cita in citas:
            if cita.estado != AppointmentStatus.PENDING or cita.is_overdue():
                continue
            
            # Recordatorio 24 horas
            if ReminderType.WHATSAPP_24H in cita.recordatorios and self.puede_enviar_recordatorio_24h(cita):
                if self.enviar_recordatorio(cita, ReminderType.WHATSAPP_24H):
                    estadisticas["recordatorios_24h_enviados"] += 1
                else:
                    estadisticas["errores"] += 1
            
            # Recordatorio 1 hora
            if ReminderType.WHATSAPP_1H in cita.recordatorios and self.puede_enviar_recordatorio_1h(cita):
                if self.enviar_recordatorio(cita, ReminderType.WHATSAPP_1H):
                    estadisticas["recordatorios_1h_enviados"] += 1
                else:
                    estadisticas["errores"] += 1
        
        return estadisticas
    
    def iniciar_verificacion_automatica(self, citas_callback: Callable[[], List[Appointment]], intervalo_segundos: int = 300):
        """
        Inicia la verificación automática de recordatorios en un hilo.
        
        Args:
            citas_callback: Función que retorna lista de citas
            intervalo_segundos: Intervalo de verificación (por defecto 5 min)
        """
        if self.is_running:
            return
        
        self.is_running = True
        
        def worker():
            while self.is_running:
                try:
                    citas = citas_callback()
                    self.procesar_citas_pendientes(citas)
                except Exception as e:
                    print(f"Error en verificación automática: {e}")
                
                time.sleep(intervalo_segundos)
        
        self.reminder_thread = threading.Thread(target=worker, daemon=True)
        self.reminder_thread.start()
    
    def detener_verificacion(self):
        """Detiene la verificación automática"""
        self.is_running = False
        if self.reminder_thread:
            self.reminder_thread.join(timeout=5)
