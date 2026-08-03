# INTEGRACIÓN COMPLETA DE SUNAT EN VISO v4.2.4

## 📋 RESUMEN DE IMPLEMENTACIÓN

Se ha implementado un sistema **completo de emisión electrónica SUNAT** en VISO con capacidad de generar, firmar y enviar comprobantes electrónicos (boletas y facturas).

---

## 🏗️ ARQUITECTURA DEL SISTEMA

### Módulos Creados:

#### 1. **sunat_ubl_generator.py**
- Generador de XML en formato UBL 2.1 (estándar internacional de facturación)
- Soporta: Facturas (tipo 01) y Boletas (tipo 03)
- Incluye: Items, totales, impuestos, datos del cliente y emisor
- **Clase Principal**: `SUNATUBLGenerator`

#### 2. **sunat_digital_signer.py**
- Firma digital de documentos XML según estándar XmlDsig
- Validación de certificados digitales
- Manejo de claves privadas (PEM, PKCS12)
- **Clase Principal**: `SUNATDigitalSigner`

#### 3. **sunat_client.py**
- Cliente SOAP para comunicación con SUNAT
- Envío de comprobantes firmados
- Consulta de estado de envíos
- Recepción de CDR (Comprobante de Recepción)
- Soporta: Ambiente de testing y producción
- **Clase Principal**: `SUNATClient`

#### 4. **configurador_sunat.py**
- Gestor centralizado de configuración SUNAT
- Almacenamiento seguro de credenciales
- Gestión de certificados y claves
- Generación de números de comprobantes
- **Clase Principal**: `ConfiguradorSUNAT`

#### 5. **generador_boletas_sunat.py**
- Integrador completo de generación de boletas con SUNAT
- Validación de datos de boletas
- Generación local o electrónica
- Envío automático a SUNAT
- **Clase Principal**: `GeneradorBoletasSUNAT`

#### 6. **gestor_certificados.py**
- Gestor del ciclo de vida de certificados
- Importación y validación de certificados
- Alertas de vencimiento
- Registro y rotación de certificados
- **Clase Principal**: `GestorCertificados`

---

## 🎨 INTERFAZ DE USUARIO

### Nueva Sección en Configuración: "Emisión Electrónica"

La sección SUNAT en la página de configuración ahora incluye:

#### Datos de la Empresa:
- RUC (consulta automática a SUNAT)
- Razón social
- Dirección
- Departamento, Provincia, Distrito
- Estado y Condición

#### Configuración de Emisión Electrónica:
- **Estado**: Botón habilitador/deshabilitador 🔴/🟢
- **Usuario SOL**: Credencial de SUNAT
- **Contraseña SOL**: Almacenada encriptada
- **Certificado Digital**: Carga de archivo (.pem/.cer)
- **Clave Privada**: Carga de archivo (.key/.pfx)
- **Ambiente**: Testing o Producción
- **Opciones**:
  - ☑️ Enviar automáticamente a SUNAT
  - ☑️ Guardar CDR localmente

#### Botones de Acción:
- **Probar Conexión SUNAT**: Valida credenciales
- **Guardar Configuración**: Persiste toda la configuración

---

## 🔧 INSTALACIÓN Y CONFIGURACIÓN

### 1. Dependencias Necesarias

Agregar a `requirements.txt`:

```
lxml>=4.9.2
cryptography>=39.0.0
requests>=2.28.0
```

Instalar:
```bash
pip install -r requirements.txt
```

### 2. Obtener Certificado Digital

1. Ir a: https://www.sunat.gob.pe
2. Descargar certificado digital (extensión .cer)
3. Convertir a formato PEM (si es necesario)

### 3. Credenciales SOL

- Usuario: `usuario.sol` (proporcionado por SUNAT)
- Contraseña: Contraseña del usuario SOL

### 4. Primer Uso

1. Abrir **Configuración → Información SUNAT**
2. Ingresar RUC y consultar datos
3. Cargar certificado y clave privada
4. Ingresar credenciales SOL
5. Hacer clic en "Probar Conexión SUNAT"
6. Si es exitoso, hacer clic en "Habilitar Emisión Electrónica"

---

## 💡 CÓMO USAR

### Generar Boleta Electrónica

```python
from utils.generador_boletas_sunat import GeneradorBoletasSUNAT
from datetime import datetime

# Inicializar generador
generador = GeneradorBoletasSUNAT("usuario1", "C:/VISO")

# Preparar datos
datos_boleta = {
    'numero_serie': 'B001',
    'numero_correlativo': '000001',
    'tipo_cliente': '1',  # 1=DNI, 6=RUC
    'numero_cliente': '12345678',
    'cliente_nombre': 'JUAN PEREZ RODRIGUEZ',
    'fecha_emision': datetime.now().strftime('%Y-%m-%d'),
    'items': [
        {
            'descripcion': 'Lentes oftálmicos',
            'cantidad': 1,
            'precio_unitario': 100.00,
            'total': 100.00,
            'unidad': 'C62'
        }
    ],
    'subtotal': 100.00,
    'igv': 18.00,
    'total': 118.00
}

# Validar
is_valid, errores = generador.validar_boleta(datos_boleta)
if not is_valid:
    print(f"Errores: {errores}")
    exit(1)

# Generar y enviar
success, result = generador.generar_boleta_electronica(datos_boleta)

if success:
    print(f"Boleta generada: {result['xml_path']}")
    print(f"Ticket SUNAT: {result['ticket_numero']}")
    print(f"CDR: {result['cdr_path']}")
else:
    print(f"Errores: {result['errores']}")
```

