#!/bin/bash
# Script de compilación automática de InventoryOptimizer para Linux/macOS
# Requisitos: GCC/Clang y CMake instalados

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "Compilando InventoryOptimizer (C++)"
echo "============================================"

# Crear directorio de compilación
mkdir -p build
cd build

# Ejecutar CMake
echo "Configurando proyecto con CMake..."
cmake .. -DCMAKE_BUILD_TYPE=Release

# Compilar
echo "Compilando..."
cmake --build . --config Release -j$(nproc)

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================"
    echo "✓ Compilación exitosa!"
    echo "============================================"
    echo "Librería generada en: $(pwd)/libInventoryOptimizer.so"
else
    echo ""
    echo "============================================"
    echo "✗ Error en la compilación"
    echo "============================================"
    exit 1
fi
