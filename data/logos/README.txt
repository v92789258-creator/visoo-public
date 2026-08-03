LOGOS DE LA EMPRESA
===================

Este directorio contiene los logos que se utilizan en las boletas/facturas del sistema VISO.

INSTRUCCIONES:
==============

1. Coloca tu logo de la empresa aquí con el nombre: logo_empresa.png

2. Requisitos del logo:
   - Formato: PNG (con fondo transparente preferiblemente)
   - Ancho recomendado: 300-500 pixels
   - Alto recomendado: 150-250 pixels (proporción 2:1)
   - Tamaño del archivo: menos de 500 KB
   - Se recomienda un logo horizontal (landscape)

3. El sistema buscará el logo en los siguientes lugares (en orden de prioridad):
   - data/logos/logo_empresa.png (esta carpeta)
   - data/logo_empresa.png
   - logo_empresa.png (raíz del proyecto)

4. Una vez coloques el logo aquí, aparecerá automáticamente en:
   - Boletas de pequeño formato (80mm de ancho)
   - Boletas de formato largo (80mm de ancho)
   - Boletas de formato extra largo (80mm de ancho)
   - Todas las plantillas de impresión térmica

5. Si no hay logo, el sistema mostrará un placeholder visual como respaldo.

NOTA IMPORTANTE:
================
El logo se insertará SIEMPRE en todas las boletas generadas.
Posición: Centrado en la parte superior de la boleta
Tamaño: Automáticamente ajustado a 30mm de ancho (en PDF)
