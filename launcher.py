"""
Launcher mejorado para VISO con Splash Screen
Ejecuta el splash loader y main.py de forma integrada
"""
import os
import sys
import subprocess
import threading
import time
import multiprocessing
import signal
import psutil


def _ensure_logs_dir(script_dir: str) -> str:
    logs_dir = os.path.join(script_dir, "logs")
    try:
        os.makedirs(logs_dir, exist_ok=True)
    except Exception:
        pass
    return logs_dir

def find_python_executable():
    """Obtener ruta del ejecutable Python actual"""
    return sys.executable

def start_splash_loader(splash_process_holder):
    """Inicia el splash loader en un thread separado"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        splash_script = os.path.join(script_dir, 'splash_loader.py')
        
        if os.path.exists(splash_script):
            python_exe = find_python_executable()
            
            # Crear proceso del splash loader
            if sys.platform == 'win32':
                creation_flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                creation_flags = 0
            
            process = subprocess.Popen(
                [python_exe, splash_script],
                cwd=script_dir,
                creationflags=creation_flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            splash_process_holder.append(process)
            print(f"[SPLASH] Loader iniciado (PID: {process.pid})")
            
    except Exception as e:
        print(f"[ERROR] No se pudo iniciar splash loader: {e}")

def cleanup_splash(splash_process):
    """Limpiar proceso del splash loader"""
    if splash_process:
        try:
            if sys.platform == 'win32':
                # En Windows, terminar el grupo de procesos
                os.killpg(os.getpgid(splash_process.pid), signal.SIGTERM)
            else:
                splash_process.terminate()
            
            # Esperar a que se cierre
            splash_process.wait(timeout=2)
        except Exception as e:
            print(f"[DEBUG] No se pudo cerrar splash: {e}")

def main():
    """Función principal"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = _ensure_logs_dir(script_dir)
    
    # Holders para procesos
    splash_processes = []
    main_process = None
    
    try:
        # 1. Iniciar splash loader en thread
        splash_thread = threading.Thread(
            target=start_splash_loader,
            args=(splash_processes,),
            daemon=True
        )
        splash_thread.start()
        
        # 2. Dar tiempo para que el splash aparezca
        time.sleep(0.3)
        
        # 3. Iniciar main.py
        python_exe = find_python_executable()
        main_py = os.path.join(script_dir, 'main.py')
        
        print(f"[LAUNCHER] Iniciando VISO desde: {main_py}")
        
        if sys.platform == 'win32':
            creation_flags = 0  # main.py mostrará su propia ventana
        else:
            creation_flags = 0
        
        # Capturar stdout/stderr del proceso principal para diagnosticar crashes duros (Qt abort, etc.).
        stdout_path = os.path.join(logs_dir, "subprocess_stdout.log")
        stderr_path = os.path.join(logs_dir, "subprocess_stderr.log")

        env = os.environ.copy()
        env.setdefault("PYTHONUNBUFFERED", "1")
        env.setdefault("PYTHONFAULTHANDLER", "1")

        try:
            stdout_f = open(stdout_path, "a", buffering=1, encoding="utf-8", errors="replace")
        except Exception:
            stdout_f = None
        try:
            stderr_f = open(stderr_path, "a", buffering=1, encoding="utf-8", errors="replace")
        except Exception:
            stderr_f = None

        main_process = subprocess.Popen(
            [python_exe, main_py],
            cwd=script_dir,
            creationflags=creation_flags,
            env=env,
            stdout=stdout_f if stdout_f is not None else None,
            stderr=stderr_f if stderr_f is not None else None
        )
        
        print(f"[LAUNCHER] VISO iniciado (PID: {main_process.pid})")
        
        # 4. Esperar a que termine main.py
        main_process.wait()
        rc = int(main_process.returncode or 0)

        try:
            if stdout_f is not None:
                stdout_f.flush()
                stdout_f.close()
        except Exception:
            pass
        try:
            if stderr_f is not None:
                stderr_f.flush()
                stderr_f.close()
        except Exception:
            pass

        # Guardar el Ãºltimo return code (sirve si la consola se cierra rÃ¡pido).
        try:
            with open(os.path.join(logs_dir, "last_returncode.txt"), "w", encoding="utf-8") as f:
                f.write(str(rc))
        except Exception:
            pass

        if rc != 0:
            try:
                print(f"[LAUNCHER] main.py terminó con código: {rc}")
                print(f"[LAUNCHER] Logs: {stdout_path} | {stderr_path}")
            except Exception:
                pass
        
        # 5. Cerrar splash loader después de que main termine
        time.sleep(0.5)
        for splash in splash_processes:
            if splash and splash.poll() is None:  # Si aún está ejecutándose
                cleanup_splash(splash)
        
        print("[LAUNCHER] VISO finalizado")
        
    except KeyboardInterrupt:
        print("[LAUNCHER] Interrupción de usuario")
        # Terminar procesos
        if main_process and main_process.poll() is None:
            main_process.terminate()
        for splash in splash_processes:
            cleanup_splash(splash)
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] Error en launcher: {e}")
        # Limpieza de emergencia
        for splash in splash_processes:
            cleanup_splash(splash)
        if main_process and main_process.poll() is None:
            main_process.terminate()
        sys.exit(1)

if __name__ == '__main__':
    # Solo ejecutar en Windows o si se llama directamente
    if sys.platform == 'win32' or __name__ == '__main__':
        main()
    else:
        # En Linux/Mac, ejecutar main.py directamente
        import sys as _sys
        import runpy
        main_script = os.path.join(os.path.dirname(__file__), 'main.py')
        runpy.run_path(main_script, run_name='__main__')