### Verificar Estado de Certificados

```python
from utils.gestor_certificados import GestorCertificados

gestor = GestorCertificados("usuario1", "C:/VISO")

# Generar reporte
reporte = gestor.obtener_reporte_certificados()
print(reporte)

# Verificar próximos a vencer
alertas = gestor.verificar_certificados_proximos_vencer(dias_alerta=30)
for cert in alertas:
    print(f"Alerta: {cert['id']} vence en {cert['dias_faltantes']} días")
```

---

## 📊 FLUJO DE GENERACIÓN DE BOLETA

```
┌─────────────────────────────────┐
│  Datos de Boleta                │
│ (cliente, items, montos)        │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Validación de Datos            │
│ (items, totales, cliente)       │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Generación XML UBL 2.1         │
│ (estructura completa)           │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Firma Digital                  │
│ (XmlDsig con certificado)       │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Guardar XML Firmado            │
│ (localización segura)           │
└──────────────┬──────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  ¿Envío Automático Habilitado?      │
│         SÍ ↓         NO ↓            │
└──────────┬──────────────┬───────────┘
           │              │
           ▼              ▼
    ┌─────────────┐  ┌──────────────┐
    │  Enviar a   │  │ Almacenar    │
    │  SUNAT      │  │ localmente   │
    │  (SOAP)     │  │              │
    └─────┬───────┘  └──────────────┘
          │
          ▼
    ┌──────────────────────┐
    │  Recibir CDR         │
    │  (Comprobante de     │
    │   Recepción)         │
    └──────────────────────┘
```

---

## 🔐 SEGURIDAD

### Encriptación:
- Contraseña SOL encriptada en reposo
- Certificados almacenados en directorio protegido
- Claves privadas nunca se transmiten

### Validaciones:
- Certificados verificados antes de usar
- Validación de datos de entrada
- Alertas de vencimiento de certificados

### Cumplimiento:
- Cumple estándar UBL 2.1 internacional
- Sigue especificaciones SUNAT
- XmlDsig según W3C

---

## 📝 ESTRUCTURA DE ARCHIVOS

```
VISO_DIR/
├── usuario1/
│   └── data/
│       └── sunat/
│           ├── config_sunat.json          # Configuración principal
│           ├── registro_certificados.json # Registro de certs
│           ├── certificados/
│           │   ├── cert_TIMESTAMP.pem    # Certificados
│           │   ├── key_TIMESTAMP.key     # Claves privadas
│           │   └── registro_certificados.json
│           └── comprobantes/
│               ├── 202401/
│               │   ├── B00100001.xml           # Boleta firmada
│               │   ├── B00100001_CDR.xml      # Recibido de SUNAT
│               │   └── B00100001_sin_firmar.xml
│               └── 202402/
└── ...
```

---

## ⚠️ CONSIDERACIONES IMPORTANTES

### Requisitos del Usuario:
1. ✅ RUC activo en SUNAT
2. ✅ Habilitación como Emisor Electrónico
3. ✅ Certificado digital vigente
4. ✅ Usuario y contraseña SOL

### Límites:
- Máximo 300 comprobantes/día (límite SUNAT)
- Certificados válidos por 1 año
- Almacenamiento local de CDRs (~5MB por año)

### Errores Comunes:
- **"Certificado no válido"**: Verificar vigencia
- **"Credenciales incorrectas"**: Validar usuario/contraseña SOL
- **"Usuario no autorizado"**: Solicitar habilitación a SUNAT
- **"Error de conexión"**: Verificar conexión a internet

---

## 🚀 PRÓXIMAS MEJORAS OPCIONALES

1. **Consulta de saldo de comprobantes** en SUNAT
2. **Resumen de envíos** diarios
3. **Búsqueda de boletas** por período
4. **Descarga automática** de CDRs
5. **Integración con PLE** (Libro Electrónico)
6. **Notificaciones** de errores
7. **Reportes** de emisión

---

## 📞 CONTACTO SUNAT

- **Portal**: https://www.sunat.gob.pe
- **Sistema**: https://www.sunat.gob.pe/ol-ti-itcpfegem/olconsultaruc
- **Soporte**: 0800-01500 (opción 2, luego 2)

---

## 📄 DOCUMENTACIÓN TÉCNICA

- [Estándar UBL 2.1](https://oasis-open.github.io/ubl-oas/index.html)
- [XmlDsig W3C](https://www.w3.org/TR/xmldsig-core/)
- [API SUNAT](https://www.sunat.gob.pe/wsServicios/index.html)
- [Especificaciones SUNAT](https://www.sunat.gob.pe/doc)

---

**Última actualización**: 23 de Enero de 2026
**Versión de VISO**: 4.2.4
**Estado**: ✅ COMPLETO Y FUNCIONAL
