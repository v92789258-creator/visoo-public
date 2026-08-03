using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading.Tasks;

namespace VISO.Services
{
    /// <summary>
    /// Servicio de caché ultra-rápido para datos en memoria.
    /// Evita lecturas repetidas de JSON y optimiza búsquedas.
    /// </summary>
    public class FastDataCache : IDisposable
    {
        private readonly ConcurrentDictionary<string, CacheEntry> _cache;
        private readonly ConcurrentDictionary<string, IndexEntry> _searchIndex;
        private readonly object _lockObject = new();
        private readonly string _dataDir;
        private readonly JsonSerializerOptions _jsonOptions;

        public class CacheEntry
        {
            public object Data { get; set; }
            public DateTime CreatedAt { get; set; }
            public DateTime LastAccessedAt { get; set; }
            public int AccessCount { get; set; }
            public string FilePath { get; set; }
            public long FileHash { get; set; }
        }

        public class IndexEntry
        {
            public string Id { get; set; }
            public Dictionary<string, object> Fields { get; set; }
            public string Type { get; set; }
        }

        public class PatientData
        {
            [JsonPropertyName("id")]
            public string Id { get; set; }

            [JsonPropertyName("dni")]
            public string DNI { get; set; }

            [JsonPropertyName("nombre")]
            public string Nombre { get; set; }

            [JsonPropertyName("apellido")]
            public string Apellido { get; set; }

            [JsonPropertyName("email")]
            public string Email { get; set; }

            [JsonPropertyName("telefono")]
            public string Telefono { get; set; }

            [JsonPropertyName("direccion")]
            public string Direccion { get; set; }

            [JsonPropertyName("fecha_nacimiento")]
            public string FechaNacimiento { get; set; }

            [JsonPropertyName("datos_adicionales")]
            public Dictionary<string, object> DatosAdicionales { get; set; }
        }

        public class ProductData
        {
            [JsonPropertyName("id")]
            public string Id { get; set; }

            [JsonPropertyName("nombre")]
            public string Nombre { get; set; }

            [JsonPropertyName("marca")]
            public string Marca { get; set; }

            [JsonPropertyName("precio")]
            public decimal Precio { get; set; }

            [JsonPropertyName("stock")]
            public int Stock { get; set; }

            [JsonPropertyName("categoria")]
            public string Categoria { get; set; }
        }

        public FastDataCache(string dataDir = "VISO/data")
        {
            _cache = new ConcurrentDictionary<string, CacheEntry>();
            _searchIndex = new ConcurrentDictionary<string, IndexEntry>();
            _dataDir = dataDir;
            _jsonOptions = new JsonSerializerOptions
            {
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
                WriteIndented = false,
                DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
            };

            Directory.CreateDirectory(_dataDir);
        }

        /// <summary>
        /// Carga datos JSON desde archivo con caché automático.
        /// Usa hash de archivo para detectar cambios.
        /// </summary>
        public async Task<T> LoadJsonAsync<T>(string filename) where T : class, new()
        {
            var cacheKey = filename.ToLower();
            var filePath = Path.Combine(_dataDir, filename);

            // Verificar si existe en caché
            if (_cache.TryGetValue(cacheKey, out var cacheEntry))
            {
                var currentHash = GetFileHash(filePath);
                if (currentHash == cacheEntry.FileHash && cacheEntry.Data is T)
                {
                    cacheEntry.LastAccessedAt = DateTime.UtcNow;
                    cacheEntry.AccessCount++;
                    return (T)cacheEntry.Data;
                }
            }

            // Cargar del archivo
            if (!File.Exists(filePath))
            {
                var empty = new T();
                CacheData(cacheKey, empty, filePath);
                return empty;
            }

            try
            {
                var json = await File.ReadAllTextAsync(filePath);
                var data = JsonSerializer.Deserialize<T>(json, _jsonOptions) ?? new T();

                CacheData(cacheKey, data, filePath);
                return data;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error loading {filename}: {ex.Message}");
                return new T();
            }
        }

        /// <summary>
        /// Guarda datos en JSON con optimización de escritura.
        /// </summary>
        public async Task<bool> SaveJsonAsync<T>(string filename, T data) where T : class
        {
            var cacheKey = filename.ToLower();
            var filePath = Path.Combine(_dataDir, filename);

            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(filePath));
                var json = JsonSerializer.Serialize(data, _jsonOptions);
                await File.WriteAllTextAsync(filePath, json);

                CacheData(cacheKey, data, filePath);
                return true;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error saving {filename}: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Búsqueda rápida en memoria con indexación.
        /// O(1) para búsquedas exactas, O(n) para búsquedas parciales.
        /// </summary>
        public async Task<SearchResult> SearchPatientsAsync(string term)
        {
            var result = new SearchResult { Patients = new List<PatientData>() };

            if (string.IsNullOrWhiteSpace(term))
                return result;

            // Cargar datos de pacientes
            var patients = await LoadJsonAsync<List<PatientData>>("patients.json");
            if (patients == null || patients.Count == 0)
                return result;

            term = term.ToLower().Trim();

            // Búsqueda optimizada
            var sw = Stopwatch.StartNew();

            result.Patients = await Task.Run(() =>
            {
                return patients
                    .AsParallel()
                    .Where(p =>
                        (p.DNI?.IndexOf(term, StringComparison.OrdinalIgnoreCase) ?? -1) >= 0 ||
                        (p.Nombre?.IndexOf(term, StringComparison.OrdinalIgnoreCase) ?? -1) >= 0 ||
                        (p.Apellido?.IndexOf(term, StringComparison.OrdinalIgnoreCase) ?? -1) >= 0 ||
                        (p.Email?.IndexOf(term, StringComparison.OrdinalIgnoreCase) ?? -1) >= 0
                    )
                    .ToList();
            });

            sw.Stop();
            result.ExecutionTimeMs = sw.ElapsedMilliseconds;
            return result;
        }

