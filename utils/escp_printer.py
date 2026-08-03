#!/usr/bin/env python3
"""
IMPRESIÓN DIRECTA PURA: PDF → Imagen → Protocolo ESC/P → EPSON L4260
Sin GUIs, sin programas externos, sin PowerShell.
Solo Python puro.
"""

import os
import sys
import logging
from typing import Tuple
from pathlib import Path

try:
    import pypdfium2 as pdfium
    from PIL import Image
    import win32print
    import win32api
except ImportError as e:
    print(f"Error: {e}")
    print("Instala: pip install pypdfium2 pillow pywin32")
    sys.exit(1)

logger = logging.getLogger(__name__)


class DirectEPSONPrinter:
    """Imprime directamente a EPSON usando protocolo ESC/P nativo."""
    
    @staticmethod
    def pdf_to_image(pdf_path: str, dpi: int = 100):
        """Convierte PDF a imagen usando pypdfium2 (sin poppler)."""
        logger.info(f"[DIRECT] Leyendo PDF con pypdfium2...")
        
        try:
            # Abrir PDF
            pdf = pdfium.PdfDocument.new()
            pdf = pdfium.PdfDocument.load(pdf_path)
            
            # Primera página
            page = pdf.get_page(0)
            
            # Obtener dimensiones
            width = int(page.get_width())
            height = int(page.get_height())
            
            logger.info(f"[DIRECT] Dimensiones: {width}x{height}")
            
            # Renderizar a bitmap
            bitmap = page.render(
                pdfium.Matrix().scale(dpi/72, dpi/72),  # DPI
                pdfium.BitmapConversion.BGR,  # Formato BGR
            )
            
            logger.info(f"[DIRECT] Renderizado exitoso")
            
            # Convertir a PIL Image
            image = Image.frombytes(
                "RGB",
                (bitmap.get_width(), bitmap.get_height()),
                bitmap.get_bytes(),
            )
            
            logger.info(f"[DIRECT] Imagen PIL creada: {image.size}")
            
            return image
        
        except Exception as e:
            logger.error(f"[DIRECT] Error renderizando: {e}")
            raise
    
    @staticmethod
    def image_to_escp(image: Image.Image) -> bytes:
        """
        Convierte imagen a formato ESC/P (protocolo nativo EPSON).
        Esto permite que la impresora imprima sin necesidad de drivers especiales.
        """
        logger.info(f"[DIRECT] Convirtiendo imagen a ESC/P...")
        
        try:
            # Convertir a blanco y negro para ESC/P
            image = image.convert('1')  # 1-bit (B/W)
            
            width, height = image.size
            
            logger.info(f"[DIRECT] Imagen B/W: {width}x{height}")
            
            # ESC/P commands
            escp_data = bytearray()
            
            # Inicializar impresora
            escp_data.extend(b'\x1b@')  # ESC @ (init)
            
            # Configurar modo gráfico
            escp_data.extend(b'\x1b*')  # ESC * (graphics)
            escp_data.extend(b'\x01')   # Mode 1 (single density)
            
            # Ancho en bytes (ESC/P usa 8 pixels por byte)
            width_bytes = (width + 7) // 8
            
            # Añadir ancho en formato little-endian
            escp_data.extend(bytes([width_bytes & 0xFF, (width_bytes >> 8) & 0xFF]))
            
            # Convertir imagen a bytes
            pixels = image.tobytes()
            
            # Enviar cada línea
            for y in range(height):
                row_start = y * width_bytes
                row_end = row_start + width_bytes
                row_data = pixels[row_start:row_end]
                escp_data.extend(row_data)
            
            # Finalizar
            escp_data.extend(b'\x0C')  # FF (form feed)
            escp_data.extend(b'\x1b@')  # ESC @ (reset)
            
            logger.info(f"[DIRECT] Datos ESC/P generados: {len(escp_data)} bytes")
            
            return bytes(escp_data)
        
        except Exception as e:
            logger.error(f"[DIRECT] Error convirtiendo a ESC/P: {e}")
            raise
    
    @staticmethod
    def send_to_printer(data: bytes, printer_name: str) -> Tuple[bool, str]:
        """Envía datos directamente a la impresora."""
        logger.info(f"[DIRECT] Enviando {len(data)} bytes a {printer_name}...")
        
        try:
            # Abrir impresora
            hprinter = win32print.OpenPrinter(printer_name)
            logger.info(f"[DIRECT] Conexión abierta")
            
            # Crear trabajo de impresión
            job_id = win32print.StartDocPrinter(
                hprinter,
                1,
                (f"VISO_Direct_Print", None, "RAW")
            )
            logger.info(f"[DIRECT] Job creado: {job_id}")
            
            # Enviar datos
            win32print.WritePrinter(hprinter, data)
            logger.info(f"[DIRECT] Datos enviados")
            
            # Finalizar
            win32print.EndDocPrinter(hprinter)
            win32print.ClosePrinter(hprinter)
            
            logger.info(f"[DIRECT] ✓ Impresión completada")
            return True, f"Impreso en {printer_name}"
        
        except Exception as e:
            logger.error(f"[DIRECT] Error: {e}")
            return False, str(e)
    
    @staticmethod
    def print_pdf_direct(pdf_path: str, printer_name: str, dpi: int = 100) -> Tuple[bool, str]:
        """
        Imprime PDF directamente a EPSON sin intermediarios.
        
        Flujo:
        1. PDF → Imagen (pypdfium2)
        2. Imagen → ESC/P (protocolo nativo EPSON)
        3. ESC/P → Cola de impresora (win32print)
        
        Sin GUIs, sin programas externos, sin PowerShell.
        """
        try:
            logger.info("=" * 70)
            logger.info("[DIRECT] IMPRESIÓN DIRECTA - EPSON L4260")
            logger.info("=" * 70)
            
            if not os.path.exists(pdf_path):
                return False, f"PDF no encontrado: {pdf_path}"
            
            logger.info(f"[DIRECT] PDF: {pdf_path}")
            logger.info(f"[DIRECT] Impresora: {printer_name}")
            
            # Paso 1: PDF a imagen
            logger.info("\n[PASO 1] Renderizando PDF...")
            image = DirectEPSONPrinter.pdf_to_image(pdf_path, dpi=dpi)
            
            # Paso 2: Imagen a ESC/P
            logger.info("\n[PASO 2] Convirtiendo a ESC/P...")
            escp_data = DirectEPSONPrinter.image_to_escp(image)
            
            # Paso 3: Enviar a impresora
            logger.info("\n[PASO 3] Enviando a impresora...")
            success, msg = DirectEPSONPrinter.send_to_printer(escp_data, printer_name)
            
            if success:
                logger.info("\n" + "=" * 70)
                logger.info("✓✓✓ ÉXITO - IMPRESIÓN DIRECTA COMPLETADA ✓✓✓")
                logger.info("=" * 70)
            
            return success, msg
        
        except Exception as e:
            logger.error(f"[DIRECT] Error crítico: {e}")
            import traceback
            traceback.print_exc()
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
    
    pdf_path = test_dir / "escp_test.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "PRUEBA IMPRESION DIRECTA")
    c.setFont("Helvetica", 12)
    c.drawString(50, 720, f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawString(50, 700, "Metodo: PDF → pypdfium2 → ESC/P → EPSON")
    c.drawString(50, 680, "Sin GUIs, sin programas externos, puro Python")
    
    # Agregar algunas líneas
    c.setFont("Helvetica", 10)
    y = 650
    for i in range(15):
        c.drawString(50, y, f"Línea {i+1}: Lorem ipsum dolor sit amet")
        y -= 20
    
    c.save()
    
    logger.info("Iniciando prueba de impresión directa...")
    success, msg = DirectEPSONPrinter.print_pdf_direct(str(pdf_path), "EPSON L4260 Series", dpi=100)
    
    if success:
        logger.info(f"✓ {msg}")
    else:
        logger.error(f"✗ {msg}")
