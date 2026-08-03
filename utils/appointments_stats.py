"""
Sistema de estadísticas y reportes para citas en VISO.
Proporciona análisis y métricas sobre el desempeño del consultorio.
"""

import json
import datetime
from typing import Dict, List, Tuple
from pathlib import Path
from collections import defaultdict, Counter
from utils.appointments_model import (
    Appointment, AppointmentStatus, AppointmentType, AppointmentsManager
)


class AppointmentsStatistics:
    """Estadísticas y análisis de citas"""
    
    def __init__(self, username: str, base_path: str = "VISO"):
        """
        Inicializa el gestor de estadísticas.
        
        Args:
            username: Nombre de usuario
            base_path: Ruta base
        """
        self.username = username
        self.base_path = base_path
        self.manager = AppointmentsManager(username)
    
    def obtener_estadisticas_generales(self) -> Dict:
        """Obtiene estadísticas generales de citas"""
        citas = self.manager.citas
        
        return {
            "total_citas": len(citas),
            "citas_pendientes": len([c for c in citas if c.estado == AppointmentStatus.PENDING]),
            "citas_completadas": len([c for c in citas if c.estado == AppointmentStatus.COMPLETED]),
            "citas_canceladas": len([c for c in citas if c.estado == AppointmentStatus.CANCELLED]),
            "citas_no_asistio": len([c for c in citas if c.estado == AppointmentStatus.NO_SHOW]),
            "citas_reprogramadas": len([c for c in citas if c.estado == AppointmentStatus.RESCHEDULED]),
        }
    
    def calcular_tasa_no_asistencia(self) -> float:
        """Calcula el porcentaje de no-asistencias"""
        citas = self.manager.citas
        citas_pasadas = [c for c in citas if c.is_overdue()]
        
        if not citas_pasadas:
            return 0.0
        
        no_asistencias = len([c for c in citas_pasadas if c.estado == AppointmentStatus.NO_SHOW])
        return (no_asistencias / len(citas_pasadas)) * 100
    
    def calcular_tasa_cancelacion(self) -> float:
        """Calcula el porcentaje de cancelaciones"""
        citas = self.manager.citas
        citas_pasadas = [c for c in citas if c.is_overdue()]
        
        if not citas_pasadas:
            return 0.0
        
        cancelaciones = len([c for c in citas_pasadas if c.estado == AppointmentStatus.CANCELLED])
        return (cancelaciones / len(citas_pasadas)) * 100
    
    def calcular_tasa_completacion(self) -> float:
        """Calcula el porcentaje de citas completadas"""
        citas = self.manager.citas
        citas_pasadas = [c for c in citas if c.is_overdue()]
        
        if not citas_pasadas:
            return 0.0
        
        completadas = len([c for c in citas_pasadas if c.estado == AppointmentStatus.COMPLETED])
        return (completadas / len(citas_pasadas)) * 100
    
    def obtener_tipos_citas_distribucion(self) -> Dict[str, int]:
        """Obtiene la distribución de tipos de citas"""
        citas = self.manager.citas
        distribucion = Counter(c.tipo.value for c in citas)
        return dict(distribucion)
    
    def obtener_citas_por_doctor(self) -> Dict[str, int]:
        """Obtiene cantidad de citas por doctor"""
        citas = self.manager.citas
        por_doctor = Counter(c.doctor for c in citas)
        return dict(por_doctor)
    
    def obtener_citas_por_dia(self, dias: int = 30) -> Dict[str, int]:
        """Obtiene cantidad de citas por día en los últimos N días"""
        citas = self.manager.citas
        fecha_limite = datetime.datetime.now() - datetime.timedelta(days=dias)
        
        por_dia = defaultdict(int)
        for cita in citas:
            try:
                fecha = datetime.datetime.strptime(cita.fecha, "%Y-%m-%d")
                if fecha >= fecha_limite:
                    por_dia[cita.fecha] += 1
            except ValueError:
                pass
        
        return dict(sorted(por_dia.items()))
    
    def obtener_horas_pico(self) -> Dict[str, int]:
        """Identifica las horas con más demanda de citas"""
        citas = self.manager.citas
        por_hora = Counter()
        
        for cita in citas:
            try:
                hora = cita.hora.split(":")[0]  # Extrae la hora
                por_hora[hora] += 1
            except (ValueError, AttributeError):
                pass
        
        return dict(por_hora.most_common(10))  # Top 10 horas
    
    def obtener_duracion_promedio(self) -> float:
        """Calcula la duración promedio de las citas"""
        citas = self.manager.citas
        
        if not citas:
            return 0.0
        
        total_duracion = sum(c.duracion_minutos for c in citas)
        return total_duracion / len(citas)
    
    def obtener_citas_proximas(self, dias: int = 7) -> List[Appointment]:
        """Obtiene citas próximas a realizarse"""
        citas = self.manager.citas
        fecha_limite = datetime.datetime.now() + datetime.timedelta(days=dias)
        
        proximas = []
        for cita in citas:
            if cita.estado == AppointmentStatus.PENDING:
                try:
                    fecha = datetime.datetime.strptime(cita.fecha, "%Y-%m-%d")
                    if datetime.datetime.now() <= fecha <= fecha_limite:
                        proximas.append(cita)
                except ValueError:
                    pass
        
        return sorted(proximas, key=lambda c: (c.fecha, c.hora))
    
    def obtener_pacientes_frecuentes(self, limite: int = 10) -> List[Tuple[str, int]]:
        """Obtiene los pacientes con más citas"""
        citas = self.manager.citas
        por_paciente = Counter(c.dni for c in citas)
        return por_paciente.most_common(limite)
    
    def obtener_reporte_semanal(self) -> Dict:
        """Genera un reporte semanal de citas"""
        ahora = datetime.datetime.now()
        inicio_semana = ahora - datetime.timedelta(days=ahora.weekday())
        fin_semana = inicio_semana + datetime.timedelta(days=6)
        
        citas = self.manager.citas
        citas_semana = []
        
        for cita in citas:
            try:
                fecha = datetime.datetime.strptime(cita.fecha, "%Y-%m-%d")
                if inicio_semana <= fecha <= fin_semana:
                    citas_semana.append(cita)
            except ValueError:
                pass
        
        return {
            "periodo": f"{inicio_semana.strftime('%Y-%m-%d')} a {fin_semana.strftime('%Y-%m-%d')}",
            "total_citas": len(citas_semana),
            "completadas": len([c for c in citas_semana if c.estado == AppointmentStatus.COMPLETED]),
            "pendientes": len([c for c in citas_semana if c.estado == AppointmentStatus.PENDING]),
            "canceladas": len([c for c in citas_semana if c.estado == AppointmentStatus.CANCELLED]),
            "no_asistio": len([c for c in citas_semana if c.estado == AppointmentStatus.NO_SHOW]),
            "citas": citas_semana
        }
    
    def obtener_reporte_mensual(self) -> Dict:
        """Genera un reporte mensual de citas"""
        ahora = datetime.datetime.now()
        inicio_mes = ahora.replace(day=1)
        
        # Primer día del próximo mes
        if ahora.month == 12:
            fin_mes = inicio_mes.replace(year=ahora.year + 1, month=1) - datetime.timedelta(days=1)
        else:
            fin_mes = inicio_mes.replace(month=ahora.month + 1) - datetime.timedelta(days=1)
        
        citas = self.manager.citas
        citas_mes = []
        
        for cita in citas:
            try:
                fecha = datetime.datetime.strptime(cita.fecha, "%Y-%m-%d")
                if inicio_mes <= fecha <= fin_mes:
                    citas_mes.append(cita)
            except ValueError:
                pass
        
        return {
            "periodo": f"{inicio_mes.strftime('%B %Y')}",
            "total_citas": len(citas_mes),
            "completadas": len([c for c in citas_mes if c.estado == AppointmentStatus.COMPLETED]),
            "pendientes": len([c for c in citas_mes if c.estado == AppointmentStatus.PENDING]),
            "canceladas": len([c for c in citas_mes if c.estado == AppointmentStatus.CANCELLED]),
            "no_asistio": len([c for c in citas_mes if c.estado == AppointmentStatus.NO_SHOW]),
            "tasa_no_asistencia": f"{self.calcular_tasa_no_asistencia():.1f}%",
            "tasa_cancelacion": f"{self.calcular_tasa_cancelacion():.1f}%",
            "tasa_completacion": f"{self.calcular_tasa_completacion():.1f}%",
            "citas": citas_mes
        }
    
    def exportar_reporte_json(self, nombre_archivo: str = "reporte_citas.json") -> str:
        """Exporta un reporte completo a JSON"""
        reporte = {
            "fecha_generacion": datetime.datetime.now().isoformat(),
            "usuario": self.username,
            "estadisticas_generales": self.obtener_estadisticas_generales(),
            "tasas": {
                "no_asistencia": f"{self.calcular_tasa_no_asistencia():.1f}%",
                "cancelacion": f"{self.calcular_tasa_cancelacion():.1f}%",
                "completacion": f"{self.calcular_tasa_completacion():.1f}%"
            },
            "distribucion_tipos": self.obtener_tipos_citas_distribucion(),
            "por_doctor": self.obtener_citas_por_doctor(),
            "horas_pico": self.obtener_horas_pico(),
            "duracion_promedio_minutos": f"{self.obtener_duracion_promedio():.1f}",
            "pacientes_frecuentes": [
                {"dni": dni, "cantidad": cantidad}
                for dni, cantidad in self.obtener_pacientes_frecuentes()
            ],
            "reporte_mensual": self.obtener_reporte_mensual(),
            "reporte_semanal": self.obtener_reporte_semanal()
        }
        
        ruta = Path(self.base_path) / self.username / "data" / nombre_archivo
        ruta.parent.mkdir(parents=True, exist_ok=True)
        
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(reporte, f, ensure_ascii=False, indent=2, default=str)
        
        return str(ruta)
    
    def obtener_resumen_dashboard(self) -> Dict:
        """Obtiene un resumen para mostrar en el dashboard"""
        estadisticas = self.obtener_estadisticas_generales()
        proximas = self.obtener_citas_proximas(7)
        
        return {
            "hoy": datetime.datetime.now().strftime("%Y-%m-%d"),
            "total_citas": estadisticas['total_citas'],
            "citas_hoy": len([c for c in proximas if c.fecha == datetime.datetime.now().strftime("%Y-%m-%d")]),
            "proximas_semana": len(proximas),
            "pendientes": estadisticas['citas_pendientes'],
            "completadas": estadisticas['citas_completadas'],
            "no_asistencias": estadisticas['citas_no_asistio'],
            "tasa_no_asistencia": f"{self.calcular_tasa_no_asistencia():.1f}%",
            "duracion_promedio": f"{self.obtener_duracion_promedio():.0f} min",
            "doctor_mas_activo": max(self.obtener_citas_por_doctor().items(), 
                                     key=lambda x: x[1])[0] if self.obtener_citas_por_doctor() else "N/A"
        }
