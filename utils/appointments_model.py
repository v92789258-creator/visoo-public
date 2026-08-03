"""
Modelo mejorado para gestión de citas en VISO.
Incluye estados, duraciones, tipos configurables y recordatorios.
"""

import json
import datetime
from enum import Enum
from typing import List, Dict, Optional
from pathlib import Path

# ============= ENUMS =============

class AppointmentStatus(Enum):
    """Estados posibles de una cita"""
    PENDING = "Pendiente"           # Cita programada
    COMPLETED = "Completada"       # Cita realizada
    CANCELLED = "Cancelada"        # Cita cancelada por usuario/optómetra
    NO_SHOW = "No presentado"      # Paciente no se presentó
    RESCHEDULED = "Reprogramada"   # Cita reprogramada


class AppointmentType(Enum):
    """Tipos de cita disponibles"""
    GRADUATION = "Graduación"      # Examen de vista completo
    REVIEW = "Revisión"            # Revisión de lentes
    CONSULTATION = "Consulta"      # Consulta general
    MAINTENANCE = "Mantenimiento"  # Ajuste/limpieza de lentes
    FOLLOW_UP = "Seguimiento"      # Seguimiento post-compra


class ReminderType(Enum):
    """Tipos de recordatorio"""
    WHATSAPP_24H = "whatsapp_24h"   # WhatsApp 24 horas antes
    WHATSAPP_1H = "whatsapp_1h"     # WhatsApp 1 hora antes
    SMS_24H = "sms_24h"             # SMS 24 horas antes
    CALL_REMINDER = "call_reminder" # Llamada recordatoria


# ============= CLASES =============

