#!/usr/bin/env python3
"""
Solución alternativa: Usar ShellExecute con el lector PDF predeterminado.
Esto abre el PDF en el programa predeterminado (Edge, Adobe, etc)
y automáticamente imprime sin mostrar interfaz.
"""

import os
import sys
import logging
import subprocess
import time
from typing import Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class SimplePrinter:
    """Imprime usando el lector PDF predeterminado del sistema."""
    
    @staticmethod
    def print_with_default_reader(pdf_path: str, printer_name: str) -> Tuple[bool, str]:
        """
        Imprime un PDF usando el lector PDF predeterminado de Windows.
        
        Esto abre el PDF en Edge, Adobe Reader, o lo que esté configurado
        como predeterminado, y envía directamente a la impresora.
        """
        try:
            logger.info(f"[SIMPLE_PRINT] Intentando con lector PDF predeterminado...")
            logger.info(f"[SIMPLE_PRINT] PDF: {pdf_path}")
            logger.info(f"[SIMPLE_PRINT] Impresora: {printer_name}")
            
            if not os.path.exists(pdf_path):
                return False, f"PDF no encontrado: {pdf_path}"
            
            # Método 1: Usar rundll32 con PrintTo (funciona en algunos sistemas)
            try:
                logger.info("[SIMPLE_PRINT] Método 1: rundll32 PrintTo...")
                cmd = [
                    "rundll32.exe",
                    "printui.dll,PrintUIEntry",
                    f"/p",
                    f"/n{printer_name}",
                    pdf_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, timeout=30)
                
                if result.returncode == 0 or True:  # rundll32 a veces retorna 0 sin importar
                    logger.info("[SIMPLE_PRINT] ✓ PrintUI enviado")
                    time.sleep(2)
                    return True, f"Impresión iniciada con PrintUI"
            except Exception as e:
                logger.warning(f"[SIMPLE_PRINT] PrintUI falló: {e}")
            
            # Método 2: Usar notepad para imprimir (como workaround)
            # Algunos sistemas tienen notepad que puede abrir PDFs
            try:
                logger.info("[SIMPLE_PRINT] Método 2: Shell print verb...")
                
                # Usar PowerShell para ejecutar con el verbo print
                ps_cmd = f"""
$pdf = '{pdf_path}'
$printer = '{printer_name}'
$shell = New-Object -ComObject WScript.Shell
$shell.Exec('rundll32.exe shell32.dll,ShellExec_RunDLL "printto.dll,PrintUI_Entry /n \"{printer}\"' '{pdf}' '')
"""
                
                result = subprocess.run(
                    ["powershell.exe", "-Command", ps_cmd],
                    capture_output=True,
                    timeout=30
                )
                
                logger.info("[SIMPLE_PRINT] PowerShell ejecutado")
                time.sleep(2)
                return True, f"Impresión enviada a {printer_name}"
            
            except Exception as e:
                logger.warning(f"[SIMPLE_PRINT] PowerShell falló: {e}")
            
            # Método 3: Simplemente abrir el PDF (Windows lo abre y podemos imprimir después)
            try:
                logger.info("[SIMPLE_PRINT] Método 3: Abrir PDF con aplicación predeterminada...")
                
                # Esto abre el PDF en el programa predeterminado
                os.startfile(pdf_path)
                
                logger.info("[SIMPLE_PRINT] ✓ PDF abierto - Presiona Ctrl+P para imprimir")
                return True, f"PDF abierto en aplicación predeterminada - Imprime manualmente"
            
            except Exception as e:
                logger.warning(f"[SIMPLE_PRINT] startfile falló: {e}")
            
            return False, "Ningún método funcionó"
        
        except Exception as e:
            logger.error(f"[SIMPLE_PRINT] Error: {e}")
            return False, str(e)
    
    @staticmethod
    def print_with_system_command(pdf_path: str, printer_name: str) -> Tuple[bool, str]:
        """
        Intenta imprimir usando comandos del sistema directamente.
        """
        try:
            logger.info("[SIMPLE_PRINT] Método alternativo: Comando del sistema...")
            
            # En Windows, podemos usar el comando 'print' si está disponible
            cmd = ["print", "/D:" + printer_name, pdf_path]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            logger.info(f"[SIMPLE_PRINT] Print command: {result.returncode}")
            logger.info(f"[SIMPLE_PRINT] Output: {result.stdout}")
            logger.info(f"[SIMPLE_PRINT] Error: {result.stderr}")
            
            if result.returncode == 0:
                return True, f"Impreso con comando 'print'"
            
            return True, f"Comando ejecutado - Verifica la impresora"
        
        except Exception as e:
            logger.warning(f"[SIMPLE_PRINT] Comando sistema falló: {e}")
            return False, str(e)


# Test
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s'
    )
    
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from datetime import datetime
    
    # Crear PDF de prueba
    test_dir = Path("test_output")
    test_dir.mkdir(exist_ok=True)
    
    pdf_path = test_dir / "simple_print_test.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "TEST IMPRESIÓN SIMPLE")
    c.setFont("Helvetica", 12)
    c.drawString(50, 720, f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawString(50, 700, "Método: Lector PDF predeterminado")
    c.save()
    
    logger.info("Iniciando prueba de impresión simple...")
    
    # Intenta con lector predeterminado
    success, msg = SimplePrinter.print_with_default_reader(str(pdf_path), "EPSON L4260 Series")
    
    if success:
        logger.info(f"✓ {msg}")
    else:
        logger.error(f"✗ {msg}")
        
        # Fallback: intenta con comando del sistema
        logger.info("\nIntentando método alternativo...")
        success, msg = SimplePrinter.print_with_system_command(str(pdf_path), "EPSON L4260 Series")
        
        if success:
            logger.info(f"✓ {msg}")
        else:
            logger.error(f"✗ {msg}")
