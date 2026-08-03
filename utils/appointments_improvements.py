"""
MEJORAS PARA EL SISTEMA DE CITAS - VISO
========================================

Modulo con utilidades mejoradas para gestión de citas:
1. Detección de conflictos de horario
2. Sugerencias automáticas de horarios disponibles
3. Estadísticas y reportes
4. Validaciones mejoradas
5. Notificaciones inteligentes
"""

import datetime
from typing import List, Dict, Tuple, Optional
from utils.appointments_model import Appointment, AppointmentStatus, AppointmentType
from utils.file_handler import cargar_pacientes


class ConflictDetector:
    """Detecta conflictos de horario en citas"""
    
    def __init__(self, appointments: List[Appointment], username: str = ""):
        self.appointments = appointments
        self.username = username
        self.conflict_window_minutes = 30  # Ventana de conflicto (no se pueden superponer)
    
    def has_conflict(self, nueva_cita: Appointment) -> Tuple[bool, List[Appointment]]:
        """
        Verifica si hay conflictos con la nueva cita.
        Retorna: (hay_conflicto, lista_de_citas_en_conflicto)
        """
        try:
            fecha_hora_nueva = datetime.datetime.strptime(
                f"{nueva_cita.fecha} {nueva_cita.hora}",
                "%Y-%m-%d %H:%M"
            )
            fecha_hora_fin_nueva = fecha_hora_nueva + datetime.timedelta(
                minutes=nueva_cita.duracion_minutos
            )
        except ValueError:
            return False, []
        
        conflictos = []
        
        for cita in self.appointments:
            # Ignorar citas canceladas o no presentadas
            if cita.estado in [AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]:
                continue
            
            # Ignorar si es la misma cita
            if cita.cita_id == nueva_cita.cita_id:
                continue
            
            try:
                fecha_hora_cita = datetime.datetime.strptime(
                    f"{cita.fecha} {cita.hora}",
                    "%Y-%m-%d %H:%M"
                )
                fecha_hora_fin_cita = fecha_hora_cita + datetime.timedelta(
                    minutes=cita.duracion_minutos
                )
                
                # Verificar solapamiento
                inicio = max(fecha_hora_nueva, fecha_hora_cita)
                fin = min(fecha_hora_fin_nueva, fecha_hora_fin_cita)
                
                if inicio < fin:
                    conflictos.append(cita)
            
            except ValueError:
                continue
        
        return len(conflictos) > 0, conflictos
    
    def get_available_slots(
        self, 
        fecha: str,  # YYYY-MM-DD
        duracion_minutos: int = 30,
        hora_inicio: str = "08:00",
        hora_fin: str = "18:00"
    ) -> List[str]:
        """
        Retorna slots de tiempo disponibles para una fecha.
        Formato: ["08:00", "08:30", "09:00", ...]
        """
        disponibles = []
        
        try:
            hora_actual = datetime.datetime.strptime(hora_inicio, "%H:%M")
            hora_limite = datetime.datetime.strptime(hora_fin, "%H:%M")
        except ValueError:
            return []
        
        # Obtener todas las citas del día
        citas_del_dia = [
            c for c in self.appointments 
            if c.fecha == fecha and c.estado not in [
                AppointmentStatus.CANCELLED, 
                AppointmentStatus.NO_SHOW
            ]
        ]
        
        intervalo_minutos = 30  # Intervalos de 30 minutos
        
        while hora_actual + datetime.timedelta(minutes=duracion_minutos) <= hora_limite:
            slot_str = hora_actual.strftime("%H:%M")
            slot_fin = hora_actual + datetime.timedelta(minutes=duracion_minutos)
            
            # Verificar si hay conflicto
            hay_conflicto = False
            for cita in citas_del_dia:
                try:
                    cita_inicio = datetime.datetime.strptime(cita.hora, "%H:%M")
                    cita_fin = cita_inicio + datetime.timedelta(minutes=cita.duracion_minutos)
                    
                    # Verificar solapamiento
                    if not (slot_fin <= cita_inicio or hora_actual >= cita_fin):
                        hay_conflicto = True
                        break
                except ValueError:
                    continue
            
            if not hay_conflicto:
                disponibles.append(slot_str)
            
            hora_actual += datetime.timedelta(minutes=intervalo_minutos)
        
        return disponibles
    
    def get_next_available_slot(
        self, 
        fecha_minima: str = None,  # YYYY-MM-DD
        duracion_minutos: int = 30
    ) -> Optional[Tuple[str, str]]:  # (fecha, hora)
        """Retorna el próximo slot disponible a partir de hoy"""
        if fecha_minima is None:
            fecha_minima = datetime.date.today()
        else:
            try:
                fecha_minima = datetime.datetime.strptime(fecha_minima, "%Y-%m-%d").date()
            except ValueError:
                fecha_minima = datetime.date.today()
        
        # Buscar en los próximos 30 días
        for i in range(30):
            fecha = (fecha_minima + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            slots = self.get_available_slots(fecha, duracion_minutos)
            
            if slots:
                return fecha, slots[0]
        
        return None


class AppointmentValidator:
    """Validador mejorado para citas"""
    
    @staticmethod
    def validar_datos_cita(
        dni: str,
        fecha: str,  # YYYY-MM-DD
        hora: str,   # HH:MM
        duracion_minutos: int = 30,
        username: str = ""
    ) -> Tuple[bool, str]:
        """
        Valida los datos de una cita.
        Retorna: (es_valido, mensaje_error)
        """
        
        # Validar DNI
        if not dni or not dni.strip():
            return False, "DNI del paciente es requerido"
        
        # Validar que el paciente existe
        try:
            pacientes = cargar_pacientes(username)
            paciente_existe = any(p.get('dni') == dni for p in pacientes)
            if not paciente_existe and dni != "00000000":
                return False, f"Paciente con DNI {dni} no encontrado"
        except:
            pass
        
        # Validar fecha
        try:
            fecha_obj = datetime.datetime.strptime(fecha, "%Y-%m-%d").date()
            if fecha_obj < datetime.date.today():
                return False, "La fecha no puede ser en el pasado"
        except ValueError:
            return False, "Formato de fecha inválido (use YYYY-MM-DD)"
        
        # Validar hora
        try:
            datetime.datetime.strptime(hora, "%H:%M")
        except ValueError:
            return False, "Formato de hora inválido (use HH:MM)"
        
        # Validar duración
        if duracion_minutos not in [30, 60, 90, 120]:
            return False, "Duración debe ser 30, 60, 90 o 120 minutos"
        
        # Validar horario de negocio (8 AM - 6 PM)
        try:
            hora_obj = datetime.datetime.strptime(hora, "%H:%M").time()
            if hora_obj < datetime.time(8, 0) or hora_obj > datetime.time(18, 0):
                return False, "La hora debe estar entre 08:00 y 18:00"
        except ValueError:
            pass
        
        return True, "Válido"
    
    @staticmethod
    def validar_reprogramacion(
        cita: Appointment,
        nueva_fecha: str,
        nueva_hora: str
    ) -> Tuple[bool, str]:
        """Valida si una cita puede ser reprogramada"""
        
        if cita.estado == AppointmentStatus.COMPLETED:
            return False, "No se puede reprogramar una cita completada"
        
        if cita.estado == AppointmentStatus.CANCELLED:
            return False, "No se puede reprogramar una cita cancelada"
        
        # Validar que no sea en el pasado
        try:
            fecha_obj = datetime.datetime.strptime(nueva_fecha, "%Y-%m-%d").date()
            if fecha_obj < datetime.date.today():
                return False, "No se puede reprogramar a una fecha pasada"
        except ValueError:
            return False, "Formato de fecha inválido"
        
        return True, "Válido"


class AppointmentStatistics:
    """Genera estadísticas de citas"""
    
    def __init__(self, appointments: List[Appointment]):
        self.appointments = appointments
    
    def get_resumen_diario(self, fecha: str = None) -> Dict:
        """Resumen de citas del día"""
        if fecha is None:
            fecha = datetime.date.today().strftime("%Y-%m-%d")
        
        citas_dia = [c for c in self.appointments if c.fecha == fecha]
        
        return {
            "total_citas": len(citas_dia),
            "pendientes": len([c for c in citas_dia if c.estado == AppointmentStatus.PENDING]),
            "completadas": len([c for c in citas_dia if c.estado == AppointmentStatus.COMPLETED]),
            "canceladas": len([c for c in citas_dia if c.estado == AppointmentStatus.CANCELLED]),
            "no_presentados": len([c for c in citas_dia if c.estado == AppointmentStatus.NO_SHOW]),
        }
    
    def get_resumen_semanal(self, fecha_inicio: str = None) -> Dict:
        """Resumen de citas de la semana"""
        if fecha_inicio is None:
            hoy = datetime.date.today()
            fecha_inicio = (hoy - datetime.timedelta(days=hoy.weekday())).strftime("%Y-%m-%d")
        
        try:
            fecha_obj = datetime.datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
            fecha_fin = fecha_obj + datetime.timedelta(days=6)
        except ValueError:
            return {}
        
        citas_semana = [
            c for c in self.appointments 
            if fecha_obj.strftime("%Y-%m-%d") <= c.fecha <= fecha_fin.strftime("%Y-%m-%d")
        ]
        
        por_dia = {}
        for dia in range(7):
            fecha = (fecha_obj + datetime.timedelta(days=dia)).strftime("%Y-%m-%d")
            por_dia[fecha] = len([c for c in citas_semana if c.fecha == fecha])
        
        return {
            "total_semana": len(citas_semana),
            "por_dia": por_dia,
            "promedio_diario": len(citas_semana) / 7 if citas_semana else 0,
            "tasa_presentismo": self._calcular_tasa_presentismo(citas_semana)
        }
    
    def get_tipos_cita_resumen(self) -> Dict[str, int]:
        """Cuenta citas por tipo"""
        tipos = {}
        for cita in self.appointments:
            if cita.estado != AppointmentStatus.CANCELLED:
                tipo_str = cita.tipo.value
                tipos[tipo_str] = tipos.get(tipo_str, 0) + 1
        return tipos
    
    def get_doctores_resumen(self) -> Dict[str, Dict]:
        """Estadísticas por doctor/optometra"""
        doctores = {}
        
        for cita in self.appointments:
            doctor = cita.optometra or cita.doctor or "Sin asignar"
            
            if doctor not in doctores:
                doctores[doctor] = {
                    "total": 0,
                    "completadas": 0,
                    "pendientes": 0,
                    "canceladas": 0
                }
            
            doctores[doctor]["total"] += 1
            
            if cita.estado == AppointmentStatus.COMPLETED:
                doctores[doctor]["completadas"] += 1
            elif cita.estado == AppointmentStatus.PENDING:
                doctores[doctor]["pendientes"] += 1
            elif cita.estado == AppointmentStatus.CANCELLED:
                doctores[doctor]["canceladas"] += 1
        
        return doctores
    
    @staticmethod
    def _calcular_tasa_presentismo(citas: List[Appointment]) -> float:
        """Calcula porcentaje de pacientes que se presentaron"""
        if not citas:
            return 0.0
        
        presentados = len([c for c in citas if c.estado in [
            AppointmentStatus.COMPLETED,
            AppointmentStatus.COMPLETED
        ]])
        
        no_canceladas = len([c for c in citas if c.estado != AppointmentStatus.CANCELLED])
        
        return (presentados / no_canceladas * 100) if no_canceladas > 0 else 0.0
    
    def get_citas_proximamente(self, horas: int = 24) -> List[Appointment]:
        """Retorna citas en las próximas X horas"""
        ahora = datetime.datetime.now()
        limite = ahora + datetime.timedelta(hours=horas)
        
        proximas = []
        for cita in self.appointments:
            if cita.estado == AppointmentStatus.PENDING:
                try:
                    fecha_hora = datetime.datetime.strptime(
                        f"{cita.fecha} {cita.hora}",
                        "%Y-%m-%d %H:%M"
                    )
                    if ahora <= fecha_hora <= limite:
                        proximas.append(cita)
                except ValueError:
                    continue
        
        return sorted(proximas, key=lambda c: f"{c.fecha} {c.hora}")


class AppointmentReminders:
    """Gestión mejorada de recordatorios"""
    
    @staticmethod
    def get_citas_para_recordar(appointments: List[Appointment]) -> Dict[str, List[Appointment]]:
        """
        Agrupa citas que necesitan recordatorios por tipo.
        Retorna:
        {
            "whatsapp_24h": [...],
            "whatsapp_1h": [...],
            "sms_24h": [...]
        }
        """
        ahora = datetime.datetime.now()
        citas_por_tipo = {
            "whatsapp_24h": [],
            "whatsapp_1h": [],
            "sms_24h": []
        }
        
        for cita in appointments:
            if cita.estado != AppointmentStatus.PENDING:
                continue
            
            try:
                fecha_hora = datetime.datetime.strptime(
                    f"{cita.fecha} {cita.hora}",
                    "%Y-%m-%d %H:%M"
                )
                
                minutos_restantes = (fecha_hora - ahora).total_seconds() / 60
                
                # Recordatorio 24 horas antes
                if 1410 <= minutos_restantes <= 1440:  # 23.5-24 horas
                    citas_por_tipo["whatsapp_24h"].append(cita)
                    citas_por_tipo["sms_24h"].append(cita)
                
                # Recordatorio 1 hora antes
                if 55 <= minutos_restantes <= 65:  # 55-65 minutos
                    citas_por_tipo["whatsapp_1h"].append(cita)
            
            except ValueError:
                continue
        
        return citas_por_tipo
    
    @staticmethod
    def generar_mensaje_recordatorio(cita: Appointment, paciente_info: Dict = None) -> str:
        """Genera un mensaje de recordatorio personalizado"""
        
        nombre_paciente = "Paciente"
        if paciente_info:
            nombre_paciente = paciente_info.get('nombre', 'Paciente')
        
        mensaje = f"""Recordatorio de Cita 👁️
        
Hola {nombre_paciente},

Te recordamos que tienes una cita programada:

📅 Fecha: {cita.fecha}
🕐 Hora: {cita.hora}
📋 Tipo: {cita.tipo.value}

Por favor, confirma tu asistencia o comunícate si necesitas cambios.

¡Gracias por confiar en nosotros! 💙
        """
        
        return mensaje.strip()
