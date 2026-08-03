# VISO 4.2.4

VISO es un sistema de gestión para ópticas. Está pensado para centralizar en una sola plataforma la atención de pacientes, el catálogo de productos, el inventario, las ventas, los reportes y la comunicación con servicios externos.

No es únicamente una pantalla de ventas: el proyecto incluye una aplicación de escritorio, un backend PHP, sincronización con servidores, generación de documentos, integraciones tributarias y herramientas de compilación y mantenimiento.

## ¿Qué funciones tiene?

### Gestión de la óptica

- Registro y consulta de pacientes y clientes.
- Gestión de productos, categorías, precios, imágenes y existencias.
- Inventario, movimientos, kardex y actualización de stock.
- Registro e historial de ventas.
- Gestión de graduaciones y datos relacionados con la atención óptica.
- Citas, notificaciones y avisos dentro de la aplicación.
- Usuarios, autenticación, permisos y control de licencias.

### Documentos, reportes e impresión

- Reportes diarios, globales y avanzados.
- Exportación de información a Excel.
- Generación de documentos PDF y comprobantes.
- Códigos QR y manejo de imágenes.
- Soporte para impresoras, puertos serie y algunas impresoras térmicas.

### Facturación e integraciones

- Integración con servicios de SUNAT para operaciones y comprobantes electrónicos.
- Generación de formatos UBL y archivos PLE en los módulos correspondientes.
- Comunicación con servicios web propios mediante APIs PHP.
- Envío de notificaciones y herramientas de integración con WhatsApp.
- Sincronización de información entre la aplicación, el servidor y dispositivos secundarios.

### Administración y continuidad operativa

- Copias de seguridad y restauración.
- Colas de sincronización y sincronización en segundo plano.
- Diagnóstico, registros de errores y comprobaciones de dependencias.
- Scripts para migración, actualización y recuperación de instalaciones.
- Construcción de ejecutables para Windows con PyInstaller y herramientas auxiliares de compilación.

## Arquitectura general

El proyecto está organizado por responsabilidades:

```text
VISO/
├── main.py                 Aplicación de escritorio y punto de entrada
├── core/                   Configuración, inicio, logs y manejo de errores
├── gui/                    Ventanas, páginas, diálogos y componentes PyQt5
├── utils/                  Inventario, ventas, reportes, sincronización e integraciones
├── php/                    Backend, autenticación, licencias, backups y APIs
├── api/                    Servicios auxiliares, incluidos endpoints para Android
├── data/                   Recursos y datos base no sensibles
├── images/                 Imágenes y recursos visuales
├── web-viso/               Recursos web complementarios
├── cpp/, csharp/, ext/     Componentes y herramientas auxiliares
└── scripts/                Utilidades de mantenimiento y soporte
```

La aplicación principal está desarrollada en Python con PyQt5. El backend está desarrollado en PHP y utiliza MySQL/MariaDB. La comunicación entre ambos lados se realiza mediante HTTP/HTTPS y APIs, mientras que los procesos de sincronización utilizan colas, trabajadores y tareas en segundo plano.

## ¿Qué tan grande o complejo es?

VISO es un proyecto grande para una aplicación mantenida por un equipo pequeño. En esta versión pública el repositorio contiene aproximadamente:

- Más de 500 archivos versionados.
- 313 archivos Python para la aplicación, la interfaz, utilidades y herramientas.
- 49 archivos PHP para el backend y las APIs.
- Código adicional HTML, JavaScript, CSS, C/C++ y C#.
- La carpeta `gui/` contiene más de 200 archivos y alrededor de 100.000 líneas de código.

Su complejidad viene de que combina varias áreas que normalmente estarían separadas:

1. Una aplicación de escritorio con muchas pantallas y diálogos.
2. Reglas de negocio para pacientes, ventas, inventario y reportes.
3. Persistencia local y comunicación con bases de datos remotas.
4. Sincronización, colas, trabajadores y manejo de conflictos.
5. Backend PHP con autenticación, licencias, backups y endpoints para distintos clientes.
6. Integraciones externas como SUNAT, WhatsApp, impresoras y servicios de actualización.
7. Empaquetado como ejecutable de Windows y herramientas de diagnóstico.

