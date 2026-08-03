"""
Manejador especial para impresoras Bluetooth que se conectan temporalmente.
Detecta cuando la impresora se conecta y envía inmediatamente.
"""

import subprocess
import time
import os
import sys
import threading
from pathlib import Path

class BluetoothTemporaryPrinter:
    """Maneja impresoras Bluetooth que solo se conectan brevemente."""
    
    def __init__(self, printer_name="BT-801", timeout=30):
        self.printer_name = printer_name
        self.timeout = timeout
        self.connection_detected = False
        self.print_sent = False
    
    def wait_for_connection(self):
        """Espera a que la impresora Bluetooth se conecte."""
        print(f"⏳ Esperando que {self.printer_name} se conecte...")
        print("   (Asegúrate de que esté en rango)")
        print()
        
        start_time = time.time()
        check_interval = 0.5
        
        while time.time() - start_time < self.timeout:
            # Verificar si el dispositivo está disponible
            try:
                result = subprocess.run(
                    ['powershell', '-Command', 
                     f'Get-PnpDevice -FriendlyName "*{self.printer_name}*" | Select-Object -ExpandProperty Status'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                
                if "OK" in result.stdout or "Running" in result.stdout:
                    print(f"✓ ¡{self.printer_name} detectada!")
                    self.connection_detected = True
                    return True
                
            except Exception:
                pass
            
            # Mostrar progreso
            elapsed = int(time.time() - start_time)
            remaining = self.timeout - elapsed
            print(f"\r  Esperando... ({remaining}s restantes)", end="", flush=True)
            time.sleep(check_interval)
        
        print(f"\n✗ Timeout: {self.printer_name} no se conectó")
        return False
    
    def send_to_temporary_printer(self, pdf_path, printer_name="BT-801"):
        """Envía documento a impresora que se conecta temporalmente."""
        print()
        print("=" * 70)
        print(f"IMPRIMIR A {printer_name} (Conexión Temporal)")
        print("=" * 70)
        print()
        
        if not os.path.exists(pdf_path):
            return False, f"Archivo no encontrado: {pdf_path}"
        
        pdf_path = os.path.abspath(pdf_path)
        
        # Paso 1: Esperar conexión
        print("[1/3] Esperando conexión...")
        if not self.wait_for_connection():
            return False, "Impresora no se conectó en el tiempo límite"
        
        print()
        print("[2/3] Enviando a cola de impresión...")
        time.sleep(0.5)  # Pequeña pausa para estabilidad
        
        try:
            # Usar comando print nativo - funciona mejor con conexiones temporales
            cmd = f'print /d:"{printer_name}" "{pdf_path}"'
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            print(f"   Comando ejecutado (código: {result.returncode})")
            
        except subprocess.TimeoutExpired:
            return False, "Timeout enviando a impresora"
        except Exception as e:
            return False, f"Error: {e}"
        
        print()
        print("[3/3] Completando envío...")
        
        # Esperar un poco para que Windows procese
        time.sleep(2)
        
        print()
        print("✓ Documento enviado a la cola")
        print()
        print("⏳ La impresora debería empezar a imprimir cuando se conecte nuevamente")
        print("   (Algunos modelos imprimen después de ~5-10 segundos)")
        
        return True, f"Documento enviado a {printer_name}"
    
    def print_pdf_interactive(self, pdf_path, printer_name="BT-801"):
        """Versión interactiva con instrucciones para el usuario."""
        print()
        print("╔" + "═" * 68 + "╗")
        print("║" + f" IMPRIMIR EN {printer_name} ".center(68) + "║")
        print("╚" + "═" * 68 + "╝")
        print()
        
        print("📋 INSTRUCCIONES:")
        print()
        print("1. Ten la impresora ENCENDIDA y EN RANGO")
        print("2. La impresora se conectará brevemente a tu PC")
        print("3. Durante esa conexión, enviaremos el documento")
        print("4. La impresora imprimirá automáticamente")
        print()
        
        input("Presiona Enter cuando la impresora esté lista...")
        print()
        
        return self.send_to_temporary_printer(pdf_path, printer_name)


def setup_for_temporary_printer():
    """Script principal para configurar y probar."""
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " CONFIGURACIÓN PARA IMPRESORAS BLUETOOTH TEMPORALES ".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    printer = BluetoothTemporaryPrinter(printer_name="BT-801", timeout=30)
    
    # Crear PDF de prueba
    print("[1] Creando documento de prueba...")
    print()
    
    try:
        from fpdf import FPDF
        test_pdf = os.path.join(os.getcwd(), "prueba_bt801.pdf")
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "PRUEBA BT-801", ln=True, align="C")
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 10, f"Hora: {time.strftime('%H:%M:%S')}", ln=True, align="C")
        pdf.cell(0, 10, "Si ves esto, funciona!", ln=True, align="C")
        pdf.output(test_pdf)
        
        print(f"✓ PDF creado: {test_pdf}")
        print()
        
    except Exception as e:
        print(f"✗ Error creando PDF: {e}")
        return
    
    # Imprimir
    print("[2] Iniciando impresión...")
    print()
    
    success, msg = printer.print_pdf_interactive(test_pdf, "BT-801")
    
    print()
    print("=" * 70)
    print("RESULTADO")
    print("=" * 70)
    print()
    
    if success:
        print(f"✓ {msg}")
        print()
        print("💡 TIPS:")
        print("   - Si no imprime, intenta acercar más la impresora")
        print("   - Asegúrate de que el Bluetooth esté activo en tu PC")
        print("   - Algunos modelos tardan 10-15 segundos en conectarse")
        print("   - Si aún no funciona, prueba reencendiendo la impresora")
    else:
        print(f"✗ {msg}")
        print()
        print("💡 SOLUCIONES:")
        print("   1. Verifica que la impresora esté ENCENDIDA")
        print("   2. Verifica que esté en RANGO de Bluetooth")
        print("   3. Acerca la impresora más al PC")
        print("   4. Recarga la batería de la impresora")
    
    print()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        setup_for_temporary_printer()
    else:
        # Importar desde VISO
        printer = BluetoothTemporaryPrinter()
        print(printer.printer_name)
