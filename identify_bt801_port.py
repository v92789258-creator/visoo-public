"""
Script para identificar cuál puerto COM tiene la impresora Bluetooth BT-801
"""

import subprocess
import sys

def find_bt801_port():
    """Encuentra el puerto COM de BT-801."""
    print()
    print("=" * 70)
    print("IDENTIFICANDO PUERTO DE BT-801")
    print("=" * 70)
    print()
                                              
    try:
        # Usar PowerShell para obtener información del dispositivo Bluetooth
        ps_command = '''
$devices = Get-CimInstance -ClassName Win32_PnPEntity | Where-Object {$_.Name -like "*BT-801*" -or $_.Name -like "*Bluetooth*Printer*"}
foreach ($device in $devices) {
    Write-Host "Dispositivo: $($device.Name)"
    Write-Host "ID: $($device.PNPDeviceID)"
    Write-Host "---"
}

# Obtener puertos COM vinculados a Bluetooth
Write-Host ""
Write-Host "PUERTOS COM DISPONIBLES:"
$ports = Get-CimInstance -ClassName Win32_SerialPort
foreach ($port in $ports) {
    Write-Host "Puerto: $($port.DeviceID) - $($port.Name)"
}
'''
        
        result = subprocess.run(
            ['powershell', '-Command', ps_command],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print(result.stdout)
        if result.stderr:
            print("Errores:", result.stderr)
        
    except Exception as e:
        print(f"Error: {e}")
    
    print()
    print("=" * 70)
    print("INSTRUCCIONES PARA CONECTAR BT-801:")
    print("=" * 70)
    print()
    print("Si BT-801 no aparece en la lista:")
    print()
    print("1. Enciende la impresora BT-801")
    print("2. Ve a: Configuración > Bluetooth y dispositivos > Dispositivos")
    print("3. Haz clic en 'Agregar dispositivo'")
    print("4. Selecciona 'Bluetooth'")
    print("5. Busca y selecciona 'BT-801'")
    print("6. Completa el emparejamiento")
    print()
    print("Una vez emparejada, debería aparecer como puerto COM en la lista arriba.")
    print()

if __name__ == "__main__":
    find_bt801_port()
