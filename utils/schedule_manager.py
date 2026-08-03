"""
Gestor de horarios laborales para VISO.
Define franjas disponibles y detecta conflictos.
"""

import json
import datetime
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from enum import Enum

class DayOfWeek(Enum):
    """Días de la semana"""
    LUNES = "Lunes"
    MARTES = "Martes"
    MIERCOLES = "Miércoles"
    JUEVES = "Jueves"
    VIERNES = "Viernes"
    SABADO = "Sábado"
    DOMINGO = "Domingo"


class ScheduleBlock:
    """Bloque de tiempo disponible"""
    
    def __init__(self, inicio: str, fin: str):
        """
        Crea un bloque de horario.
        
        Args:
            inicio: Hora de inicio (HH:MM)
            fin: Hora de fin (HH:MM)
        """
        self.inicio = inicio
        self.fin = fin
    
    def contiene_hora(self, hora: str, duracion: int = 30) -> bool:
        """Verifica si una hora cabe dentro del bloque"""
        try:
            inicio_dt = datetime.datetime.strptime(self.inicio, "%H:%M")
            fin_dt = datetime.datetime.strptime(self.fin, "%H:%M")
            hora_dt = datetime.datetime.strptime(hora, "%H:%M")
            hora_fin_dt = hora_dt + datetime.timedelta(minutes=duracion)
            
            return inicio_dt <= hora_dt and hora_fin_dt <= fin_dt
        except ValueError:
            return False
    
    def to_dict(self) -> Dict:
        return {"inicio": self.inicio, "fin": self.fin}
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ScheduleBlock":
        return cls(data["inicio"], data["fin"])


