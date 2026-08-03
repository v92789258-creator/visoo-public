"""
Sistema automático de detección de puertos COM para cualquier impresora térmica.
Se ejecuta una sola vez al iniciar VISO y guarda el puerto detectado.
"""

import os
import time
from pathlib import Path
import serial.tools.list_ports


def _get_escpos_serial():
    from escpos.printer import Serial
    return Serial


class AutoDetectPrinter:
    """Auto-detecta automáticamente el puerto COM de cualquier impresora térmica."""
    
    CONFIG_FILE = Path("config_printer_port.txt")

    @staticmethod
    def _sort_com_ports(ports):
        def _port_key(port_name):
            txt = str(port_name or "").strip().upper()
            if txt.startswith("COM"):
                try:
                    return int(txt[3:])
                except Exception:
                    return 9999
            return 9999
        return sorted(set(ports), key=_port_key)
    
    @staticmethod
    def get_all_com_ports():
        """Obtiene todos los puertos COM visibles, incluyendo fallback por registro en Windows."""
        ports = []

        try:
            for port in serial.tools.list_ports.comports():
                device_name = str(getattr(port, "device", "") or "").strip().upper()
                if device_name.startswith("COM"):
                    ports.append(device_name)
        except Exception:
            pass

        # En algunas PCs Bluetooth emparejadas, pyserial no lista bien todos los COM.
        # Usamos el registro de Windows como respaldo.
        if os.name == "nt":
            try:
                import winreg

                registry_key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"HARDWARE\DEVICEMAP\SERIALCOMM",
                )
                index = 0
                while True:
                    try:
                        _name, value, _typ = winreg.EnumValue(registry_key, index)
                        value_txt = str(value or "").strip().upper()
                        if value_txt.startswith("COM"):
                            ports.append(value_txt)
                        index += 1
                    except OSError:
                        break
                winreg.CloseKey(registry_key)
            except Exception:
                pass

        return AutoDetectPrinter._sort_com_ports(ports)
    
    @staticmethod
    def test_port(port, timeout=1):
        """
        Intenta conectar a un puerto COM para verificar si hay impresora.
        Retorna True si encuentra impresora, False si no.
        """
        try:
            Serial = _get_escpos_serial()
            printer = Serial(
                devfile=port,
                baudrate=9600,
                timeout=timeout,
                writeTimeout=timeout
            )
            
            # Si llegó aquí sin excepción = hay impresora
            printer.close()
            return True
            
        except (OSError, serial.SerialException, FileNotFoundError):
            # OSError 22 = Puerto no disponible o sin dispositivo
            # SerialException = No se pudo abrir
            # FileNotFoundError = Puerto no existe
            return False
        except Exception:
            return False
    
    @staticmethod
    def find_printer_port(force_rescan=False):
        """
        Detecta automáticamente en qué puerto COM está la impresora térmica.
        
        Retorna: (puerto_encontrado, fue_guardado_en_config)
        """
        
        # 1. Si ya hay puerto guardado y no se fuerza rescanning, usarlo
        if AutoDetectPrinter.CONFIG_FILE.exists() and not force_rescan:
            saved_port = AutoDetectPrinter.CONFIG_FILE.read_text().strip()
            if saved_port and AutoDetectPrinter.test_port(saved_port, timeout=0.5):
                print(f"✅ Puerto guardado encontrado: {saved_port}")
                return saved_port, False
        
        # 2. Detectar puerto automáticamente
        print("🔍 Detectando puerto de impresora térmica...")
        print("   (Asegúrate de que la impresora está ENCENDIDA)")
        print()
        
        ports = AutoDetectPrinter.get_all_com_ports()
        
        if not ports:
            print("❌ No se encontraron puertos COM disponibles")
            return None, False
        
        print(f"   Escaneando puertos: {', '.join(ports)}")
        print()
        
        # Intentar cada puerto
        for port in ports:
            print(f"   [{port}]", end=" ", flush=True)
            
            if AutoDetectPrinter.test_port(port, timeout=1):
                print("✅ ENCONTRADA")
                print()
                
                # Guardar en config para próxima vez
                AutoDetectPrinter.CONFIG_FILE.write_text(port)
                print(f"✅ Puerto guardado: {port}")
                print(f"   (Se usará automáticamente en próximos inicios)")
                print()
                
                return port, True
            else:
                print("❌", end=" ", flush=True)
                time.sleep(0.3)  # Pausa pequeña entre puertos
        
        print()
        print("❌ No se encontró impresora térmica en ningún puerto COM")
        print()
        print("Soluciones:")
        print("1. Verifica que la impresora está ENCENDIDA")
        print("2. Verifica que está emparejada como Bluetooth (Configuración > Bluetooth)")
        print("3. Intenta desconectar/reconectar la impresora")
        print("4. Reinicia la impresora y la PC")
        print()
        
        return None, False
    
    @staticmethod
    def clear_saved_port():
        """Elimina puerto guardado para forzar rescanning."""
        if AutoDetectPrinter.CONFIG_FILE.exists():
            AutoDetectPrinter.CONFIG_FILE.unlink()
            print(f"✅ Configuración borrada. En próximo inicio se rescaneará.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        print("Forzando rescanning de puerto...")
        AutoDetectPrinter.clear_saved_port()
    
    port, _ = AutoDetectPrinter.find_printer_port()
    
    if port:
        print(f"Puerto final: {port}")
    else:
        print("No se pudo detectar impresora")
        sys.exit(1)