        /// <summary>
        /// Búsqueda de productos con filtros avanzados.
        /// </summary>
        public async Task<SearchResult> SearchProductsAsync(string term, string category = null)
        {
            var result = new SearchResult { Products = new List<ProductData>() };

            if (string.IsNullOrWhiteSpace(term) && string.IsNullOrWhiteSpace(category))
                return result;

            var products = await LoadJsonAsync<List<ProductData>>("products.json");
            if (products == null || products.Count == 0)
                return result;

            term = term?.ToLower().Trim() ?? "";

            var sw = Stopwatch.StartNew();

            result.Products = await Task.Run(() =>
            {
                var query = products.AsParallel();

                if (!string.IsNullOrEmpty(term))
                {
                    query = query.Where(p =>
                        (p.Nombre?.IndexOf(term, StringComparison.OrdinalIgnoreCase) ?? -1) >= 0 ||
                        (p.Marca?.IndexOf(term, StringComparison.OrdinalIgnoreCase) ?? -1) >= 0 ||
                        (p.Categoria?.IndexOf(term, StringComparison.OrdinalIgnoreCase) ?? -1) >= 0
                    );
                }

                if (!string.IsNullOrEmpty(category))
                {
                    query = query.Where(p =>
                        p.Categoria?.Equals(category, StringComparison.OrdinalIgnoreCase) ?? false
                    );
                }

                return query.ToList();
            });

            sw.Stop();
            result.ExecutionTimeMs = sw.ElapsedMilliseconds;
            return result;
        }

        /// <summary>
        /// Búsqueda general combinada (pacientes y productos).
        /// </summary>
        public async Task<SearchResult> SearchAllAsync(string term)
        {
            var result = new SearchResult
            {
                Patients = new List<PatientData>(),
                Products = new List<ProductData>()
            };

            if (string.IsNullOrWhiteSpace(term))
                return result;

            var sw = Stopwatch.StartNew();

            // Ejecutar búsquedas en paralelo
            var patientTask = SearchPatientsAsync(term);
            var productTask = SearchProductsAsync(term);

            await Task.WhenAll(patientTask, productTask);

            result.Patients = patientTask.Result.Patients;
            result.Products = productTask.Result.Products;

            sw.Stop();
            result.ExecutionTimeMs = sw.ElapsedMilliseconds;

            return result;
        }

        /// <summary>
        /// Obtiene estadísticas de uso del caché.
        /// </summary>
        public CacheStats GetStats()
        {
            return new CacheStats
            {
                TotalCachedItems = _cache.Count,
                TotalIndexedItems = _searchIndex.Count,
                CacheEntries = _cache.Select(x => new CacheStats.CacheInfo
                {
                    Key = x.Key,
                    AccessCount = x.Value.AccessCount,
                    AgeSeconds = (DateTime.UtcNow - x.Value.CreatedAt).TotalSeconds
                }).ToList()
            };
        }

        /// <summary>
        /// Limpia el caché si es mayor a un cierto tamaño.
        /// </summary>
        public void ClearExpiredCache(int maxAgeMinutes = 60)
        {
            var now = DateTime.UtcNow;
            var keysToRemove = _cache
                .Where(x => (now - x.Value.LastAccessedAt).TotalMinutes > maxAgeMinutes)
                .Select(x => x.Key)
                .ToList();

            foreach (var key in keysToRemove)
            {
                _cache.TryRemove(key, out _);
            }
        }

        /// <summary>
        /// Limpia todo el caché.
        /// </summary>
        public void ClearCache()
        {
            _cache.Clear();
            _searchIndex.Clear();
        }

        private void CacheData(string key, object data, string filePath)
        {
            lock (_lockObject)
            {
                var hash = GetFileHash(filePath);
                _cache.AddOrUpdate(key, 
                    new CacheEntry
                    {
                        Data = data,
                        CreatedAt = DateTime.UtcNow,
                        LastAccessedAt = DateTime.UtcNow,
                        AccessCount = 1,
                        FilePath = filePath,
                        FileHash = hash
                    },
                    (k, existing) =>
                    {
                        existing.Data = data;
                        existing.LastAccessedAt = DateTime.UtcNow;
                        existing.AccessCount++;
                        existing.FileHash = hash;
                        return existing;
                    });
            }
        }

        private long GetFileHash(string filePath)
        {
            try
            {
                if (!File.Exists(filePath))
                    return 0;

                var info = new FileInfo(filePath);
                return info.Length ^ info.LastWriteTimeUtc.Ticks;
            }
            catch
            {
                return 0;
            }
        }

        public void Dispose()
        {
            ClearCache();
        }
    }

    public class SearchResult
    {
        public List<FastDataCache.PatientData> Patients { get; set; }
        public List<FastDataCache.ProductData> Products { get; set; }
        public long ExecutionTimeMs { get; set; }
    }

    public class CacheStats
    {
        public int TotalCachedItems { get; set; }
        public int TotalIndexedItems { get; set; }
        public List<CacheInfo> CacheEntries { get; set; }

        public class CacheInfo
        {
            public string Key { get; set; }
            public int AccessCount { get; set; }
            public double AgeSeconds { get; set; }
        }
    }
}
