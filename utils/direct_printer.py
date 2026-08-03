#!/usr/bin/env python3
import os
import logging
import win32print
import win32ui
from PIL import Image, ImageWin
import pypdfium2 as pdfium  # Librería potente para renderizar PDF (pip install pypdfium2)

# Configuración de logs
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class DirectPrinter:
    @staticmethod
    def get_printer_handle(printer_name: str):
        """Obtiene el handle de la impresora."""
        try:
            return win32print.OpenPrinter(printer_name)
        except Exception as e:
            logger.error(f"No se pudo abrir la impresora: {e}")
            return None

    @staticmethod
    def print_pdf(pdf_path: str, printer_name: str):
        """
        Imprime un PDF convirtiéndolo a imagen y enviándolo vía GDI (Windows).
        """
        if not os.path.exists(pdf_path):
            logger.error(f"Archivo no encontrado: {pdf_path}")
            return False

        logger.info(f"Procesando PDF: {pdf_path}")
        
        try:
            # 1. Cargar el PDF con pypdfium2
            pdf = pdfium.PdfDocument(pdf_path)
            n_pages = len(pdf)
            logger.info(f"Documento cargado. Páginas: {n_pages}")

            # 2. Configurar el contexto de impresión de Windows (GDI)
            hDC = win32ui.CreateDC()
            hDC.CreatePrinterDC(printer_name)
            
            # Obtener dimensiones físicas de la impresora (para escalar la imagen)
            printable_area = (
                hDC.GetDeviceCaps(110), # HORZRES (Ancho en pixeles)
                hDC.GetDeviceCaps(111)  # VERTRES (Alto en pixeles)
            )
            printer_dpi = (
                hDC.GetDeviceCaps(88),  # LOGPIXELSX
                hDC.GetDeviceCaps(90)   # LOGPIXELSY
            )
            
            logger.info(f"Resolución impresora: {printable_area} @ {printer_dpi} DPI")

            # Iniciar trabajo de impresión
            hDC.StartDoc(f"Python Print: {os.path.basename(pdf_path)}")

            # 3. Iterar por cada página del PDF
            for page_number in range(n_pages):
                hDC.StartPage()
                
                # Renderizar página PDF a imagen PIL
                # scale=3 asegura buena calidad (300dpi aprox si base es 72)
                page = pdf[page_number]
                bitmap = page.render(scale=3) 
                pil_image = bitmap.to_pil()
                
                # Rotar si es necesario (ej. apaisado)
                if pil_image.width > pil_image.height:
                    pil_image = pil_image.rotate(90, expand=True)

                # Escalar imagen para ajustar al área de impresión (Fit to Page)
                # Mantener relación de aspecto
                img_w, img_h = pil_image.size
                prt_w, prt_h = printable_area
                
                ratio_w = prt_w / img_w
                ratio_h = prt_h / img_h
                scale_factor = min(ratio_w, ratio_h)
                
                new_w = int(img_w * scale_factor)
                new_h = int(img_h * scale_factor)
                
                # Centrar imagen
                x_offset = (prt_w - new_w) // 2
                y_offset = (prt_h - new_h) // 2
                
                # Crear Dib (Device Independent Bitmap) para Windows
                dib = ImageWin.Dib(pil_image)
                
                # Dibujar en el contexto de la impresora
                # Coordenadas: (x1, y1, x2, y2)
                dib.draw(hDC.GetHandleOutput(), (x_offset, y_offset, x_offset + new_w, y_offset + new_h))
                
                hDC.EndPage()
                logger.info(f"Página {page_number + 1} enviada.")

            # Finalizar trabajo
            hDC.EndDoc()
            hDC.DeleteDC()
            logger.info("Impresión finalizada correctamente.")
            return True

        except Exception as e:
            logger.error(f"Error durante la impresión: {e}")
            import traceback
            traceback.print_exc()
            return False

# --- GENERADOR DE PRUEBA ---
if __name__ == "__main__":
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    
    # 1. Crear PDF de prueba
    test_file = "prueba_epson.pdf"
    c = canvas.Canvas(test_file, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 24)
    c.drawString(100, h - 100, "PRUEBA DE IMPRESIÓN GDI")
    c.setFont("Helvetica", 14)
    c.drawString(100, h - 150, "Este texto fue renderizado a imagen y enviado vía Windows GDI.")
    c.drawString(100, h - 180, "Sin drivers RAW, sin Acrobat, sin dependencias externas.")
    c.rect(100, h - 300, 200, 100, fill=0) # Un rectángulo para validar gráficos
    c.save()
    
    # 2. Imprimir
    # IMPORTANTE: Pon aquí el nombre EXACTO de tu impresora como aparece en Windows
    IMPRESORA = "EPSON L4260 Series" 
    
    DirectPrinter.print_pdf(test_file, IMPRESORA)