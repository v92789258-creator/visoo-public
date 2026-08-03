"""
SplashScreen - Pantalla de carga simple con imagen
"""
import sys
import os
import tkinter as tk
import threading
import time

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class SplashLoader:
    def __init__(self, root):
        self.root = root
        self.root.title("VISO")
        
        # Ventana sin decoración
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        
        # Cargar imagen splash.png
        self.photo = None
        try:
            if HAS_PIL:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                splash_path = os.path.join(script_dir, 'splash.png')
                
                if os.path.exists(splash_path):
                    img = Image.open(splash_path)
                    
                    # Limitar a mucho más pequeño (1/8 de la pantalla)
                    screen_width = self.root.winfo_screenwidth()
                    screen_height = self.root.winfo_screenheight()
                    max_width = screen_width // 4
                    max_height = screen_height // 4
                    
                    # Redimensionar manteniendo proporción
                    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                    
                    img_width = img.width
                    img_height = img.height
                    
                    self.photo = ImageTk.PhotoImage(img)
                    
                    # Configurar ventana con tamaño de la imagen
                    self.root.geometry(f'{img_width}x{img_height}')
                    
                    # Centrar ventana
                    self.root.update_idletasks()
                    x = (screen_width // 2) - (img_width // 2)
                    y = (screen_height // 2) - (img_height // 2)
                    self.root.geometry(f'{img_width}x{img_height}+{x}+{y}')
                    
                    # Label con la imagen
                    label = tk.Label(self.root, image=self.photo, bg='#000000')
                    label.pack(fill=tk.BOTH, expand=True)
                    self.logo_loaded = True
                else:
                    self.root.geometry('400x300')
                    label = tk.Label(self.root, text='VISO', font=('Arial', 40), bg='#000000', fg='#ffffff')
                    label.pack(fill=tk.BOTH, expand=True)
                    self.logo_loaded = False
        except Exception as e:
            print(f"[DEBUG] Error cargando splash: {e}")
            self.root.geometry('400x300')
            label = tk.Label(self.root, text='VISO', font=('Arial', 40), bg='#000000', fg='#ffffff')
            label.pack(fill=tk.BOTH, expand=True)
            self.logo_loaded = False
        
        self.should_close = False
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def on_closing(self):
        """Manejar cierre de ventana"""
        self.should_close = True
        try:
            self.root.destroy()
        except:
            pass
        sys.exit(0)


class SplashScreen:
    """Clase simplificada para ejecutar el splash desde main.py"""
    def __init__(self):
        self.root = None
        self.splash = None
        
    def show(self):
        """Mostrar el splash screen"""
        self.root = tk.Tk()
        self.splash = SplashLoader(self.root)
        
        def close_splash():
            # Esperar 1.5 segundos
            time.sleep(1.5)
            
            try:
                self.root.destroy()
            except:
                pass
        
        # Cerrar el splash en un thread separado
        close_thread = threading.Thread(target=close_splash, daemon=True)
        close_thread.start()
        
        # Timeout: cerrar después de 15 segundos como máximo
        def timeout_close():
            time.sleep(15)
            try:
                if self.root.winfo_exists():
                    self.root.destroy()
            except:
                pass
        
        timeout_thread = threading.Thread(target=timeout_close, daemon=True)
        timeout_thread.start()
        
        # Ejecutar el mainloop
        try:
            self.root.mainloop()
        except:
            pass


def run_splash():
    """Ejecutar la pantalla de carga"""
    root = tk.Tk()
    splash = SplashLoader(root)
    
    def close_splash():
        time.sleep(1.5)
        try:
            root.destroy()
        except:
            pass
    
    close_thread = threading.Thread(target=close_splash, daemon=True)
    close_thread.start()
    
    def timeout_close():
        time.sleep(15)
        try:
            if root.winfo_exists():
                root.destroy()
        except:
            pass
    
    timeout_thread = threading.Thread(target=timeout_close, daemon=True)
    timeout_thread.start()
    
    root.mainloop()


if __name__ == '__main__':
    run_splash()



if __name__ == '__main__':
    run_splash()
