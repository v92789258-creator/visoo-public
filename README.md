# VISO

Sistema de gestión para ópticas. Incluye una aplicación de escritorio para administrar productos, pacientes, ventas, inventario, reportes e impresión, además de un backend PHP para sincronización y servicios web.

## Requisitos

- Windows 10/11 recomendado para la aplicación de escritorio.
- Python 3.10 o superior.
- PHP 8.x y MySQL/MariaDB si se utilizará el backend incluido en `php/`.

## Instalación rápida

```powershell
git clone https://github.com/v92789258-creator/visoo-public.git
cd visoo-public
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements_minimal.txt
python main.py
```

Para generar un ejecutable de Windows, instala las dependencias de compilación y ejecuta:

```powershell
python setup.py
```

## Backend PHP

El código PHP está en `php/`. Configura el servidor web y la base de datos según tu entorno. Las credenciales y tokens deben definirse mediante variables de entorno; nunca las guardes en el repositorio:

- `VISO_DB_PASSWORD`
- `VISO_ADMIN_TOKEN`
- `VISO_BACKUP_TOKEN`
- `SUNAT_DEFAULT_TOKEN`
- `ANTHROPIC_API_KEY` (opcional)

Revisa y cambia las URLs de API antes de desplegar una instalación propia.

## Qué incluye

- Gestión de pacientes, productos, ventas e inventario.
- Reportes y generación de documentos PDF.
- Soporte para impresión y códigos QR.
- Integración con servicios externos cuando se configuran sus credenciales.

## Seguridad

Este repositorio no contiene contraseñas, tokens privados, bases de datos ni datos de usuarios. Antes de publicar una instancia propia, configura secretos fuera del código y revisa las URLs de servicios externos.

## Licencia

Este proyecto se distribuye bajo la [Licencia MIT](LICENSE). Puedes usarlo, copiarlo, modificarlo y redistribuirlo respetando sus condiciones.

## Contribuciones

Las contribuciones son bienvenidas mediante issues y pull requests. Cualquier persona puede hacer un fork y proponer cambios; el acceso de escritura directo a `main` depende de los permisos de GitHub.
