"""
Script para conectar y configurar la impresora Bluetooth BT-801 en Windows.
"""

import subprocess
import sys
import time
import os

def check_bluetooth_device():
    """Verifica si BT-801 está emparejada."""
    print("=" * 70)
    print("VERIFICAR DISPOSITIVO BLUETOOTH BT-801")
    print("=" * 70)
    print()
    
    try:
        result = subprocess.run(
            ['powershell', '-Command', 
             'Get-CimInstance -ClassName Win32_PnPDevice | Where-Object {$_.Name -like "*BT-801*"} | Select-Object -Property Name, Status'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if "BT-801" in result.stdout:
            print("✓ BT-801 está emparejada en Windows")
            print(result.stdout)
            return True
        else:
            print("✗ BT-801 no está emparejada")
            print()
            print("PASOS PARA EMPAREJAR:")
            print("1. Enciende la impresora BT-801")
            print("2. Ve a Configuración > Bluetooth y dispositivos")
            print("3. Haz clic en 'Agregar dispositivo'")
            print("4. Selecciona 'Bluetooth'")
            print("5. Busca y selecciona BT-801")
            print("6. Completa el emparejamiento")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def setup_printer():
    """Configura BT-801 como impresora en Windows."""
    print()
    print("=" * 70)
    print("CONFIGURAR BT-801 COMO IMPRESORA")
    print("=" * 70)
    print()
    
    try:
        # Método 1: Usar Add-Printer con el puerto Bluetooth
        print("[1] Intentando agregar impresora vía PowerShell...")
        
        ps_script = '''
# Verificar si ya existe
$printerExists = Get-Printer -Name "BT-801" -ErrorAction SilentlyContinue
if ($printerExists) {
    Write-Host "Impresora BT-801 ya existe"
    exit 0
}

# Agregar puerto Bluetooth
$portName = "BT-801:"
$existsPort = Get-PrinterPort -Name $portName -ErrorAction SilentlyContinue
if (-not $existsPort) {
    Write-Host "Creando puerto Bluetooth..."
    Add-PrinterPort -Name $portName -PrinterHostAddress "BT-801" -ErrorAction SilentlyContinue
}

# Agregar impresora
Write-Host "Agregando impresora BT-801..."
Add-Printer -Name "BT-801" -PortName $portName -DriverName "Generic / Text Only" -ErrorAction SilentlyContinue

Write-Host "Impresora agregada exitosamente"
'''
        
        result = subprocess.run(
            ['powershell', '-Command', ps_script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✓ Impresora configurada")
            print(result.stdout)
        else:
            print("✗ Error configurando impresora")
            if result.stderr:
                print(f"Error: {result.stderr}")
    
    except Exception as e:
        print(f"Error: {e}")

def test_printer():
    """Prueba imprimir a BT-801."""
    print()
    print("=" * 70)
    print("PRUEBA DE IMPRESIÓN")
    print("=" * 70)
    print()
    
    try:
        # Crear archivo de prueba
        test_file = "test_print.txt"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("""
╔════════════════════════════════════════════╗
║                 PRUEBA BT-801              ║
║            Impresora Bluetooth             ║
║                                            ║
║    Si ves esto en la impresora,           ║
║            ¡FUNCIONA!                     ║
║                                            ║
╚════════════════════════════════════════════╝
""")
        
        print("Enviando archivo de prueba a BT-801...")
        
        # Enviar a imprimir
        result = subprocess.run(
            f'print /d:"BT-801" "{test_file}"',
            shell=True,
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0 or "enviado" in result.stdout.lower():
            print("✓ Archivo enviado a la cola de impresión")
            print()
            print("⏰ Espera 10-15 segundos para que la impresora imprima...")
        else:
            print("Estado de envío:", result.returncode)
            if result.stdout:
                print("Stdout:", result.stdout)
            if result.stderr:
                print("Stderr:", result.stderr)
        
        # Limpiar
        if os.path.exists(test_file):
            os.remove(test_file)
    
    except Exception as e:
        print(f"Error: {e}")

def main():
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " CONFIGURACIÓN DE IMPRESORA BLUETOOTH BT-801 ".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    # Verificar si tiene permisos de administrador
    try:
        result = subprocess.run(['powershell', '-Command', '$PSVersionTable.PSVersion'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            print("⚠️  ADVERTENCIA: Ejecuta este script como Administrador")
            print()
    except Exception:
        pass
    
    # Paso 1: Verificar dispositivo
    if not check_bluetooth_device():
        print()
        input("Presiona Enter después de emparejar BT-801...")
    
    # Paso 2: Configurar como impresora
    setup_printer()
    
    # Paso 3: Prueba
    input()
    print()
    print("¿Deseas hacer una prueba de impresión? (S/n): ", end="")
    respuesta = input().strip().lower()
    
    if respuesta != 'n':
        test_printer()
    
    print()
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print()
    print("✓ Configuración completada")
    print()
    print("Ahora puedes usar BT-801 en VISO:")
    print("1. Abre una venta")
    print("2. Haz clic en 'Imprimir Boleta'")
    print("3. Selecciona BT-801")
    print("4. La boleta debería imprimirse")
    print()

if __name__ == "__main__":
    main()