class Appointment:
    """Representa una cita mejorada"""
    
    def __init__(
        self,
        dni: str,
        fecha: str,  # Formato: YYYY-MM-DD
        hora: str,   # Formato: HH:MM
        duracion_minutos: int = 30,
        tipo: AppointmentType = AppointmentType.GRADUATION,
        estado: AppointmentStatus = AppointmentStatus.PENDING,
        notas: str = "",
        doctor: str = "",
        optometra: str = "",
        recordatorios: Optional[List[ReminderType]] = None,
        cita_id: Optional[str] = None,
        nombre_paciente: str = ""
    ):
        """
        Crea una nueva cita.
        """
        self.cita_id = cita_id or self._generate_id()
        self.dni = dni
        self.nombre_paciente = nombre_paciente
        self.fecha = fecha
        self.hora = hora
        self.duracion_minutos = duracion_minutos
        self.tipo = tipo
        self.estado = estado
        self.notas = notas
        self.doctor = doctor
        self.optometra = optometra
        self.recordatorios = recordatorios or [ReminderType.WHATSAPP_24H]
        self.created_at = datetime.datetime.now().isoformat()
        self.updated_at = datetime.datetime.now().isoformat()
        self.historial_cambios = []
    
    @staticmethod
    def _generate_id() -> str:
        """Genera ID único para la cita"""
        return f"CITA_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def get_end_time(self) -> str:
        """Calcula la hora de fin basada en duración"""
        try:
            inicio = datetime.datetime.strptime(self.hora, "%H:%M")
            fin = inicio + datetime.timedelta(minutes=self.duracion_minutos)
            return fin.strftime("%H:%M")
        except ValueError:
            return "N/A"
    
    def is_overdue(self) -> bool:
        """Comprueba si la cita ya pasó"""
        try:
            fecha_hora = datetime.datetime.strptime(
                f"{self.fecha} {self.hora}",
                "%Y-%m-%d %H:%M"
            )
            return fecha_hora < datetime.datetime.now()
        except ValueError:
            return False
    
    def get_time_until_appointment(self) -> Optional[float]:
        """Retorna horas hasta la cita (negativo si pasó)"""
        try:
            fecha_hora = datetime.datetime.strptime(
                f"{self.fecha} {self.hora}",
                "%Y-%m-%d %H:%M"
            )
            delta = (fecha_hora - datetime.datetime.now()).total_seconds() / 3600
            return delta
        except ValueError:
            return None
    
    def cambiar_estado(self, nuevo_estado: AppointmentStatus, razon: str = ""):
        """Cambia el estado y registra el cambio"""
        if self.estado != nuevo_estado:
            self.historial_cambios.append({
                "fecha": datetime.datetime.now().isoformat(),
                "estado_anterior": self.estado.value,
                "estado_nuevo": nuevo_estado.value,
                "razon": razon
            })
            self.estado = nuevo_estado
            self.updated_at = datetime.datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Convierte la cita a diccionario"""
        return {
            "cita_id": self.cita_id,
            "dni": self.dni,
            "nombre_paciente": self.nombre_paciente,
            "fecha": self.fecha,
            "hora": self.hora,
            "duracion_minutos": self.duracion_minutos,
            "tipo": self.tipo.value,
            "estado": self.estado.value,
            "notas": self.notas,
            "doctor": self.doctor,
            "optometra": self.optometra,
            "recordatorios": [r.value for r in self.recordatorios],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "historial_cambios": self.historial_cambios
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Appointment":
        """Crea una cita desde diccionario"""
        # Safe status conversion
        status_val = data.get("estado", "Pendiente")
        try:
            status = AppointmentStatus(status_val)
        except ValueError:
            # Try flexible matching
            try:
                status = next(s for s in AppointmentStatus if s.value.lower() == str(status_val).lower())
            except StopIteration:
                status = AppointmentStatus.PENDING

        # Safe type conversion
        type_val = data.get("tipo", "Graduación")
        try:
            appt_type = AppointmentType(type_val)
        except ValueError:
            try:
                appt_type = next(t for t in AppointmentType if t.value.lower() == str(type_val).lower())
            except StopIteration:
                appt_type = AppointmentType.GRADUATION

        cita = cls(
            dni=data.get("dni"),
            nombre_paciente=data.get("nombre_paciente", ""),
            fecha=data.get("fecha"),
            hora=data.get("hora"),
            duracion_minutos=data.get("duracion_minutos", 30),
            tipo=appt_type,
            estado=status,
            notas=data.get("notas", ""),
            doctor=data.get("doctor", ""),
            optometra=data.get("optometra", ""),
            recordatorios=[ReminderType(r) for r in data.get("recordatorios", ["whatsapp_24h"])],
            cita_id=data.get("cita_id")
        )
        cita.created_at = data.get("created_at", cita.created_at)
        cita.updated_at = data.get("updated_at", cita.updated_at)
        cita.historial_cambios = data.get("historial_cambios", [])
        return cita


class AppointmentsManager:
    """Gestor centralizado de citas"""
    
    def __init__(self, username: str, base_path: str = "VISO"):
        """
        Inicializa el gestor de citas.
        
        Args:
            username: Nombre de usuario/optómetra
            base_path: Ruta base para almacenar citas
        """
        self.username = username
        self.citas_path = Path(base_path) / username / "data" / "citas.json"
        self.citas_path.parent.mkdir(parents=True, exist_ok=True)
        self.citas: List[Appointment] = []
        self.load_citas()
    
    def load_citas(self):
        """Carga citas del archivo JSON"""
        try:
            if self.citas_path.exists():
                with open(self.citas_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.citas = [Appointment.from_dict(c) for c in data]
            else:
                self.citas = []
        except Exception as e:
            print(f"Error cargando citas: {e}")
            self.citas = []
    
    def save_citas(self):
        """Guarda citas en archivo JSON"""
        try:
            with open(self.citas_path, 'w', encoding='utf-8') as f:
                json.dump([c.to_dict() for c in self.citas], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error guardando citas: {e}")
    
    def agregar_cita(self, cita: Appointment) -> bool:
        """Agrega una nueva cita"""
        self.citas.append(cita)
        self.save_citas()
        return True
    
    def eliminar_cita(self, cita_id: str) -> bool:
        """Elimina una cita por ID"""
        self.citas = [c for c in self.citas if c.cita_id != cita_id]
        self.save_citas()
        return True
    
    def actualizar_cita(self, cita_id: str, **kwargs) -> Optional[Appointment]:
        """Actualiza una cita existente"""
        for cita in self.citas:
            if cita.cita_id == cita_id:
                for key, value in kwargs.items():
                    if hasattr(cita, key):
                        setattr(cita, key, value)
                cita.updated_at = datetime.datetime.now().isoformat()
                self.save_citas()
                return cita
        return None
    
    def obtener_cita(self, cita_id: str) -> Optional[Appointment]:
        """Obtiene una cita por ID"""
        return next((c for c in self.citas if c.cita_id == cita_id), None)
    
    def obtener_citas_paciente(self, dni: str) -> List[Appointment]:
        """Obtiene todas las citas de un paciente"""
        return [c for c in self.citas if c.dni == dni]
    
    def obtener_citas_fecha(self, fecha: str) -> List[Appointment]:
        """Obtiene citas de una fecha específica"""
        return sorted([c for c in self.citas if c.fecha == fecha], key=lambda x: x.hora)
    
    def obtener_citas_pendientes(self) -> List[Appointment]:
        """Obtiene todas las citas pendientes"""
        return [c for c in self.citas if c.estado == AppointmentStatus.PENDING and not c.is_overdue()]
    
    def obtener_citas_rango(self, fecha_inicio: str, fecha_fin: str) -> List[Appointment]:
        """Obtiene citas en un rango de fechas"""
        return [
            c for c in self.citas
            if fecha_inicio <= c.fecha <= fecha_fin
        ]
    
    def hay_conflicto(self, fecha: str, hora: str, duracion: int, excluir_cita_id: Optional[str] = None) -> bool:
        """
        Verifica si hay conflicto de horario.
        
        Args:
            fecha: Fecha de la cita
            hora: Hora de inicio (HH:MM)
            duracion: Duración en minutos
            excluir_cita_id: ID de cita a excluir (útil para ediciones)
        
        Returns:
            True si hay conflicto, False si está disponible
        """
        try:
            cita_inicio = datetime.datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
            cita_fin = cita_inicio + datetime.timedelta(minutes=duracion)
            
            for cita in self.citas:
                # Excluir la cita que se está editando
                if excluir_cita_id and cita.cita_id == excluir_cita_id:
                    continue
                
                # Solo considerar conflicto con citas PENDIENTE o COMPLETADA
                # No hay conflicto con CANCELADAS o NO_SHOW
                if cita.fecha == fecha and cita.estado in (AppointmentStatus.PENDING, AppointmentStatus.COMPLETED):
                    existente_inicio = datetime.datetime.strptime(f"{cita.fecha} {cita.hora}", "%Y-%m-%d %H:%M")
                    existente_fin = existente_inicio + datetime.timedelta(minutes=cita.duracion_minutos)
                    
                    # Verificar superposición
                    if cita_inicio < existente_fin and cita_fin > existente_inicio:
                        return True
            
            return False
        except ValueError:
            return False
    
    def obtener_estadisticas(self) -> Dict:
        """Retorna estadísticas de citas"""
        total = len(self.citas)
        completadas = len([c for c in self.citas if c.estado == AppointmentStatus.COMPLETED])
        canceladas = len([c for c in self.citas if c.estado == AppointmentStatus.CANCELLED])
        no_presentados = len([c for c in self.citas if c.estado == AppointmentStatus.NO_SHOW])
        pendientes = len([c for c in self.citas if c.estado == AppointmentStatus.PENDING])
        
        return {
            "total": total,
            "completadas": completadas,
            "canceladas": canceladas,
            "no_presentados": no_presentados,
            "pendientes": pendientes,
            "tasa_inasistencia": (no_presentados / completadas * 100) if completadas > 0 else 0,
            "tasa_cancelacion": (canceladas / total * 100) if total > 0 else 0
        }