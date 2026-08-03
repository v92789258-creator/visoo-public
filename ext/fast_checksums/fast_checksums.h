#ifndef FAST_CHECKSUMS_H
#define FAST_CHECKSUMS_H

#include <map>
#include <string>

// fast_checksums.h
// Declaración de funciones para el módulo nativo `fast_checksums`.
// Proporciona utilidades rápidas relacionadas con checksums de archivos.

namespace fast_checksums {
    // Recorre recursivamente `path` y devuelve un map de ruta_relativa -> sha256_hex
    // Lanzará std::runtime_error si `path` no existe o no es un directorio.
    std::map<std::string, std::string> directory_checksums(const std::string& path);
}

#endif // FAST_CHECKSUMS_H
