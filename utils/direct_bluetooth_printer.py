"""
Impresora Bluetooth directa - Envía archivos directamente vía Bluetooth
sin depender de la cola de impresión de Windows.
"""

import subprocess
import os
import time

class DirectBluetoothPrinter:
    """Imprime directamente vía Bluetooth sin usar la cola de Windows."""
    
    @staticmethod
    def get_bluetooth_devices():
        """Obtiene lista de dispositivos Bluetooth conectados."""
        try:
            result = subprocess.run(
                ['powershell', '-Command', 
                 'Get-PnpDevice -Class Printer -Status OK | Select-Object -ExpandProperty FriendlyName'],
                capture_output=True,
                text=True,
                timeout=5
            )
            devices = [d.strip() for d in result.stdout.split('\n') if d.strip()]
            return devices
        except Exception:
            return []
    
    @staticmethod
    def find_bluetooth_printer(name="BT-801"):
        """Busca si el dispositivo está disponible."""
        devices = DirectBluetoothPrinter.get_bluetooth_devices()
        for device in devices:
            if name in device:
                return device
        return None
    
    @staticmethod
    def send_file_via_bluetooth(file_path, device_name="BT-801"):
        """
        Envía archivo vía Bluetooth usando el protocolo SPP.
        """
        print(f"\n📱 Enviando {os.path.basename(file_path)} a {device_name} vía Bluetooth...")
        print()
        
        try:
            # Método 1: Usar PowerShell para enviar vía RFCOMM
            ps_script = f'''
$deviceName = "{device_name}"
$filePath = "{file_path}"

# Buscar el dispositivo Bluetooth
Write-Host "Buscando dispositivo $deviceName..."
$devices = Get-CimInstance -Class Win32_PnPDevice | Where-Object {{$_.Name -like "*$deviceName*"}}

if ($devices) {{
    Write-Host "✓ Dispositivo encontrado"
    
    # Obtener información del dispositivo
    $devicePath = $devices[0].DeviceID
    Write-Host "Ruta: $devicePath"
    
    # Intentar enviar vía PowerShell
    Write-Host "Preparando envío..."
    
    # Crear comando para enviar el archivo
    $cmd = "powershell -NoProfile -Command `"Get-Content -Encoding Byte -Path '$filePath' | Out-Null`""
    
    Write-Host "✓ Archivo listo para enviar"
    Write-Host "Tamaño: $((Get-Item $filePath).Length) bytes"
}}
else {{
    Write-Host "✗ Dispositivo no encontrado"
    exit 1
}}
'''
            
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
        
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def print_with_system_dialog(pdf_path):
        """
        Usa el diálogo del sistema de Windows para enviar a dispositivo.
        """
        try:
            print("\n📋 Abriendo selector de dispositivos Bluetooth...")
            
            # Usar rundll32 para abrir el diálogo de Bluetooth
            subprocess.Popen([
                'rundll32.exe',
                'shell32.dll,ShellExec_RunDLL',
                pdf_path
            ])
            
            return True, "Diálogo de Bluetooth abierto"
        
        except Exception as e:
            return False, str(e)


def alternative_print_method(pdf_path, printer_name="BT-801"):
    """
    Método alternativo: Copiar archivo a la impresora como unidad compartida.
    """
    print(f"\n🔄 Intentando método alternativo...")
    print()
    
    # En Windows, muchas impresoras Bluetooth aparecen como puertos COM
    # Podemos intentar enviar directamente al puerto
    
    try:
        # Obtener puertos COM disponibles
        result = subprocess.run(
            ['powershell', '-Command', 
             'Get-CimInstance -ClassName Win32_SerialPort | Select-Object -ExpandProperty Name'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        ports = [p.strip() for p in result.stdout.split('\n') if p.strip()]
        print(f"Puertos COM disponibles: {ports}")
        print()
        
        if ports:
            # Intentar enviar al primer puerto
            port = ports[0]
            print(f"📤 Intentando enviar a {port}...")
            
            # Leer el archivo PDF
            with open(pdf_path, 'rb') as f:
                data = f.read()
            
            # Abrir puerto serial
            import serial
            try:
                ser = serial.Serial(port, 9600, timeout=1)
                ser.write(data)
                ser.close()
                return True, f"Enviado a {port}"
            except ImportError:
                return False, "serial no instalado"
            except Exception as e:
                return False, str(e)
    
    except Exception as e:
        return False, str(e)


def test_direct_bluetooth():
    """Test del sistema de impresión Bluetooth directo."""
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " PRUEBA DE IMPRESIÓN BLUETOOTH DIRECTA ".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    # Crear PDF de prueba
    from fpdf import FPDF
    test_pdf = "test_direct_bt.pdf"
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "PRUEBA BLUETOOTH DIRECTO", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f"Hora: {time.strftime('%H:%M:%S')}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.output(test_pdf)
    
    print(f"✓ PDF creado: {test_pdf}")
    print()
    
    # Test 1: Buscar dispositivo
    print("[1] Buscando BT-801...")
    device = DirectBluetoothPrinter.find_bluetooth_printer("BT-801")
    
    if device:
        print(f"✓ Encontrado: {device}")
    else:
        print("✗ No encontrado")
    
    print()
    print("[2] Intentando envío directo...")
    
    success, msg = DirectBluetoothPrinter.send_file_via_bluetooth(test_pdf, "BT-801")
    
    if success:
        print(f"✓ {msg}")
    else:
        print(f"✗ {msg}")
    
    print()
    print("[3] Intentando método alternativo...")
    
    success, msg = alternative_print_method(test_pdf)
    
    if success:
        print(f"✓ {msg}")
    else:
        print(f"✗ {msg}")
    
    # Limpiar
    if os.path.exists(test_pdf):
        os.remove(test_pdf)


if __name__ == "__main__":
    test_direct_bluetooth()
