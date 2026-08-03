import json
import datetime
from typing import List, Dict

CITAS_PATH = r"VISO/232456789/data/citas.json"


def cargar_citas(path=CITAS_PATH) -> List[Dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def citas_pendientes_para_usuario(dni: str, ahora: datetime.datetime = None) -> List[Dict]:
    if ahora is None:
        ahora = datetime.datetime.now()
    citas = cargar_citas()
    pendientes = []
    for cita in citas:
        if cita.get("dni") == dni:
            fecha_str = cita.get("fecha", "")
            hora_str = cita.get("hora", "00:00")
            try:
                dt_cita = datetime.datetime.strptime(f"{fecha_str} {hora_str}", "%Y-%m-%d %H:%M")
                delta = (dt_cita - ahora).total_seconds() / 3600
                if 0 < delta <= 24:
                    pendientes.append({"cita": cita, "horas": delta})
            except Exception:
                continue
    return pendientes

def contar_notificaciones(dni: str) -> int:
    pendientes = citas_pendientes_para_usuario(dni)
    # Notificamos todas las citas dentro de 24h (incluyendo 1h, 2h, etc)
    return len(pendientes)

def obtener_mensajes_notificaciones(dni: str) -> List[str]:
    pendientes = citas_pendientes_para_usuario(dni)
    mensajes = []
    for p in pendientes:
        horas = p["horas"]
        cita = p["cita"]
        if horas < 1.5:
            tiempo = "en 1 hora"
        elif horas < 2.5:
            tiempo = "en 2 horas"
        elif horas < 6.5:
            tiempo = f"en {int(round(horas))} horas"
        elif horas < 24.5:
            tiempo = f"en {int(round(horas))} horas"
        else:
            tiempo = f"pronto"
        mensajes.append(f"Tienes una cita el {cita['fecha']} a las {cita['hora']} {tiempo}.")
    return mensajes
