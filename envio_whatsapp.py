import os
import webbrowser
import datetime
import json
from utils.notifications import citas_pendientes_para_usuario, cargar_citas

# Leer el número de WhatsApp desde whatsapp.json
def obtener_numero_whatsapp(username):
    whatsapp_json_path = os.path.join('VISO', username, 'data', 'whatsapp.json')
    if not os.path.exists(whatsapp_json_path):
        return None
    try:
        with open(whatsapp_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('whatsapp')
    except Exception:
        return None

def enviar_recordatorios_whatsapp(username, dni):
    numero = obtener_numero_whatsapp(username)
    if not numero:
        print('No hay número de WhatsApp configurado.')
        return
    # Cargar todas las citas y enviar recordatorio para cada una pendiente en las próximas 24h
    from utils.notifications import cargar_citas
    import datetime
    ahora = datetime.datetime.now()
    citas = cargar_citas()
    import time
    for cita in citas:
        fecha_str = cita.get('fecha', '')
        hora_str = cita.get('hora', '00:00')
        try:
            dt_cita = datetime.datetime.strptime(f"{fecha_str} {hora_str}", "%Y-%m-%d %H:%M")
            delta = (dt_cita - ahora).total_seconds() / 3600
            if 0 < delta <= 24:
                paciente = cita.get('nombre', 'Paciente')
                mensaje = f"Tienes una cita pendiente con {paciente} el {fecha_str} a las {hora_str}."
                mensaje_url = mensaje.replace(' ', '%20')
                whatsapp_app_url = f"whatsapp://send?phone={numero}&text={mensaje_url}"
                try:
                    opened = webbrowser.open(whatsapp_app_url)
                    if not opened:
                        raise Exception('No se pudo abrir WhatsApp Desktop.')
                except Exception:
                    web_url = f"https://wa.me/{numero}?text={mensaje_url}"
                    webbrowser.open(web_url)
                print(f"Enviado recordatorio a WhatsApp: {mensaje}")
                time.sleep(2)
        except Exception:
            continue

if __name__ == "__main__":
    # Leer usuario desde VISO/sesion.txt
    sesion_path = os.path.join('VISO', 'sesion.txt')
    if not os.path.exists(sesion_path):
        print('No se encontró el archivo de sesión.')
        exit(1)
    with open(sesion_path, 'r', encoding='utf-8') as f:
        usuario = f.read().strip()
    # Buscar todas las citas pendientes para ese usuario (dni=usuario)
    enviar_recordatorios_whatsapp(usuario, usuario)
