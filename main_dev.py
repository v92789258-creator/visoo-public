"""Wrapper de main.py para desarrollo - agrega --dev automáticamente"""

import sys
import os

# Agregar --dev a los argumentos si no está presente
if "--dev" not in sys.argv and "dev" not in sys.argv:
    sys.argv.append("--dev")

# Importar y ejecutar main
from main import __name__ as main_name

if __name__ == "__main__":
    # Re-ejecutar como si fuera main.py pero con --dev
    from main import app_instance, main as main_func
    
    try:
        app_instance_obj = app_instance
        
        if app_instance_obj.initialize():
            if main_func(app_instance_obj):
                exit_code = app_instance_obj.app.exec_()
                sys.exit(exit_code)
            else:
                print("[ERROR] La función main() retornó False")
                print("\n" + "="*70)
                print("PRESIONA ENTER PARA CERRAR...")
                print("="*70)
                try:
                    input()
                except:
                    pass
                sys.exit(1)
        else:
            print("[ERROR] No se pudo inicializar la aplicación")
            print("\n" + "="*70)
            print("PRESIONA ENTER PARA CERRAR...")
            print("="*70)
            try:
                input()
            except:
                pass
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR CRÍTICO] Error al iniciar la aplicación: {e}", file=sys.stderr)
        print("\nDetalles del error:")
        import traceback
        traceback.print_exc(file=sys.stderr)
        
        print("\n" + "="*70)
        print("PRESIONA ENTER PARA CERRAR...")
        print("="*70)
        try:
            input()
        except:
            pass
        
        sys.exit(1)
