"""
Manejador de impresoras térmicas Bluetooth usando python-escpos.
Este es el método que REALMENTE funciona para BT-801 y similares.
Auto-detecta el puerto COM correcto.
"""

import os
import time
from PIL import Image


def _get_escpos_serial():
    from escpos.printer import Serial
    return Serial


class ThermalBluetoothPrinter:
    """Impresora térmica Bluetooth usando escpos con auto-detección de puerto."""
    
    @staticmethod
    def get_printer_port():
        """
        Obtiene el puerto COM de la impresora.
        Usa auto-detección si no ha sido configurado.
        """
        from utils.auto_detect_printer import AutoDetectPrinter
        
        port, _ = AutoDetectPrinter.find_printer_port()
        return port
    
    @staticmethod
    def detect_printer(port=None):
        """Detecta impresora térmica en puerto COM."""
        try:
            Serial = _get_escpos_serial()
            if not port:
                port = ThermalBluetoothPrinter.get_printer_port()
            
            if not port:
                return False, None
            
            try:
                printer = Serial(port, baudrate=9600, timeout=1, writeTimeout=1)
                printer.close()
                return True, port
            except Exception as e:
                print(f"No se pudo conectar a {port}: {e}")
                return False, None
        except Exception as e:
            return False, None
    
    @staticmethod
    def print_pdf_to_thermal(pdf_path, port=None, width_px=576, timeout=15):
        """
        Imprime PDF a impresora térmica (auto-detecta puerto si es necesario).
        """
        if not os.path.exists(pdf_path):
            return False, f"Archivo no encontrado: {pdf_path}"

        try:
            import fitz
        except Exception:
            return False, "El modulo PDF (PyMuPDF) no esta disponible en esta compilacion."
        
        printer = None
        temp_images = []
        start_time = time.time()
        
        def check_timeout():
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Tiempo de impresión excedido ({timeout}s)")
        
        try:
            try:
                Serial = _get_escpos_serial()
            except Exception:
                return False, "El modulo de impresion termica (python-escpos) no esta disponible en esta compilacion."

            # Auto-detectar puerto si no se proporciona
            if not port:
                check_timeout()
                port = ThermalBluetoothPrinter.get_printer_port()
                if not port:
                    # Obtener lista de puertos disponibles
                    import serial.tools.list_ports
                    available_ports = [p.device for p in serial.tools.list_ports.comports()]
                    
                    if available_ports:
                        ports_str = ", ".join(available_ports)
                        return False, f"No se encontró impresora térmica automáticamente.\n\nPuertos disponibles: {ports_str}\n\nVerifica que:\n1. La impresora esté ENCENDIDA\n2. Esté CONECTADA por Bluetooth\n3. Intenta reiniciar la impresora"
                    else:
                        return False, "No se encontraron puertos COM disponibles.\n\nVerifica que:\n1. La impresora esté ENCENDIDA\n2. Esté CONECTADA por Bluetooth\n3. Intenta reconectar la impresora"
            
            check_timeout()
            print(f"📱 Conectando a impresora en puerto {port}...")
            
            # Verificar que el puerto existe antes de intentar conectar
            import serial.tools.list_ports
            available_ports = [p.device for p in serial.tools.list_ports.comports()]
            
            if port not in available_ports:
                ports_str = ", ".join(available_ports) if available_ports else "Ninguno"
                return False, f"Impresora no encontrada en {port}.\n\nPuertos disponibles: {ports_str}\n\nVerifica que:\n1. La impresora esté ENCENDIDA\n2. Esté CONECTADA por Bluetooth\n3. El puerto {port} esté disponible"
            
            # Conectar a la impresora con timeouts cortos (se desconecta rápido)
            try:
                check_timeout()
                printer = Serial(port, baudrate=9600, timeout=1, writeTimeout=1)
            except Exception as e:
                return False, f"Error al conectar con impresora en {port}:\n{str(e)}\n\nVerifica que la impresora esté encendida y disponible."
            
            check_timeout()
            print("✓ Conectado")
            print(f"📄 Convirtiendo PDF: {os.path.basename(pdf_path)}")
            
            # Abrir PDF
            doc = fitz.open(pdf_path)
            
            # Procesar cada página
            for page_num, page in enumerate(doc):
                check_timeout()
                print(f"  Página {page_num + 1}/{len(doc)}...", end="", flush=True)
                
                # Convertir página a imagen
                pixmap = page.get_pixmap(dpi=200)
                img = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples).convert("RGB")
                
                # Redimensionar a ancho de impresora
                wpercent = (width_px / float(img.size[0]))
                hsize = int((float(img.size[1]) * float(wpercent)))
                img = img.resize((width_px, hsize), Image.Resampling.LANCZOS)
                
                # Guardar imagen temporal
                temp_file = f"temp_page_{page_num}.png"
                img.save(temp_file, "PNG")
                temp_images.append(temp_file)
                
                # Imprimir imagen
                check_timeout()
                printer.image(temp_file)
                print(" ✓")
            
            check_timeout()
            doc.close()
            
            # Cortar papel
            print("📋 Finalizando impresión...")
            check_timeout()
            try:
                if hasattr(printer, 'cut'):
                    printer.cut()
                else:
                    # Si cut no está disponible, usar comando raw para cortar papel
                    printer._raw(b'\x1d\x56\x00')
            except (AttributeError, Exception):
                # Si no se puede cortar, continuar de todas formas
                pass
            
            printer.close()
            
            # Limpiar imágenes temporales
            for temp_file in temp_images:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            
            return True, f"PDF impreso exitosamente en {port}"
        
        except TimeoutError as te:
            # Timeout
            for temp_file in temp_images:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
            if printer:
                try:
                    printer.close()
                except Exception:
                    pass
            return False, f"Tiempo de impresión excedido.\n\nVerifica que la impresora esté conectada y encendida."
        
        except Exception as e:
            # Limpiar imágenes temporales en caso de error
            for temp_file in temp_images:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
            
            error_msg = f"Error imprimiendo a thermal: {str(e)}"
            print(f"❌ {error_msg}")
            
            if printer:
                try:
                    printer.close()
                except Exception:
                    pass
            
            return False, f"Error de impresión térmica:\n{str(e)}\n\nVerifica que la impresora esté conectada y encendida."
    
    @staticmethod
    def print_image_thermal(image, port=None):
        """
        Imprime una imagen PNG/JPG directamente en la impresora térmica.
        
        Args:
            image: Objeto PIL Image
            port: Puerto COM (auto-detecta si es None)
        
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        printer = None
        try:
            try:
                Serial = _get_escpos_serial()
            except Exception:
                return False, "El modulo de impresion termica (python-escpos) no esta disponible en esta compilacion."

            # Auto-detectar puerto si no se proporciona
            if not port:
                port = ThermalBluetoothPrinter.get_printer_port()
            
            if not port:
                return False, "No se encontró puerto de impresora térmica"
            
            # Conectar a la impresora
            printer = Serial(port, baudrate=9600, timeout=2, writeTimeout=2)
            
            # Redimensionar imagen si es muy grande (ancho máximo 576px para 80mm)
            max_width = 576
            if image.width > max_width:
                ratio = max_width / image.width
                new_height = int(image.height * ratio)
                image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # Convertir a escala de grises si es necesario
            if image.mode != 'L':
                image = image.convert('L')
            
            # Imprimir imagen
            printer.image(image)
            
            # Avanzar papel después de imprimir (usar métodos disponibles)
            try:
                # Intentar usar feed si está disponible
                if hasattr(printer, 'feed'):
                    printer.feed(3)
                else:
                    # Si no está feed, usar control de papel
                    printer._raw(b'\n' * 3)
            except AttributeError:
                # Si feed no está disponible, simplemente ignorar
                pass
            
            return True, "Imagen impresa exitosamente"
        
        except Exception as e:
            error_msg = f"Error imprimiendo imagen térmica: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
        
        finally:
            if printer:
                try:
                    printer.close()
                except Exception:
                    pass


def test_thermal_printer():
    """Test del sistema de impresión térmica."""
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " PRUEBA DE IMPRESIÓN TÉRMICA BLUETOOTH ".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    # Paso 1: Detectar puertos
    print("[1] Detectando puertos COM...")
    ports = ThermalBluetoothPrinter.get_available_ports()
    
    if ports:
        print(f"✓ Puertos encontrados:")
        for p in ports:
            print(f"   - {p}")
    else:
        print("✗ No hay puertos COM disponibles")
        return
    
    print()
    
    # Paso 2: Crear PDF de prueba
    print("[2] Creando PDF de prueba...")
    
    from fpdf import FPDF
    test_pdf = "thermal_test.pdf"
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "PRUEBA ESCPOS TERMICO", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f"Hora: {time.strftime('%H:%M:%S')}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 10, "Si ves esto = FUNCIONA!", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.output(test_pdf)
    
    print(f"✓ PDF creado: {test_pdf}")
    print()
    
    # Paso 3: Imprimir
    print("[3] Imprimiendo...")
    print()
    print("⏳ INSTRUCCIONES:")
    print("   1. Enciende la impresora BT-801")
    print("   2. Asegúrate que esté emparejada (puerto COM debe aparecer arriba)")
    print("   3. Coloca papel en la impresora")
    print()
    
    input("Presiona ENTER para comenzar la impresión...")
    print()
    
    success, msg = ThermalBluetoothPrinter.print_pdf_to_thermal(test_pdf, port=ports[0] if ports else None)
    
    print()
    print("=" * 70)
    print("RESULTADO")
    print("=" * 70)
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
    test_thermal_printer()
