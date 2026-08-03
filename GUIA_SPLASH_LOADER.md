# 🚀 VISO Splash Loader - Guía de Uso

## ¿Qué se implementó?

Se creó un sistema completo de **pantalla de carga** para VISO que:

✅ **Muestra una ventana moderna** con barra de progreso antes de que inicie la aplicación  
✅ **Simula fases de carga**: PyQt5, Sesión, Licencia, Productos, Pacientes  
✅ **Se ejecuta en paralelo** con el programa principal  
✅ **Se cierra automáticamente** cuando VISO está listo  
✅ **Interfaz profesional** con colores coordinados y animaciones suaves  
✅ **Muy ligero y rápido** (Python optimizado + Tkinter nativo)

## Archivos Creados

| Archivo | Descripción |
|---------|-------------|
| `splash_loader.py` | Pantalla de carga con barra de progreso |
| `launcher.py` | Gestor que inicia splash + main.py |
| `run_viso.bat` | Atajo para ejecutar VISO con splash |
| `SplashLoader.cpp` | Versión alternativa en C++ (sin compilar) |
| `compile_splash_simple.bat` | Script para compilar C++ si es necesario |
| `README_SPLASH_LOADER.md` | Documentación técnica |

## 🎯 Cómo Usar

### Opción 1: Ejecutar con Launcher (RECOMENDADO)

```bash
python launcher.py
```

O simplemente haz doble clic en `run_viso.bat`

### Opción 2: Ejecutar main.py directamente (sin splash)

```bash
python main.py
```

### Opción 3: Crear Acceso Directo

1. Haz clic derecho en escritorio → "Nuevo" → "Acceso directo"
2. Ubicación: `C:\ruta\a\viso\launcher.py` (o `run_viso.bat`)
3. Dale un nombre (ej: "VISO")
4. Haz doble clic para ejecutar

## 🎨 Personalización

Puedes editar `splash_loader.py` para cambiar:

- **Colores**: Línea ~40 → `bg='#0f172a'` (azul oscuro), `fg='#60a5fa'` (azul claro)
- **Textos**: Línea ~46 → `text='⚡ VISO v4.2.4'`
- **Fases**: Línea ~95 → Edita la lista `phases`
- **Velocidad**: Línea ~107 → `time.sleep(0.3)` (más bajo = más rápido)

## 📊 Flujo de Ejecución

```
1. Usuario ejecuta launcher.py o run_viso.bat
   ↓
2. launcher.py inicia splash_loader.py en thread separado
   ↓
3. Aparece ventana de carga con animación
   ↓
4. launcher.py inicia main.py
   ↓
5. VISO se carga en background
   ↓
6. Cuando main.py está listo, splash se cierra automáticamente
   ↓
7. Se muestra interfaz completa de VISO
```

## 🔧 Solución de Problemas

### La ventana splash no aparece
- Verifica que `splash_loader.py` exista en la carpeta
- Intenta ejecutar: `python splash_loader.py` directamente

### El launcher no encuentra main.py
- Asegúrate de que `launcher.py` esté en la misma carpeta que `main.py`
- Verifica que las rutas sean correctas

### Quiero compilar la versión C++
- Necesitas Visual Studio Community (gratuito)
- Abre "Visual Studio Developer Command Prompt"
- Ejecuta: `compile_splash_simple.bat`

## ⚡ Ventajas vs Ejecutar main.py Directo

| Aspecto | Sin Splash | Con Splash |
|--------|-----------|-----------|
| Experiencia visual | Console salida confusa | Interfaz profesional |
| Retroalimentación | Sin feedback | Barra de progreso animada |
| Confusión del usuario | ¿Qué está haciendo? | Muestra cada fase |
| Profesionalismo | Básico | Producto pulido |

## 📝 Notas

- El splash loader es **completamente independiente** de main.py
- Si main.py falla, el splash se cerrará después de 5 segundos
- Los logs de consola siguen funcionando normalmente
- Compatible con PyInstaller para crear ejecutables .exe

---

¿Problemas? Verifica los logs en: `%TEMP%\VISO_LOGS\app_output.log`
