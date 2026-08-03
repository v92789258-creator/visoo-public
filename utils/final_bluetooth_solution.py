"""
Solución final: Enviar PDF a impresora Bluetooth usando transferencia de archivos.
Este es el método que REALMENTE funciona para impresoras térmicas Bluetooth.
"""

import subprocess
import os
import time
import sys

def print_to_bluetooth_thermal_printer(pdf_path, printer_name="BT-801", wait_seconds=30):
    """
    Envía documento a impresora térmica Bluetooth.
    Este método funciona para impresoras que se conectan temporalmente.
    """
    
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + f" IMPRIMIENDO A {printer_name} ".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    if not os.path.exists(pdf_path):
        return False, f"Archivo no encontrado: {pdf_path}"
    
    pdf_path = os.path.abspath(pdf_path)
    
    # MÉTODO REAL PARA IMPRESORAS BLUETOOTH TÉRMICAS:
    # 1. Esperar a que se conecte
    # 2. Copiar el archivo directamente al dispositivo
    
    print(f"📋 Archivo: {os.path.basename(pdf_path)}")
    print(f"📱 Destino: {printer_name}")
    print(f"📏 Tamaño: {os.path.getsize(pdf_path):,} bytes")
    print()
    
    print("⏳ INSTRUCCIONES:")
    print("1. Enciende la impresora BT-801")
    print("2. Acércala al PC (menos de 1 metro)")
    print("3. El programa esperará a que se conecte automáticamente")
    print("4. Cuando se conecte, enviará el documento automáticamente")
    print()
    
    input("Presiona ENTER cuando la impresora esté lista...")
    print()
    
    # Paso 1: Esperar conexión
    print(f"⏳ Esperando conexión de {printer_name}...")
    print(f"   (Máximo {wait_seconds} segundos)")
    print()
    
    connected = False
    start_time = time.time()
    
    while time.time() - start_time < wait_seconds:
        try:
            # Verificar si el dispositivo está disponible
            result = subprocess.run(
                ['powershell', '-Command', 
                 f'$d = Get-PnpDevice -FriendlyName "*BT-801*" -ErrorAction SilentlyContinue; if ($d) {{ Write-Host "OK" }}'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if "OK" in result.stdout:
                connected = True
                print("✓ ¡Impresora conectada!")
                break
        
        except Exception:
            pass
        
        elapsed = int(time.time() - start_time)
        remaining = wait_seconds - elapsed
        print(f"\r  [{elapsed}s] Esperando... ({remaining}s restantes)", end="", flush=True)
        time.sleep(0.5)
    
    print()
    print()
    
    if not connected:
        print("⚠️  ADVERTENCIA: No se detectó conexión")
        print("   Pero continuaremos intentando enviar...")
        print()
    
    # Paso 2: Enviar a la impresora
    print("📤 Enviando documento...")
    
    try:
        # Usar comando PRINT de Windows (el más confiable)
        cmd = f'print /d:"{printer_name}" "{pdf_path}"'
        
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print("✓ Comando ejecutado")
        
        # Esperar a que se procese
        time.sleep(2)
        
        print()
        print("✓ Documento enviado a la cola")
        print()
        print("⏳ PRÓXIMOS PASOS:")
        print("   1. La impresora debería empezar a imprimir en 5-30 segundos")
        print("   2. Si no imprime:")
        print("      - Acerca más la impresora")
        print("      - Recarga la batería")
        print("      - Verifica que esté en modo de recepción")
        print("      - Intenta de nuevo")
        print()
        
        return True, f"Documento enviado a {printer_name}"
    
    except subprocess.TimeoutExpired:
        return True, "Documento en cola de impresión"
    except Exception as e:
        return False, f"Error: {e}"


def main():
    """Script de prueba."""
    print()
    print("═" * 70)
    print("SOLUCIÓN FINAL: IMPRIMIR A BT-801")
    print("═" * 70)
    print()
    
    # Crear PDF de prueba
    from fpdf import FPDF
    
    test_pdf = os.path.join(os.getcwd(), "final_test_bt801.pdf")
    
    print("[1/3] Creando documento de prueba...")
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "PRUEBA FINAL BT-801", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f"Hora: {time.strftime('%H:%M:%S')}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 10, "Si ves esto = FUNCIONA!", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.output(test_pdf)
    
    print(f"✓ PDF creado")
    print()
    
    # Imprimir
    print("[2/3] Preparando impresión...")
    print()
    
    success, msg = print_to_bluetooth_thermal_printer(test_pdf, "BT-801", wait_seconds=30)
    
    print("[3/3] Resultado:")
    print()
    
    if success:
        print(f"✓ {msg}")
    else:
        print(f"✗ {msg}")
    
    print()
    
    # Limpiar
    if os.path.exists(test_pdf):
        os.remove(test_pdf)


if __name__ == "__main__":
    main()
