#!/usr/bin/env python3
"""
Script para detectar el nombre EXACTO de la impresora en Windows
"""

import sys
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def get_all_printers():
    """Obtiene TODAS las impresoras del sistema."""
    logger.info("\n" + "=" * 70)
    logger.info("BUSCANDO TODAS LAS IMPRESORAS DEL SISTEMA")
    logger.info("=" * 70 + "\n")
    
    printers = []
    
    # Método 1: Usando win32print
    try:
        import win32print
        logger.info("[MÉTODO 1] Usando win32print...")
        
        # Intentar diferentes enumeraciones
        flags_list = [
            ("PRINTER_ENUM_LOCAL", win32print.PRINTER_ENUM_LOCAL),
            ("PRINTER_ENUM_CONNECTIONS", win32print.PRINTER_ENUM_CONNECTIONS),
            ("PRINTER_ENUM_NETWORK", win32print.PRINTER_ENUM_NETWORK),
            ("PRINTER_ENUM_SHARED", win32print.PRINTER_ENUM_SHARED),
        ]
        
        for flag_name, flag_value in flags_list:
            try:
                result = win32print.EnumPrinters(flag_value)
                if result:
                    logger.info(f"  ✓ {flag_name}:")
                    for item in result:
                        # EnumPrinters devuelve tuplas
                        if isinstance(item, tuple) and len(item) > 0:
                            printer_name = item[0] if isinstance(item[0], str) else str(item[0])
                            if printer_name and printer_name not in printers:
                                printers.append(printer_name)
                                logger.info(f"    - {printer_name}")
            except Exception as e:
                logger.warning(f"  ✗ {flag_name}: {e}")
    
    except ImportError:
        logger.error("win32print no disponible")
    
    # Método 2: Usando registro de Windows
    try:
        logger.info("\n[MÉTODO 2] Usando registro de Windows...")
        import winreg
        
        try:
            reg_path = r"SYSTEM\CurrentControlSet\Control\Print\Printers"
            registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
            
            i = 0
            while True:
                try:
                    printer_name = winreg.EnumKey(registry_key, i)
                    if printer_name not in printers:
                        printers.append(printer_name)
                        logger.info(f"  ✓ {printer_name}")
                    i += 1
                except OSError:
                    break
            
            winreg.CloseKey(registry_key)
        except Exception as e:
            logger.warning(f"  Error accediendo registro: {e}")
    
    except ImportError:
        logger.error("winreg no disponible")
    
    # Método 3: Usando comandos PowerShell
    try:
        logger.info("\n[MÉTODO 3] Usando PowerShell...")
        import subprocess
        
        ps_command = "Get-Printer | Select-Object Name"
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command', ps_command],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines[3:]:  # Saltamos encabezados
                line = line.strip()
                if line and line not in printers and not line.startswith('-'):
                    printers.append(line)
                    logger.info(f"  ✓ {line}")
    
    except Exception as e:
        logger.warning(f"  PowerShell error: {e}")
    
    # Eliminar duplicados pero mantener orden
    unique_printers = []
    seen = set()
    for p in printers:
        if p and p not in seen:
            unique_printers.append(p)
            seen.add(p)
    
    return unique_printers

def test_printer(printer_name):
    """Prueba si la impresora funciona."""
    logger.info(f"\n[TEST] Probando impresora: {printer_name}")
    
    try:
        import win32print
        
        hprinter = win32print.OpenPrinter(printer_name)
        win32print.ClosePrinter(hprinter)
        logger.info(f"  ✓ Impresora accesible")
        return True
    except Exception as e:
        logger.error(f"  ✗ Error: {e}")
        return False

def main():
    logger.info("\n")
    logger.info("╔" + "=" * 68 + "╗")
    logger.info("║" + "  DETECTOR DE IMPRESORAS WINDOWS".center(68) + "║")
    logger.info("╚" + "=" * 68 + "╝")
    
    # Obtener todas las impresoras
    printers = get_all_printers()
    
    if not printers:
        logger.error("\n❌ No se encontraron impresoras")
        logger.info("\nSolución:")
        logger.info("1. Verifica que la EPSON L4260 esté conectada por USB")
        logger.info("2. Verifica que el driver esté instalado")
        logger.info("3. Ve a Configuración > Dispositivos > Impresoras y escáneres")
        logger.info("4. Anota exactamente el nombre que aparece ahí")
        return False
    
    logger.info("\n" + "=" * 70)
    logger.info(f"TOTAL: {len(printers)} impresora(s) encontrada(s)")
    logger.info("=" * 70)
    
    # Buscar EPSON
    epson_printers = [p for p in printers if 'EPSON' in p.upper() or 'L4260' in p.upper()]
    
    if epson_printers:
        logger.info("\n✓ IMPRESORAS EPSON ENCONTRADAS:")
        for i, p in enumerate(epson_printers, 1):
            logger.info(f"  {i}. {p}")
            test_printer(p)
        
        logger.info("\n" + "=" * 70)
        logger.info("USA UNO DE ESTOS NOMBRES PARA IMPRIMIR:")
        for p in epson_printers:
            logger.info(f"  printer_name = \"{p}\"")
        logger.info("=" * 70)
    else:
        logger.warning("\n⚠ No se encontraron impresoras EPSON")
        logger.info("\nTodas las impresoras disponibles:")
        for i, p in enumerate(printers, 1):
            logger.info(f"  {i}. {p}")
    
    logger.info("\n")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