class WorkingSchedule:
    """Horario laboral de un optómetra"""
    
    def __init__(self, optometra: str):
        """
        Inicializa horario laboral.
        
        Args:
            optometra: Nombre del optómetra
        """
        self.optometra = optometra
        
        # Horario por defecto: Lunes a Viernes, 9:00 a 18:00, Sábado 9:00 a 14:00
        self.horarios: Dict[str, List[ScheduleBlock]] = {
            "Lunes": [ScheduleBlock("09:00", "13:00"), ScheduleBlock("14:00", "18:00")],
            "Martes": [ScheduleBlock("09:00", "13:00"), ScheduleBlock("14:00", "18:00")],
            "Miércoles": [ScheduleBlock("09:00", "13:00"), ScheduleBlock("14:00", "18:00")],
            "Jueves": [ScheduleBlock("09:00", "13:00"), ScheduleBlock("14:00", "18:00")],
            "Viernes": [ScheduleBlock("09:00", "13:00"), ScheduleBlock("14:00", "18:00")],
            "Sábado": [ScheduleBlock("09:00", "14:00")],
            "Domingo": []  # No labora
        }
        
        # Fechas donde no labora (días feriados, vacaciones)
        self.dias_no_laborables: List[str] = []
    
    def establecer_horario_dia(self, dia: str, bloques: List[Tuple[str, str]]):
        """Establece el horario para un día específico"""
        self.horarios[dia] = [ScheduleBlock(inicio, fin) for inicio, fin in bloques]
    
    def agregar_dia_no_laborable(self, fecha: str):
        """Agrega un día no laborable (formato YYYY-MM-DD)"""
        if fecha not in self.dias_no_laborables:
            self.dias_no_laborables.append(fecha)
    
    def remover_dia_no_laborable(self, fecha: str):
        """Remueve un día de la lista no laborable"""
        self.dias_no_laborables = [f for f in self.dias_no_laborables if f != fecha]
    
    def esta_disponible(self, fecha: str, hora: str, duracion: int = 30) -> bool:
        """
        Verifica si hay disponibilidad en una fecha y hora.
        
        Args:
            fecha: Fecha (YYYY-MM-DD)
            hora: Hora (HH:MM)
            duracion: Duración en minutos
        
        Returns:
            True si está disponible, False en caso contrario
        """
        # Verificar si es día no laborable
        if fecha in self.dias_no_laborables:
            return False
        
        # Obtener día de la semana
        try:
            fecha_dt = datetime.datetime.strptime(fecha, "%Y-%m-%d")
            dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            dia_semana = dias[fecha_dt.weekday()]
            
            # Verificar si tiene bloques horarios ese día
            bloques = self.horarios.get(dia_semana, [])
            if not bloques:
                return False
            
            # Verificar si la hora cabe en algún bloque
            for bloque in bloques:
                if bloque.contiene_hora(hora, duracion):
                    return True
            
            return False
        except ValueError:
            return False
    
    def obtener_franjas_disponibles(self, fecha: str, duracion: int = 30) -> List[str]:
        """
        Retorna todas las franjas disponibles para una fecha y duración.
        
        Args:
            fecha: Fecha (YYYY-MM-DD)
            duracion: Duración en minutos
        
        Returns:
            Lista de horas disponibles (HH:MM)
        """
        franjas = []
        
        if not self.esta_disponible(fecha, "09:00", duracion):
            return franjas
        
        try:
            fecha_dt = datetime.datetime.strptime(fecha, "%Y-%m-%d")
            dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            dia_semana = dias[fecha_dt.weekday()]
            
            bloques = self.horarios.get(dia_semana, [])
            
            for bloque in bloques:
                inicio_dt = datetime.datetime.strptime(bloque.inicio, "%H:%M")
                fin_dt = datetime.datetime.strptime(bloque.fin, "%H:%M")
                
                hora_actual = inicio_dt
                while hora_actual + datetime.timedelta(minutes=duracion) <= fin_dt:
                    franjas.append(hora_actual.strftime("%H:%M"))
                    hora_actual += datetime.timedelta(minutes=30)  # Incrementar de 30 en 30 min
            
            return franjas
        except ValueError:
            return franjas
    
    def to_dict(self) -> Dict:
        return {
            "optometra": self.optometra,
            "horarios": {
                dia: [b.to_dict() for b in bloques]
                for dia, bloques in self.horarios.items()
            },
            "dias_no_laborables": self.dias_no_laborables
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "WorkingSchedule":
        ws = cls(data["optometra"])
        ws.horarios = {
            dia: [ScheduleBlock.from_dict(b) for b in bloques]
            for dia, bloques in data.get("horarios", {}).items()
        }
        ws.dias_no_laborables = data.get("dias_no_laborables", [])
        return ws


class ScheduleManager:
    """Gestor centralizado de horarios laborales"""
    
    def __init__(self, username: str, base_path: str = "VISO"):
        """
        Inicializa el gestor de horarios.
        
        Args:
            username: Nombre de usuario
            base_path: Ruta base
        """
        self.username = username
        self.horarios_path = Path(base_path) / username / "data" / "horarios.json"
        self.horarios_path.parent.mkdir(parents=True, exist_ok=True)
        self.horarios: Dict[str, WorkingSchedule] = {}
        self.load_horarios()
    
    def load_horarios(self):
        """Carga horarios del archivo JSON"""
        try:
            if self.horarios_path.exists():
                with open(self.horarios_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.horarios = {
                        optometra: WorkingSchedule.from_dict(h)
                        for optometra, h in data.items()
                    }
            else:
                self.horarios = {}
        except Exception as e:
            print(f"Error cargando horarios: {e}")
            self.horarios = {}
    
    def save_horarios(self):
        """Guarda horarios en archivo JSON"""
        try:
            with open(self.horarios_path, 'w', encoding='utf-8') as f:
                json.dump(
                    {opt: h.to_dict() for opt, h in self.horarios.items()},
                    f,
                    ensure_ascii=False,
                    indent=2
                )
        except Exception as e:
            print(f"Error guardando horarios: {e}")
    
    def obtener_horario(self, optometra: str) -> Optional[WorkingSchedule]:
        """Obtiene el horario de un optómetra"""
        if optometra not in self.horarios:
            # Crear horario por defecto si no existe
            self.horarios[optometra] = WorkingSchedule(optometra)
            self.save_horarios()
        
        return self.horarios[optometra]
    
    def establecer_horario(self, optometra: str, ws: WorkingSchedule):
        """Establece el horario de un optómetra"""
        self.horarios[optometra] = ws
        self.save_horarios()
    
    def obtener_proxima_disponibilidad(self, optometra: str, duracion: int = 30) -> Optional[Tuple[str, str]]:
        """
        Obtiene la próxima fecha y hora disponible.
        
        Args:
            optometra: Nombre del optómetra
            duracion: Duración de la cita en minutos
        
        Returns:
            Tupla (fecha, hora) o None si no hay disponibilidad
        """
        ws = self.obtener_horario(optometra)
        fecha_actual = datetime.date.today()
        
        # Buscar en los próximos 30 días
        for i in range(30):
            fecha = (fecha_actual + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            franjas = ws.obtener_franjas_disponibles(fecha, duracion)
            
            if franjas:
                return (fecha, franjas[0])
        
        return None

    def obtener_franjas_disponibles(self, fecha: str, duracion: int = 30, optometra: Optional[str] = None) -> List[str]:
        """
        Obtiene franjas disponibles para una fecha.
        Delegado al WorkingSchedule del optómetra.
        """
        if not optometra:
            optometra = self.username
        
        ws = self.obtener_horario(optometra)
        return ws.obtener_franjas_disponibles(fecha, duracion)
