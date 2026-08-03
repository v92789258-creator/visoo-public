#!/usr/bin/env python3
"""
IMPRESIÓN DIRECTA CON GDI - VISO
Renderiza PDF a imagen y lo envía directamente a la impresora EPSON
usando Windows GDI (Graphics Device Interface).

Características:
✓ Sin programas externos
✓ Sin navegadores (Edge, Chrome)
✓ Sin aplicaciones de impresión
✓ Directo: PDF → GDI → Impresora
✓ Calidad profesional
"""

import os
import logging
from typing import Tuple
from pathlib import Path

try:
    import win32print
    import win32ui
    from PIL import Image, ImageWin
    import pypdfium2 as pdfium
except ImportError as e:
    raise ImportError(f"Librería requerida no disponible: {e}")

logger = logging.getLogger(__name__)


class DirectPrinter:
    """Impresión directa a EPSON usando Windows GDI."""
    
    @staticmethod
    def print_pdf(pdf_path: str, printer_name: str) -> Tuple[bool, str]:
        """
        Imprime un PDF convirtiéndolo a imagen y enviándolo vía GDI (Windows).
        
        Flujo:
        1. Cargar PDF con pypdfium2
        2. Renderizar cada página a imagen
        3. Usar Windows GDI para enviar a impresora
        
        Sin programas externos, sin navegadores, directo a la impresora.
        """
        if not os.path.exists(pdf_path):
            logger.error(f"Archivo no encontrado: {pdf_path}")
            return False, f"PDF no encontrado: {pdf_path}"

        logger.info(f"[GDI_PRINT] Procesando PDF: {pdf_path}")
        
        try:
            # 1. Cargar el PDF con pypdfium2
            pdf = pdfium.PdfDocument(pdf_path)
            n_pages = len(pdf)
            logger.info(f"[GDI_PRINT] Documento cargado. Páginas: {n_pages}")

            # 2. Configurar el contexto de impresión de Windows (GDI)
            hDC = win32ui.CreateDC()
            hDC.CreatePrinterDC(printer_name)
            
            # Obtener dimensiones físicas de la impresora
            printable_area = (
                hDC.GetDeviceCaps(110),  # HORZRES (Ancho en pixeles)
                hDC.GetDeviceCaps(111)   # VERTRES (Alto en pixeles)
            )
            printer_dpi = (
                hDC.GetDeviceCaps(88),   # LOGPIXELSX
                hDC.GetDeviceCaps(90)    # LOGPIXELSY
            )
            
            logger.info(f"[GDI_PRINT] Área imprimible: {printable_area}")
            logger.info(f"[GDI_PRINT] Resolución: {printer_dpi} DPI")

            # Iniciar trabajo de impresión
            hDC.StartDoc(f"VISO_Boleta_{Path(pdf_path).stem}")

            # 3. Iterar por cada página del PDF
            for page_number in range(n_pages):
                hDC.StartPage()
                
                logger.info(f"[GDI_PRINT] Renderizando página {page_number + 1}/{n_pages}...")
                
                # Renderizar página PDF a imagen PIL
                page = pdf[page_number]
                bitmap = page.render(scale=3)  # scale=3 da ~300dpi
                pil_image = bitmap.to_pil()
                
                # Convertir a RGB si es necesario
                if pil_image.mode != 'RGB':
                    pil_image = pil_image.convert('RGB')

                # Obtener dimensiones de la imagen
                img_w, img_h = pil_image.size
                prt_w, prt_h = printable_area
                
                # Escalar para ajustar a la página (Fit to Page)
                ratio_w = prt_w / img_w
                ratio_h = prt_h / img_h
                scale_factor = min(ratio_w, ratio_h) * 0.95  # 95% para margen
                
                new_w = int(img_w * scale_factor)
                new_h = int(img_h * scale_factor)
                
                # Centrar imagen
                x_offset = (prt_w - new_w) // 2
                y_offset = (prt_h - new_h) // 2
                
                logger.info(f"[GDI_PRINT] Escalando: {img_w}x{img_h} → {new_w}x{new_h}")
                
                # Crear DIB (Device Independent Bitmap) para Windows
                dib = ImageWin.Dib(pil_image)
                
                # Dibujar en el contexto de la impresora
                dib.draw(hDC.GetHandleOutput(), (x_offset, y_offset, x_offset + new_w, y_offset + new_h))
                
                hDC.EndPage()
                logger.info(f"[GDI_PRINT] ✓ Página {page_number + 1} enviada")

            # Finalizar trabajo
            hDC.EndDoc()
            hDC.DeleteDC()
            
            logger.info(f"[GDI_PRINT] ✓ Impresión finalizada correctamente")
            return True, f"Boleta impresa en {printer_name}"

        except Exception as e:
            logger.error(f"[GDI_PRINT] Error durante la impresión: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error de impresión: {e}"


# Test
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s'
    )
    
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from datetime import datetime
    
    # Crear boleta de prueba
    test_dir = Path("test_output")
    test_dir.mkdir(exist_ok=True)
    
    test_file = test_dir / "gdi_boleta_test.pdf"
    c = canvas.Canvas(str(test_file), pagesize=letter)
    w, h = letter
    
    # Encabezado
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, h - 50, "BOLETA DE VENTA")
    
    # Detalles
    c.setFont("Helvetica", 11)
    y = h - 100
    c.drawString(50, y, "Empresa: Mi Negocio VISO")
    y -= 30
    c.drawString(50, y, f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 30
    c.drawString(50, y, "Método: Impresión GDI directa (sin programas externos)")
    
    # Productos
    y -= 50
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Descripción")
    c.drawString(300, y, "Cantidad")
    c.drawString(400, y, "Precio")
    c.drawString(500, y, "Total")
    
    y -= 20
    c.line(50, y, 550, y)
    
    # Items
    c.setFont("Helvetica", 10)
    y -= 30
    items = [
        ("Producto A", "2", "$150.00", "$300.00"),
        ("Producto B", "1", "$250.00", "$250.00"),
        ("Producto C", "3", "$100.00", "$300.00"),
    ]
    
    for desc, cant, precio, total in items:
        c.drawString(50, y, desc)
        c.drawString(300, y, cant)
        c.drawString(400, y, precio)
        c.drawString(500, y, total)
        y -= 25
    
    # Total
    y -= 20
    c.line(50, y, 550, y)
    y -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(400, y, "TOTAL: $850.00")
    
    c.save()
    
    logger.info("=" * 70)
    logger.info("PRUEBA DE IMPRESIÓN DIRECTA - GDI")
    logger.info("=" * 70)
    
    # Imprimir
    IMPRESORA = "EPSON L4260 Series"
    success, msg = DirectPrinter.print_pdf(str(test_file), IMPRESORA)
    
    if success:
        logger.info(f"✓ {msg}")
        logger.info("=" * 70)
        logger.info("✓✓✓ BOLETA DEBE ESTAR IMPRIMIÉNDOSE AHORA ✓✓✓")
        logger.info("=" * 70)
    else:
        logger.error(f"✗ {msg}")
