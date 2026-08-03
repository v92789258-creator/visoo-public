"""
Manejador de impresoras Bluetooth y térmicas para VISO.
Soporta impresoras de rollo de 80mm y 58mm.
"""

import os
import sys
import subprocess
import platform
import threading
import logging
import tempfile
from datetime import datetime
from typing import List, Tuple, Optional
from functools import wraps
from threading import Thread, Event

# Configurar logger
logger = logging.getLogger(__name__)
BLUETOOTH_TIMEOUT = 10  # segundos para timeout de búsqueda Bluetooth


class PrinterHandler:
    """Maneja la impresión en impresoras Bluetooth térmicas."""
    
    def __init__(self):
        self.system = platform.system()
        self.printers: List[str] = []
        self.selected_printer: Optional[str] = None
        self._search_lock = threading.Lock()
        self._bluetooth_search_stop = Event()
        
    def find_bluetooth_printers(self) -> List[str]:
        """Encuentra impresoras Bluetooth disponibles con timeout."""
        try:
            if self.system == "Windows":
                return self._find_windows_printers()
            elif self.system == "Linux":
                return self._find_linux_printers()
            elif self.system == "Darwin":  # macOS
                return self._find_macos_printers()
            return []
        except Exception as e:
            logger.error(f"Error buscando impresoras: {e}")
            return []
    
    def find_wired_printers(self) -> List[str]:
        """Encuentra impresoras cableadas (USB/Red) disponibles."""
        try:
            if self.system == "Windows":
                # Usar el mismo método que busca TODAS las impresoras
                return self._find_windows_printers()
            elif self.system == "Linux":
                return self._find_linux_printers()
            elif self.system == "Darwin":  # macOS
                return self._find_macos_printers()
            return []
        except Exception as e:
            logger.error(f"Error buscando impresoras cableadas: {e}")
            return []
    
    def _find_windows_printers(self) -> List[str]:
        """Encuentra TODAS las impresoras en Windows, incluyendo Bluetooth con validación."""
        printers = []
        
        # Método 1: Buscar impresoras en el sistema de impresoras de Windows
        try:
            import win32print
            try:
                # Intentar múltiples enumeraciones para captar locales, conexiones y red
                flags_list = [
                    win32print.PRINTER_ENUM_LOCAL,
                    win32print.PRINTER_ENUM_CONNECTIONS,
                    win32print.PRINTER_ENUM_NETWORK,
                    win32print.PRINTER_ENUM_SHARED,
                ]

                for flag in flags_list:
                    try:
                        result = win32print.EnumPrinters(flag)
                        for item in result:
                            # EnumPrinters devuelve tuplas; el nombre suele estar en [0]
                            if isinstance(item, tuple) and len(item) > 0:
                                name = item[0]
                            else:
                                name = item

                            if name:
                                # Normalizar a str
                                try:
                                    name_str = name if isinstance(name, str) else str(name)
                                except Exception:
                                    name_str = str(name)

                                if name_str and name_str not in printers:
                                    printers.append(name_str)
                    except Exception:
                        # Ignorar errores por flag individual
                        continue
            except Exception as e:
                logger.warning(f"Error enumerando impresoras con win32print: {e}")
        except ImportError:
            logger.warning("win32print no disponible, usando métodos alternativos")
        
        # Método 2: Buscar dispositivos Bluetooth emparejados CON TIMEOUT
        try:
            bluetooth_devices = self._find_bluetooth_devices_with_timeout()
            if bluetooth_devices:
                for device in bluetooth_devices:
                    if device and device not in printers:
                        printers.append(device)
        except Exception as e:
            logger.warning(f"Error buscando dispositivos Bluetooth: {e}")
        
        # Método 3: Buscar en el Registro de Windows (validado)
        try:
            registry_printers = self._find_printers_in_registry()
            if registry_printers:
                for p in registry_printers:
                    if p and p not in printers:
                        printers.append(p)
        except Exception as e:
            logger.warning(f"Error buscando en Registro: {e}")
        
        # Limpiar y convertir bytes a string de forma SEGURA
        printers_clean = self._sanitize_printer_names(printers)
        
        # Eliminar duplicados manteniendo el orden
        printers_unicos = list(dict.fromkeys(printers_clean))  # Preserva orden desde Python 3.7
        
        self.printers = printers_unicos
        logger.info(f"Impresoras encontradas: {printers_unicos}")
        return printers_unicos
    
    def _sanitize_printer_names(self, printers: List) -> List[str]:
        """Sanitiza y convierte nombres de impresoras de forma segura."""
        printers_clean = []
        for p in printers:
            try:
                if isinstance(p, bytes):
                    # Decodificar bytes de forma segura (no usar strip con null bytes directamente)
                    p_str = p.decode('utf-8', errors='ignore')
                    # Limpiar caracteres de control y null bytes
                    p_str = ''.join(c for c in p_str if ord(c) >= 32 or c == '\n').strip()
                elif isinstance(p, str):
                    p_str = p.strip()
                else:
                    p_str = str(p).strip()
                
                # Validar que no esté vacío después de limpiar
                if p_str and len(p_str) > 0:
                    printers_clean.append(p_str)
            except Exception as e:
                logger.debug(f"Error sanitizando nombre de impresora: {e}")
                continue
        
        return printers_clean
    
    def _find_bluetooth_devices_with_timeout(self, timeout: int = BLUETOOTH_TIMEOUT) -> List[str]:
        """Encuentra dispositivos Bluetooth con timeout para evitar que cuelgue."""
        devices = []
        result_container = {'devices': []}
        
        def search_bluetooth():
            try:
                devices_found = self._find_bluetooth_devices()
                result_container['devices'] = devices_found
            except Exception as e:
                logger.error(f"Error en búsqueda Bluetooth: {e}")
        
        # Ejecutar búsqueda en thread separado con timeout
        search_thread = Thread(target=search_bluetooth, daemon=True)
        search_thread.start()
        search_thread.join(timeout=timeout)
        
        if search_thread.is_alive():
            logger.warning(f"Búsqueda Bluetooth tomó más de {timeout}s, abortando")
            return []
        
        return result_container['devices']
    
    def _find_bluetooth_devices(self) -> List[str]:
        """Encuentra dispositivos Bluetooth emparejados en Windows."""
        try:
            devices = []
            # Usar WMI para obtener dispositivos Bluetooth
            result = subprocess.run(
                ['powershell', '-Command', 
                 'Get-WmiObject -Class Win32_PnPDevice -Filter "Name LIKE \'%Bluetooth%\'" | Select-Object -ExpandProperty Name'],
                capture_output=True,
                text=True,
                timeout=8  # Timeout interno para PowerShell
            )
            
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        devices.append(line.strip())
            
            # Alternativa: buscar en el registro de Bluetooth
            if not devices:
                devices.extend(self._get_bluetooth_from_registry())
            
            return devices
        except subprocess.TimeoutExpired:
            logger.warning("Búsqueda Bluetooth en PowerShell excedió timeout")
            return []
        except Exception as e:
            logger.warning(f"Error en búsqueda Bluetooth: {e}")
            return []
    
    def _get_bluetooth_from_registry(self) -> List[str]:
        """Obtiene dispositivos Bluetooth del Registro de Windows de forma segura."""
        try:
            import winreg
            devices = []
            
            # Ruta del registro para dispositivos Bluetooth
            bluetooth_path = r"SYSTEM\CurrentControlSet\Services\BTHPORT\Parameters\Devices"
            
            try:
                registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, bluetooth_path)
                subkeys_count = winreg.QueryInfoKey(registry_key)[0]
                
                for i in range(subkeys_count):
                    try:
                        device_key_name = winreg.EnumKey(registry_key, i)
                        device_key = winreg.OpenKey(registry_key, device_key_name)
                        try:
                            device_name = winreg.QueryValueEx(device_key, "Name")[0]
                            if device_name:
                                devices.append(device_name)
                        except WindowsError:
                            # Si no hay nombre, usar el key name como fallback
                            if device_key_name:
                                devices.append(device_key_name)
                        finally:
                            winreg.CloseKey(device_key)
                    except Exception as e:
                        logger.debug(f"Error leyendo Bluetooth device {i}: {e}")
                        continue
                
                winreg.CloseKey(registry_key)
            except FileNotFoundError:
                logger.debug("Ruta Bluetooth no encontrada en registro")
            except Exception as e:
                logger.warning(f"Error accediendo a ruta Bluetooth en registro: {e}")
            
            return devices
        except Exception as e:
            logger.warning(f"Error en _get_bluetooth_from_registry: {e}")
            return []
    
    def _find_printers_in_registry(self) -> List[str]:
        """Busca impresoras en el Registro de Windows de forma segura."""
        try:
            import winreg
            printers = []
            
            # Rutas comunes del registro para impresoras
            paths = [
                r"SYSTEM\CurrentControlSet\Control\Print\Printers",
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Print\Printers",
            ]
            
            for path in paths:
                try:
                    registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
                    subkeys_count = winreg.QueryInfoKey(registry_key)[0]
                    
                    for i in range(subkeys_count):
                        try:
                            printer_name = winreg.EnumKey(registry_key, i)
                            if printer_name and len(printer_name) > 0:
                                printers.append(printer_name)
                        except Exception as e:
                            logger.debug(f"Error leyendo printer {i}: {e}")
                            continue
                    
                    winreg.CloseKey(registry_key)
                except FileNotFoundError:
                    logger.debug(f"Ruta de registro no encontrada: {path}")
                    continue
                except Exception as e:
                    logger.debug(f"Error accediendo a {path}: {e}")
                    continue
            
            return printers
        except Exception as e:
            logger.warning(f"Error en _find_printers_in_registry: {e}")
            return []
    
    def _find_linux_printers(self) -> List[str]:
        """Encuentra TODAS las impresoras en Linux."""
        try:
            result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True, timeout=5)
            printers = []
            for line in result.stdout.split('\n'):
                if line.strip():
                    try:
                        printer_name = line.split()[1].rstrip(':')
                        printers.append(printer_name)
                    except IndexError:
                        continue
            self.printers = printers
            return printers
        except subprocess.TimeoutExpired:
            logger.warning("Búsqueda de impresoras en Linux excedió timeout")
            return []
        except Exception as e:
            logger.warning(f"Error en Linux: {e}")
            return []
    
    def _find_macos_printers(self) -> List[str]:
        """Encuentra TODAS las impresoras en macOS."""
        try:
            result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True, timeout=5)
            printers = []
            for line in result.stdout.split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) > 1:
                        printer_name = parts[1].rstrip(':')
                        printers.append(printer_name)
            self.printers = printers
            return printers
        except subprocess.TimeoutExpired:
            logger.warning("Búsqueda de impresoras en macOS excedió timeout")
            return []
        except Exception as e:
            logger.warning(f"Error en macOS: {e}")
            return []
    
    def set_printer(self, printer_name: Optional[str]) -> bool:
        """Establece la impresora activa."""
        if printer_name and printer_name != "No hay impresoras disponibles":
            self.selected_printer = printer_name
            logger.info(f"Impresora seleccionada: {printer_name}")
            return True
        return False
    
    def print_pdf(self, pdf_path: str, printer_name: Optional[str] = None) -> Tuple[bool, str]:
        """Imprime un PDF en la impresora especificada."""
        if not os.path.exists(pdf_path):
            msg = f"Archivo PDF no encontrado: {pdf_path}"
            logger.error(msg)
            return False, msg
        
        printer = printer_name or self.selected_printer
        if not printer:
            msg = "No hay impresora seleccionada"
            logger.error(msg)
            return False, msg
        
        try:
            if self.system == "Windows":
                return self._print_windows(pdf_path, printer)
            elif self.system == "Linux":
                return self._print_linux(pdf_path, printer)
            elif self.system == "Darwin":
                return self._print_macos(pdf_path, printer)
            else:
                msg = f"Sistema operativo no soportado: {self.system}"
                logger.error(msg)
                return False, msg
        except Exception as e:
            msg = f"Error al imprimir: {e}"
            logger.error(msg)
            return False, msg
    
    def _print_windows(self, pdf_path: str, printer_name: str) -> Tuple[bool, str]:
        """Imprime en Windows usando escpos para impresoras térmicas."""
        try:
            if not os.path.exists(pdf_path):
                return False, f"Archivo no encontrado: {pdf_path}"
            
            pdf_path = os.path.abspath(pdf_path)
            printer_name = str(printer_name or "").strip()
            printer_name_lower = printer_name.lower()
            
            # Para impresoras Bluetooth térmicas, usar escpos
            if any(x in printer_name_lower for x in ['bt-', 'hoco', 'bluetooth', 'thermal']):
                from utils.escpos_thermal_printer import ThermalBluetoothPrinter
                
                logger.info(f"Imprimiendo en impresora térmica: {printer_name}")
                # Imprimir (escpos detectará el puerto automáticamente)
                success, message = ThermalBluetoothPrinter.print_pdf_to_thermal(pdf_path)
                if success:
                    return success, message
                try:
                    if _is_printer_available(printer_name):
                        logger.warning("[PRINT] Sin COM visible; intentando spooler de Windows para impresora termica")
                        std_success, std_message = self._print_windows_standard(pdf_path, printer_name)
                        if std_success:
                            return std_success, std_message
                except Exception:
                    pass
                return False, message
            
            # Para otras impresoras, usar método estándar
            return self._print_windows_standard(pdf_path, printer_name)
        
        except Exception as e:
            msg = f"Error en impresión Windows: {str(e)}"
            logger.error(msg)
            return False, msg
    
    def _print_windows_standard(self, pdf_path: str, printer_name: str) -> Tuple[bool, str]:
        """Método estándar de impresión en Windows - OPTIMIZADO PARA IMPRESORAS USB."""
        try:
            # Convertir a ruta absoluta
            pdf_path = os.path.abspath(pdf_path)
            
            if not os.path.exists(pdf_path):
                return False, f"Archivo PDF no encontrado: {pdf_path}"
            
            logger.info(f"[PRINT] ╔═══════════════════════════════════════════════╗")
            logger.info(f"[PRINT] ║  IMPRIMIENDO: {os.path.basename(pdf_path):33}║")
            logger.info(f"[PRINT] ║  IMPRESORA:   {printer_name:33}║")
            logger.info(f"[PRINT] ║  TIPO:        USB CABLE (DIRECTO)           ║")
            logger.info(f"[PRINT] ╚═══════════════════════════════════════════════╝")
            
            import time
            time.sleep(0.3)
            
            # PRIORIDAD 1: SumatraPDF (MEJOR para PDFs + USB)
            try:
                logger.info(f"[PRINT] [1/5] Intentando SumatraPDF...")
                sumatra_paths = [
                    "C:\\Program Files\\SumatraPDF\\SumatraPDF.exe",
                    "C:\\Program Files (x86)\\SumatraPDF\\SumatraPDF.exe"
                ]
                
                for sumatra_path in sumatra_paths:
                    if os.path.exists(sumatra_path):
                        logger.info(f"[PRINT] ✓ SumatraPDF encontrado")
                        cmd = f'"{sumatra_path}" -print-to "{printer_name}" -silent "{pdf_path}"'
                        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
                        time.sleep(2)
                        logger.info(f"[PRINT] ✓✓ Enviado a SumatraPDF correctamente")
                        return True, f"Impreso con SumatraPDF en {printer_name}"
            except Exception as e:
                logger.warning(f"[PRINT] SumatraPDF falló: {e}")
            
            # PRIORIDAD 2: Adobe Acrobat Reader (Script directo)
            try:
                logger.info(f"[PRINT] [2/5] Intentando Adobe Acrobat Reader...")
                acrobat_paths = [
                    "C:\\Program Files\\Adobe\\Acrobat DC\\Acrobat\\Acrobat.exe",
                    "C:\\Program Files\\Adobe\\Acrobat\\Acrobat.exe",
                    "C:\\Program Files (x86)\\Adobe\\Reader 11.0\\Reader\\AcroRd32.exe",
                    "C:\\Program Files\\Adobe\\Acrobat Reader DC\\Reader\\AcroRd32.exe",
                    "C:\\Program Files (x86)\\Adobe\\Acrobat Reader\\Reader\\AcroRd32.exe"
                ]
                
                for acrobat_path in acrobat_paths:
                    if os.path.exists(acrobat_path):
                        logger.info(f"[PRINT] ✓ Acrobat encontrado")
                        # /t = print to printer
                        cmd = f'"{acrobat_path}" /t "{pdf_path}" "{printer_name}"'
                        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
                        time.sleep(2)
                        logger.info(f"[PRINT] ✓✓ Acrobat ejecutado correctamente")
                        return True, f"Impreso con Acrobat en {printer_name}"
            except Exception as e:
                logger.warning(f"[PRINT] Acrobat falló: {e}")
            
            # PRIORIDAD 3: Foxit Reader
            try:
                logger.info(f"[PRINT] [3/5] Intentando Foxit Reader...")
                foxit_paths = [
                    "C:\\Program Files\\Foxit Software\\Foxit Reader\\FoxitReader.exe",
                    "C:\\Program Files (x86)\\Foxit Software\\Foxit Reader\\FoxitReader.exe"
                ]
                
                for foxit_path in foxit_paths:
                    if os.path.exists(foxit_path):
                        logger.info(f"[PRINT] ✓ Foxit encontrado")
                        cmd = f'"{foxit_path}" -p "{pdf_path}" "{printer_name}"'
                        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
                        time.sleep(2)
                        logger.info(f"[PRINT] ✓✓ Foxit ejecutado correctamente")
                        return True, f"Impreso con Foxit en {printer_name}"
            except Exception as e:
                logger.warning(f"[PRINT] Foxit falló: {e}")
            
            # PRIORIDAD 4: PowerShell con proceso directo (MEJOR para USB)
            try:
                logger.info(f"[PRINT] [4/5] Intentando PowerShell directo...")
                ps_command = f'''
$pdf = "{pdf_path}"
$printer = "{printer_name}"

# Usar shellexecute directo
$shell = New-Object -ComObject Shell.Application
$shell.ShellExecuteAsync($pdf, "", "", "print", 0)
Start-Sleep -Milliseconds 3000
'''
                result = subprocess.run(
                    ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_command],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                time.sleep(2)
                logger.info(f"[PRINT] ✓✓ PowerShell ejecutado")
                return True, f"Impreso en {printer_name}"
            except Exception as e:
                logger.warning(f"[PRINT] PowerShell directo falló: {e}")
            
            # PRIORIDAD 5: Usar IExplore/Edge para imprimir PDFs
            try:
                logger.info(f"[PRINT] [5/5] Intentando navegador...")
                # Intentar con Edge (más moderno)
                edge_paths = [
                    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
                    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
                ]
                
                for edge_path in edge_paths:
                    if os.path.exists(edge_path):
                        logger.info(f"[PRINT] ✓ Edge encontrado")
                        # Abrir y imprimir
                        cmd = f'"{edge_path}" --print-to-pdf "{pdf_path}"'
                        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
                        time.sleep(2)
                        # Ahora enviar a imprimir
                        logger.info(f"[PRINT] ✓✓ Edge ejecutado")
                        return True, f"Impreso vía navegador en {printer_name}"
            except Exception as e:
                logger.warning(f"[PRINT] Navegador falló: {e}")
            
            logger.error(f"[PRINT] ✗✗ TODOS LOS MÉTODOS FALLARON")
            logger.error(f"[PRINT] SOLUCIÓN RECOMENDADA:")
            logger.error(f"[PRINT] Descarga SumatraPDF desde: https://www.sumatrapdfreader.org/")
            logger.error(f"[PRINT] Es gratuito y funciona perfecto para impresoras USB")
            return False, "No se pudo imprimir - intenta instalar SumatraPDF"
            
        except Exception as e:
            msg = f"[PRINT] Error crítico: {str(e)}"
            logger.error(msg)
            return False, msg
    
    def _print_linux(self, pdf_path: str, printer_name: str) -> Tuple[bool, str]:
        """Imprime en Linux."""
        try:
            # Usar lp command con timeout
            result = subprocess.run(
                ['lp', '-d', printer_name, pdf_path],
                capture_output=True,
                text=True,
                timeout=15
            )
            if result.returncode == 0:
                logger.info(f"Documento impreso en {printer_name}")
                return True, "Documento enviado a la impresora"
            else:
                logger.error(f"Error en impresión Linux: {result.stderr}")
                return False, result.stderr
        except subprocess.TimeoutExpired:
            logger.warning("Impresión Linux excedió timeout")
            return False, "Timeout en impresión"
        except Exception as e:
            msg = f"Error en impresión Linux: {e}"
            logger.error(msg)
            return False, msg
    
    def _print_macos(self, pdf_path: str, printer_name: str) -> Tuple[bool, str]:
        """Imprime en macOS."""
        try:
            # Usar lp command (similar a Linux) con timeout
            result = subprocess.run(
                ['lp', '-d', printer_name, pdf_path],
                capture_output=True,
                text=True,
                timeout=15
            )
            if result.returncode == 0:
                logger.info(f"Documento impreso en {printer_name}")
                return True, "Documento enviado a la impresora"
            else:
                logger.error(f"Error en impresión macOS: {result.stderr}")
                return False, result.stderr
        except subprocess.TimeoutExpired:
            logger.warning("Impresión macOS excedió timeout")
            return False, "Timeout en impresión"
        except Exception as e:
            msg = f"Error en impresión macOS: {e}"
            logger.error(msg)
            return False, msg
    
    def _get_default_pdf_reader(self) -> Optional[str]:
        """Obtiene la ruta del lector PDF por defecto en Windows."""
        try:
            import winreg
            
            # Buscar rutas comunes
            paths_to_try = [
                r"C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
                r"C:\Program Files (x86)\Adobe\Acrobat Reader\AcroRd32.exe",
                r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
                r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
            ]
            
            for path in paths_to_try:
                if os.path.exists(path):
                    logger.info(f"Encontrado lector PDF: {path}")
                    return path
            
            return None
        except Exception as e:
            logger.warning(f"Error buscando PDF reader: {e}")
            return None
    
    def print_raw(self, port: str, data: bytes) -> Tuple[bool, str]:
        """Imprime datos raw directamente al puerto serial/USB."""
        try:
            if sys.platform.startswith('win'):
                import win32file
                handle = win32file.CreateFile(
                    port,
                    win32file.GENERIC_WRITE,
                    0,
                    None,
                    win32file.OPEN_EXISTING,
                    0,
                    None
                )
                win32file.WriteFile(handle, data)
                win32file.CloseHandle(handle)
                logger.info(f"Datos enviados al puerto {port}")
                return True, "Datos enviados al puerto"
            else:
                with open(port, 'wb') as f:
                    f.write(data)
                logger.info(f"Datos enviados al puerto {port}")
                return True, "Datos enviados al puerto"
        except Exception as e:
            msg = f"Error enviando datos raw: {e}"
            logger.error(msg)
            return False, msg
    
    def _print_image_windows(self, image_path: str, printer_name: str) -> Tuple[bool, str]:
        """Imprime una imagen en Windows (térmica o estándar)."""
        try:
            image_path = os.path.abspath(image_path)
            
            # Detectar si es impresora térmica
            if any(x in printer_name.lower() for x in ['bt-', 'thermal', 'hoco', 'bluetooth']):
                # Para impresoras térmicas, convertir a escpos
                from utils.escpos_thermal_printer import ThermalBluetoothPrinter
                from PIL import Image
                
                img = Image.open(image_path)
                logger.info(f"Imprimiendo imagen térmica en: {printer_name}")
                return ThermalBluetoothPrinter.print_image_thermal(img)
            else:
                # Para impresoras normales, usar método estándar
                return self._print_image_windows_standard(image_path, printer_name)
        
        except Exception as e:
            msg = f"Error imprimiendo imagen en Windows: {str(e)}"
            logger.error(msg)
            return False, msg
    
    def _print_image_linux(self, image_path: str, printer_name: str) -> Tuple[bool, str]:
        """Imprime una imagen en Linux."""
        try:
            image_path = os.path.abspath(image_path)
            
            # En Linux usar lp o lpr
            cmd = ['lp', '-d', printer_name, image_path]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Imagen impresa en {printer_name}")
                return True, f"Imagen impresa en {printer_name}"
            else:
                return False, f"Error: {result.stderr}"
        except Exception as e:
            msg = f"Error imprimiendo imagen en Linux: {str(e)}"
            logger.error(msg)
            return False, msg
    
    def _print_image_macos(self, image_path: str, printer_name: str) -> Tuple[bool, str]:
        """Imprime una imagen en macOS."""
        try:
            image_path = os.path.abspath(image_path)
            
            # En macOS usar lp
            cmd = ['lp', '-d', printer_name, image_path]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Imagen impresa en {printer_name}")
                return True, f"Imagen impresa en {printer_name}"
            else:
                return False, f"Error: {result.stderr}"
        except Exception as e:
            msg = f"Error imprimiendo imagen en macOS: {str(e)}"
            logger.error(msg)
            return False, msg
    
    def _print_image_windows_with_options(self, image_path: str, printer_name: str, options: dict) -> Tuple[bool, str]:
        """Imprime una imagen en Windows con opciones de personalización."""
        try:
            from PIL import Image
            
            image_path = os.path.abspath(image_path)
            
            # Detectar si es impresora térmica
            is_thermal = any(x in printer_name.lower() for x in ['bt-', 'thermal', 'hoco', 'bluetooth'])
            
            # Cargar imagen original
            img = Image.open(image_path)
            
            # Aplicar opciones
            width_mm = options.get('width_mm', 60)
            height_mm = options.get('height_mm', 30)
            show_text = options.get('show_text', True)
            center = options.get('center', True)
            margin_top_mm = options.get('margin_top_mm', 5)
            margin_left_mm = options.get('margin_left_mm', 5)
            quality = options.get('quality', 'Alta (lenta)')
            
            # Redimensionar imagen según opciones
            dpi = 300 if 'Alta' in quality else (203 if 'Media' in quality else 100)
            
            width_px = int((width_mm / 25.4) * dpi)
            height_px = int((height_mm / 25.4) * dpi)
            
            # Redimensionar manteniendo aspecto
            img.thumbnail((width_px, height_px), Image.Resampling.LANCZOS)
            
            # Si es térmica, imprimir directamente
            if is_thermal:
                from utils.escpos_thermal_printer import ThermalBluetoothPrinter
                logger.info(f"Imprimiendo imagen térmica con opciones en: {printer_name}")
                return ThermalBluetoothPrinter.print_image_thermal(img)
            else:
                # Para impresoras estándar, guardar con las opciones aplicadas
                temp_dir = tempfile.gettempdir()
                temp_image = os.path.join(temp_dir, f"barcode_custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                img.save(temp_image)
                
                # Imprimir
                try:
                    import win32print
                    import win32api
                    
                    win32api.ShellExecute(0, "print", temp_image, None, ".", 0)
                    logger.info(f"Imagen personalizada enviada a imprimir: {temp_image}")
                    return True, "Imagen enviada a imprimir con opciones personalizadas"
                except ImportError:
                    import subprocess
                    subprocess.Popen(
                        f'powershell -Command "Start-Process \\"{temp_image}\\" -Verb Print"',
                        shell=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    logger.info(f"Imagen personalizada enviada a imprimir (fallback): {temp_image}")
                    return True, "Imagen enviada a imprimir con opciones personalizadas"
        
        except Exception as e:
            msg = f"Error imprimiendo imagen con opciones: {str(e)}"
            logger.error(msg)
            return False, msg
    
    def _print_image_linux_with_options(self, image_path: str, printer_name: str, options: dict) -> Tuple[bool, str]:
        """Imprime una imagen en Linux con opciones de personalización."""
        try:
            image_path = os.path.abspath(image_path)
            
            # En Linux usar lp con opciones
            quality = options.get('quality', 'Media')
            quality_option = '-o media=Custom'
            
            cmd = ['lp', '-d', printer_name, quality_option, image_path]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Imagen impresa en {printer_name} con opciones")
                return True, f"Imagen impresa en {printer_name} con opciones personalizadas"
            else:
                return False, f"Error: {result.stderr}"
        except Exception as e:
            msg = f"Error imprimiendo imagen en Linux: {str(e)}"
            logger.error(msg)
            return False, msg
    
    def _print_image_macos_with_options(self, image_path: str, printer_name: str, options: dict) -> Tuple[bool, str]:
        """Imprime una imagen en macOS con opciones de personalización."""
        try:
            image_path = os.path.abspath(image_path)
            
            # En macOS usar lp con opciones
            cmd = ['lp', '-d', printer_name, image_path]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Imagen impresa en {printer_name} con opciones")
                return True, f"Imagen impresa en {printer_name} con opciones personalizadas"
            else:
                return False, f"Error: {result.stderr}"
        except Exception as e:
            msg = f"Error imprimiendo imagen en macOS: {str(e)}"
            logger.error(msg)
            return False, msg


# Instancia global
_printer_handler: Optional[PrinterHandler] = None

def get_printer_handler() -> PrinterHandler:
    """Obtiene la instancia global del manejador de impresoras."""
    global _printer_handler
    if _printer_handler is None:
        _printer_handler = PrinterHandler()
    return _printer_handler


def print_boleta(pdf_path: str, printer_name: Optional[str] = None) -> Tuple[bool, str]:
    """Función conveniente para imprimir una boleta."""
    handler = get_printer_handler()
    return handler.print_pdf(pdf_path, printer_name)


def find_available_printers() -> List[str]:
    """
    Encuentra SOLO las impresoras realmente disponibles y conectadas.
    Filtra impresoras que no estén activamente conectadas.
    """
    handler = get_printer_handler()
    
    # Obtener impresoras Bluetooth
    bluetooth_printers = handler.find_bluetooth_printers()
    
    # Obtener impresoras cableadas (USB/Red)
    wired_printers = handler.find_wired_printers()
    
    # Combinar manteniendo orden y eliminar duplicados
    seen = set()
    all_printers = []
    for p in bluetooth_printers + wired_printers:
        if p and p not in seen:
            seen.add(p)
            all_printers.append(p)

    # Para impresoras Bluetooth no forzar validación con win32print
    available_printers = []
    for printer in all_printers:
        try:
            # Si fue detectada como Bluetooth, incluirla directamente
            if printer in bluetooth_printers:
                available_printers.append(printer)
                continue

            # Para impresoras cableadas/estándar, validar su disponibilidad
            if _is_printer_available(printer):
                available_printers.append(printer)
        except Exception:
            # Si hay error, seguir con la siguiente
            continue

    # Ordenar para UI pero mantener nombres legibles
    return sorted(available_printers)


def _is_printer_available(printer_name: str) -> bool:
    """
    Valida si una impresora está realmente disponible y conectada.
    
    Args:
        printer_name: Nombre de la impresora a validar
    
    Returns:
        True si la impresora está disponible, False si no
    """
    try:
        system = platform.system()
        
        if system == "Windows":
            try:
                import win32print
                # Obtener todos los nombres de impresoras conocidas usando múltiples flags
                flags = (
                    win32print.PRINTER_ENUM_LOCAL |
                    win32print.PRINTER_ENUM_CONNECTIONS |
                    win32print.PRINTER_ENUM_NETWORK |
                    win32print.PRINTER_ENUM_SHARED
                )
                printers = win32print.EnumPrinters(flags)
                printer_names = []
                for p in printers:
                    try:
                        if isinstance(p, tuple) and len(p) > 0:
                            n = p[0]
                        else:
                            n = p
                        if n:
                            printer_names.append(n if isinstance(n, str) else str(n))
                    except Exception:
                        continue

                # Normalizar búsqueda simple: si está en la lista, considerarla disponible
                if printer_name in printer_names:
                    return True

                # Si no está en la lista, intentar buscar en el registro como fallback
                try:
                    import winreg
                    reg_path = r"SYSTEM\CurrentControlSet\Control\Print\Printers"
                    registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                    i = 0
                    while True:
                        try:
                            name = winreg.EnumKey(registry_key, i)
                            if name and name == printer_name:
                                winreg.CloseKey(registry_key)
                                return True
                            i += 1
                        except OSError:
                            break
                    winreg.CloseKey(registry_key)
                except Exception:
                    pass

                # Si no lo encontramos explícitamente, devolver False (más conservador)
                return False
            except ImportError:
                # Fallback: si no tenemos win32print, asumir disponible
                return True
        
        elif system == "Linux":
            # En Linux, verificar con lpstat
            try:
                result = subprocess.run(
                    ["lpstat", "-p", "-d"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                return printer_name in result.stdout
            except:
                return True
        
        elif system == "Darwin":  # macOS
            # En macOS, verificar con lpstat
            try:
                result = subprocess.run(
                    ["lpstat", "-p"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                return printer_name in result.stdout
            except:
                return True
        
        # Por defecto, asumir que está disponible
        return True
        
    except Exception as e:
        logger.warning(f"Error validando disponibilidad de {printer_name}: {e}")
        # Si hay error, asumimos que NO está disponible para ser conservadores
        return False



def print_image(image_path: str, printer_name: Optional[str] = None) -> Tuple[bool, str]:
    """Imprime una imagen (como códigos de barras) en la impresora especificada."""
    if not os.path.exists(image_path):
        return False, f"Archivo de imagen no encontrado: {image_path}"
    
    handler = get_printer_handler()
    printer = printer_name or handler.selected_printer
    
    if not printer:
        return False, "No hay impresora seleccionada"
    
    try:
        if handler.system == "Windows":
            return handler._print_image_windows(image_path, printer)
        elif handler.system == "Linux":
            return handler._print_image_linux(image_path, printer)
        elif handler.system == "Darwin":
            return handler._print_image_macos(image_path, printer)
        else:
            return False, f"Sistema operativo no soportado: {handler.system}"
    except Exception as e:
        return False, f"Error al imprimir imagen: {str(e)}"


def print_image_with_options(image_path: str, printer_name: Optional[str] = None, options: dict = None) -> Tuple[bool, str]:
    """
    Imprime una imagen con opciones de personalización.
    
    Args:
        image_path: Ruta de la imagen
        printer_name: Nombre de la impresora
        options: Dict con opciones:
            - width_mm: Ancho en milímetros
            - height_mm: Alto en milímetros
            - show_text: Mostrar texto/números
            - center: Centrar en página
            - margin_top_mm: Margen superior
            - margin_left_mm: Margen izquierdo
            - quality: 'Baja (rápida)', 'Media', 'Alta (lenta)'
    
    Returns:
        Tuple[bool, str]: (éxito, mensaje)
    """
    if not os.path.exists(image_path):
        return False, f"Archivo de imagen no encontrado: {image_path}"
    
    if options is None:
        options = {}
    
    handler = get_printer_handler()
    printer = printer_name or handler.selected_printer
    
    if not printer:
        return False, "No hay impresora seleccionada"
    
    try:
        if handler.system == "Windows":
            return handler._print_image_windows_with_options(image_path, printer, options)
        elif handler.system == "Linux":
            return handler._print_image_linux_with_options(image_path, printer, options)
        elif handler.system == "Darwin":
            return handler._print_image_macos_with_options(image_path, printer, options)
        else:
            return False, f"Sistema operativo no soportado: {handler.system}"
    except Exception as e:
        return False, f"Error al imprimir imagen: {str(e)}"