Por eso no debe tratarse como un script aislado. Una modificación en inventario, ventas, sincronización o APIs puede afectar otras partes del sistema. Para contribuir conviene entender primero el flujo de datos y probar los cambios en una instalación de desarrollo.

## Requisitos

- Windows 10/11 recomendado para la aplicación de escritorio.
- Python 3.10 o superior.
- PHP 8.x y MySQL/MariaDB si se utilizará el backend incluido en `php/`.

La aplicación se desarrolló principalmente para Windows. Algunas funciones opcionales, como impresión, generación de Excel o sincronización remota, requieren sus dependencias y configuración correspondiente.

## Instalación rápida

```powershell
git clone https://github.com/v92789258-creator/visoo-public.git
cd visoo-public
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

`requirements.txt` es la instalación completa e incluye las librerías para la interfaz PyQt5, PDF, imágenes, códigos QR, red, impresoras, Excel, validación, sincronización y herramientas de compilación.

Si solo quieres probar la interfaz y las funciones básicas, puedes instalar el conjunto reducido:

```powershell
pip install -r requirements_minimal.txt
```

El conjunto reducido puede necesitar paquetes adicionales cuando se utilicen módulos avanzados.

## Crear el ejecutable de Windows

El archivo recomendado para compilar VISO es `build_exe_optimized.py`. Primero instala las dependencias completas del proyecto y ejecuta el comando desde la carpeta raíz:

```powershell
pip install -r requirements.txt
python build_exe_optimized.py
```

Este script usa PyInstaller y genera un build optimizado en modo `onedir`. El ejecutable queda normalmente en:

```text
dist/VISO/VISO.exe
```

El proceso necesita encontrar `main.py` e `icon.ico`, y recomienda tener al menos 7 GB libres entre el disco del proyecto y la carpeta temporal de Windows. Si existe `splash.png`, también se incorpora al arranque.

### Perfiles de compilación

Sin argumentos se compila el perfil completo. También puedes usar estos perfiles y opciones:

```powershell
# Desarrollo: deja visible la consola para ver errores
python build_exe_optimized.py dev

# Inicio más rápido, reduciendo componentes pesados
python build_exe_optimized.py faststart

# Ejecutable más pequeño si UPX está instalado
python build_exe_optimized.py small

# Perfil rápido conservando Excel, PDF, reportes e impresión térmica
python build_exe_optimized.py faststart withpdf withreports withexcel withthermal
```

Opciones adicionales: `nopdf`, `noreports`, `noexcel`, `nothermal`, `noqml`, `legacydata`, `withpdf`, `withreports`, `withexcel` y `withthermal`. Al usar `noexcel`, por ejemplo, el ejecutable no incluirá la exportación a Excel.

El archivo `setup.py` también contiene una configuración alternativa de PyInstaller, pero `build_exe_optimized.py` es la opción recomendada para la versión actual.

## Backend PHP

El código PHP está en `php/`. Configura el servidor web y la base de datos según tu entorno. Las credenciales y tokens deben definirse mediante variables de entorno; nunca las guardes en el repositorio:

- `VISO_DB_PASSWORD`
- `VISO_ADMIN_TOKEN`
- `VISO_BACKUP_TOKEN`
- `SUNAT_DEFAULT_TOKEN`

Revisa y cambia las URLs de API antes de desplegar una instalación propia.

## Seguridad

Este repositorio no contiene contraseñas, tokens privados, bases de datos ni datos de usuarios. Antes de publicar una instancia propia, configura secretos fuera del código y revisa las URLs de servicios externos.

## Licencia

Este proyecto se distribuye bajo la [Licencia MIT](LICENSE). Puedes usarlo, copiarlo, modificarlo y redistribuirlo respetando sus condiciones.

## Contribuciones

Las contribuciones son bienvenidas mediante issues y pull requests. Cualquier persona puede hacer un fork y proponer cambios; el acceso de escritura directo a `main` depende de los permisos de GitHub.
