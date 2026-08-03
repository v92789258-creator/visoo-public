// FastJSONLoader.cpp
// Cargador ultra-rápido de archivos JSON compilado en C++
// Se puede llamar desde Python usando ctypes

#include <fstream>
#include <string>
#include <vector>
#include <map>
#include <cstring>
#include <cstdlib>

#ifdef _WIN32
    #define EXPORT __declspec(dllexport)
#else
    #define EXPORT
#endif

// Estructura simple para datos en caché
struct CacheEntry {
    char* data;
    size_t size;
    unsigned long file_mtime;
};

// Caché global thread-safe (simplificado)
static std::map<std::string, CacheEntry> g_cache;

/**
 * Obtiene el timestamp modificación de un archivo
 */
extern "C" EXPORT unsigned long GetFileModTime(const char* filename)
{
    try {
        std::ifstream file(filename, std::ios::binary | std::ios::ate);
        if (!file.is_open()) {
            return 0;
        }
        file.close();
        
        // Obtener mtime - plataforma específica
        #ifdef _WIN32
            struct _stat64 file_stat;
            if (_stat64(filename, &file_stat) == 0) {
                return (unsigned long)file_stat.st_mtime;
            }
        #else
            struct stat file_stat;
            if (stat(filename, &file_stat) == 0) {
                return (unsigned long)file_stat.st_mtime;
            }
        #endif
        
        return 0;
    }
    catch (...) {
        return 0;
    }
}

/**
 * Lee un archivo JSON y lo retorna como string
 * Parámetro output_size: se llena con el tamaño del contenido
 * Retorna: puntero a memoria que DEBE ser liberada con FreeMemory()
 */
extern "C" EXPORT char* LoadJSONFile(const char* filename, unsigned long* output_size)
{
    try {
        // Obtener mtime actual
        unsigned long current_mtime = GetFileModTime(filename);
        
        // Verificar caché
        auto it = g_cache.find(filename);
        if (it != g_cache.end()) {
            if (it->second.file_mtime == current_mtime && it->second.data != nullptr) {
                // Caché válido
                *output_size = it->second.size;
                
                // Copiar datos a memoria nuevo (el llamador es responsable de liberar)
                char* result = (char*)malloc(it->second.size + 1);
                if (result) {
                    std::memcpy(result, it->second.data, it->second.size);
                    result[it->second.size] = '\0';
                }
                return result;
            }
        }
        
        // Leer archivo
        std::ifstream file(filename, std::ios::binary | std::ios::ate);
        if (!file.is_open()) {
            *output_size = 0;
            return nullptr;
        }
        
        // Obtener tamaño
        std::streamsize size = file.tellg();
        file.seekg(0, std::ios::beg);
        
        // Leer contenido
        char* buffer = (char*)malloc(size + 1);
        if (!buffer) {
            *output_size = 0;
            return nullptr;
        }
        
        if (!file.read(buffer, size)) {
            free(buffer);
            *output_size = 0;
            return nullptr;
        }
        
        buffer[size] = '\0';
        file.close();
        
        // Actualizar caché
        // Liberar entrada anterior si existe
        if (it != g_cache.end() && it->second.data != nullptr) {
            free(it->second.data);
        }
        
        // Almacenar en caché
        CacheEntry entry;
        entry.data = (char*)malloc(size + 1);
        if (entry.data) {
            std::memcpy(entry.data, buffer, size);
            entry.data[size] = '\0';
            entry.size = size;
            entry.file_mtime = current_mtime;
            g_cache[filename] = entry;
        }
        
        *output_size = size;
        return buffer;
    }
    catch (...) {
        *output_size = 0;
        return nullptr;
    }
}

/**
 * Lee un archivo JSON y lo retorna como string (versión alternativa)
 * Mismo que LoadJSONFile pero más simple de usar
 */
extern "C" EXPORT const char* LoadJSONFileSimple(const char* filename)
{
    try {
        // Obtener mtime actual
        unsigned long current_mtime = GetFileModTime(filename);
        
        // Verificar caché
        auto it = g_cache.find(filename);
        if (it != g_cache.end()) {
            if (it->second.file_mtime == current_mtime && it->second.data != nullptr) {
                // Caché válido - retornar directamente (no copiar)
                return it->second.data;
            }
        }
        
        // Leer archivo
        std::ifstream file(filename, std::ios::binary | std::ios::ate);
        if (!file.is_open()) {
            return nullptr;
        }
        
        // Obtener tamaño
        std::streamsize size = file.tellg();
        file.seekg(0, std::ios::beg);
        
        // Leer contenido
        char* buffer = (char*)malloc(size + 1);
        if (!buffer) {
            return nullptr;
        }
        
        if (!file.read(buffer, size)) {
            free(buffer);
            return nullptr;
        }
        
        buffer[size] = '\0';
        file.close();
        
        // Actualizar caché
        if (it != g_cache.end() && it->second.data != nullptr) {
            free(it->second.data);
        }
        
        // Almacenar en caché
        CacheEntry entry;
        entry.data = buffer;
        entry.size = size;
        entry.file_mtime = current_mtime;
        g_cache[filename] = entry;
        
        return buffer;
    }
    catch (...) {
        return nullptr;
    }
}

/**
 * Guarda un string JSON a un archivo
 */
extern "C" EXPORT int SaveJSONFile(const char* filename, const char* json_content, unsigned long content_size)
{
    try {
        std::ofstream file(filename, std::ios::binary);
        if (!file.is_open()) {
            return 0;  // Error
        }
        
        file.write(json_content, content_size);
        file.close();
        
        // Invalidar caché para este archivo
        auto it = g_cache.find(filename);
        if (it != g_cache.end() && it->second.data != nullptr) {
            free(it->second.data);
            g_cache.erase(it);
        }
        
        return 1;  // Éxito
    }
    catch (...) {
        return 0;  // Error
    }
}

/**
 * Libera memoria asignada por LoadJSONFile
 */
extern "C" EXPORT void FreeMemory(void* ptr)
{
    if (ptr != nullptr) {
        free(ptr);
    }
}

/**
 * Limpia el caché completamente
 */
extern "C" EXPORT void ClearCache()
{
    for (auto& entry : g_cache) {
        if (entry.second.data != nullptr) {
            free(entry.second.data);
        }
    }
    g_cache.clear();
}

/**
 * Retorna el número de entradas en el caché
 */
extern "C" EXPORT int GetCacheSize()
{
    return (int)g_cache.size();
}

/**
 * Obtiene estadísticas del caché
 * Formato: "item1_size:item1_mtime;item2_size:item2_mtime;..."
 */
extern "C" EXPORT const char* GetCacheStats()
{
    static std::string stats;
    stats.clear();
    
    for (const auto& entry : g_cache) {
        if (!stats.empty()) {
            stats += ";";
        }
        stats += entry.first + ":" + std::to_string(entry.second.size);
    }
    
    return stats.c_str();
}
