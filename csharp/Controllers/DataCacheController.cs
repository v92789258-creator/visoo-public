using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using VISO.Services;

namespace VISO.Controllers
{
    /// <summary>
    /// API REST para acceso optimizado a datos desde Python.
    /// Todas las operaciones están cacheadas en memoria.
    /// </summary>
    [ApiController]
    [Route("api/data")]
    public class DataCacheController : ControllerBase
    {
        private static readonly Lazy<FastDataCache> _cache = 
            new Lazy<FastDataCache>(() => new FastDataCache());

        public static FastDataCache Cache => _cache.Value;

        /// <summary>
        /// Búsqueda de pacientes por término (DNI, nombre, apellido, email).
        /// Tiempo de respuesta: &lt;50ms típicamente.
        /// </summary>
        /// <param name="term">Término de búsqueda</param>
        /// <returns>Lista de pacientes encontrados</returns>
        [HttpGet("search/patients")]
        public async Task<IActionResult> SearchPatients([FromQuery] string term)
        {
            if (string.IsNullOrWhiteSpace(term))
                return BadRequest("El término de búsqueda no puede estar vacío");

            try
            {
                var result = await Cache.SearchPatientsAsync(term);
                return Ok(new
                {
                    success = true,
                    count = result.Patients.Count,
                    executionTimeMs = result.ExecutionTimeMs,
                    patients = result.Patients
                });
            }
            catch (Exception ex)
            {
                return StatusCode(500, new { success = false, error = ex.Message });
            }
        }

        /// <summary>
        /// Búsqueda de productos por término y categoría.
        /// Tiempo de respuesta: &lt;30ms típicamente.
        /// </summary>
        [HttpGet("search/products")]
        public async Task<IActionResult> SearchProducts(
            [FromQuery] string term,
            [FromQuery] string category = null)
        {
            if (string.IsNullOrWhiteSpace(term) && string.IsNullOrWhiteSpace(category))
                return BadRequest("Se requiere término o categoría");

            try
            {
                var result = await Cache.SearchProductsAsync(term, category);
                return Ok(new
                {
                    success = true,
                    count = result.Products.Count,
                    executionTimeMs = result.ExecutionTimeMs,
                    products = result.Products
                });
            }
            catch (Exception ex)
            {
                return StatusCode(500, new { success = false, error = ex.Message });
            }
        }

        /// <summary>
        /// Búsqueda general en pacientes y productos.
        /// Tiempo de respuesta: &lt;100ms típicamente.
        /// </summary>
        [HttpGet("search/all")]
        public async Task<IActionResult> SearchAll([FromQuery] string term)
        {
            if (string.IsNullOrWhiteSpace(term))
                return BadRequest("El término de búsqueda no puede estar vacío");

            try
            {
                var result = await Cache.SearchAllAsync(term);
                return Ok(new
                {
                    success = true,
                    patientsFound = result.Patients.Count,
                    productsFound = result.Products.Count,
                    executionTimeMs = result.ExecutionTimeMs,
                    patients = result.Patients,
                    products = result.Products
                });
            }
            catch (Exception ex)
            {
                return StatusCode(500, new { success = false, error = ex.Message });
            }
        }

        /// <summary>
        /// Carga datos JSON especificados en caché.
        /// Retorna inmediatamente de caché en futuras llamadas.
        /// </summary>
        [HttpPost("load")]
        public async Task<IActionResult> LoadData([FromBody] LoadRequest request)
        {
            if (string.IsNullOrWhiteSpace(request?.Filename))
                return BadRequest("El nombre del archivo es requerido");

            try
            {
                // Forzar caché
                var result = await Cache.LoadJsonAsync<object>(request.Filename);
                return Ok(new
                {
                    success = true,
                    message = "Datos cargados en caché",
                    filename = request.Filename
                });
            }
            catch (Exception ex)
            {
                return StatusCode(500, new { success = false, error = ex.Message });
            }
        }

        /// <summary>
        /// Obtiene estadísticas del caché.
        /// </summary>
        [HttpGet("cache-stats")]
        public IActionResult GetCacheStats()
        {
            var stats = Cache.GetStats();
            return Ok(new
            {
                success = true,
                totalCachedItems = stats.TotalCachedItems,
                totalIndexedItems = stats.TotalIndexedItems,
                cacheEntries = stats.CacheEntries
            });
        }

        /// <summary>
        /// Limpia el caché expirado (default: &gt;60 minutos).
        /// </summary>
        [HttpPost("cache-cleanup")]
        public IActionResult CleanupCache([FromBody] CleanupRequest request = null)
        {
            var maxAgeMinutes = request?.MaxAgeMinutes ?? 60;
            Cache.ClearExpiredCache(maxAgeMinutes);
            return Ok(new { success = true, message = "Caché limpiado" });
        }

        /// <summary>
        /// Limpia todo el caché.
        /// </summary>
        [HttpPost("cache-clear")]
        public IActionResult ClearCache()
        {
            Cache.ClearCache();
            return Ok(new { success = true, message = "Caché completamente limpiado" });
        }
    }

    public class LoadRequest
    {
        public string Filename { get; set; }
    }

    public class CleanupRequest
    {
        public int MaxAgeMinutes { get; set; } = 60;
    }
}
