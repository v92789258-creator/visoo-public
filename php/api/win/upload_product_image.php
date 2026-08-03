<?php
/**
 * API: Subir imagen de producto
 * POST /api/win/upload_product_image.php
 * 
 * Recibe una imagen y la guarda en el servidor junto al producto.
 * 
 * Parámetros:
 * - usuario_id (POST): ID del usuario
 * - codigo_producto (POST): Código único del producto
 * - imagen (FILE): Archivo de imagen (JPG, PNG)
 * 
 * Respuesta:
 * {
 *   "success": true,
 *   "message": "Imagen subida correctamente",
 *   "imagen_url": "https://api.yhana.cloud/uploads/productos/codigo_123.jpg",
 *   "codigo_producto": "codigo_123"
 * }
 */

error_reporting(E_ALL);
ini_set('display_errors', '0');
ini_set('log_errors', '1');

header('Content-Type: application/json; charset=utf-8');

// ============================================================================
// Validar parámetros requeridos
// ============================================================================

if (!isset($_POST['usuario_id']) || !isset($_POST['codigo_producto'])) {
    http_response_code(400);
    echo json_encode([
        'success' => false,
        'message' => 'Parámetros incompletos (usuario_id, codigo_producto requeridos)'
    ]);
    exit;
}

if (!isset($_FILES['imagen'])) {
    http_response_code(400);
    echo json_encode([
        'success' => false,
        'message' => 'No se recibió archivo de imagen'
    ]);
    exit;
}

$usuario_id = intval($_POST['usuario_id']);
$codigo_producto = sanitize_filename($_POST['codigo_producto']);
$imagen_file = $_FILES['imagen'];

if ($usuario_id <= 0) {
    http_response_code(400);
    echo json_encode([
        'success' => false,
        'message' => 'usuario_id inválido'
    ]);
    exit;
}

// ============================================================================
// Validar imagen
// ============================================================================

$allowed_mimes = ['image/jpeg', 'image/png', 'image/webp'];
$max_size = 5 * 1024 * 1024; // 5MB

if (!in_array($imagen_file['type'], $allowed_mimes)) {
    http_response_code(400);
    echo json_encode([
        'success' => false,
        'message' => 'Tipo de archivo no permitido. Solo JPG, PNG, WebP'
    ]);
    exit;
}

if ($imagen_file['size'] > $max_size) {
    http_response_code(400);
    echo json_encode([
        'success' => false,
        'message' => 'Archivo demasiado grande (máximo 5MB)'
    ]);
    exit;
}

if ($imagen_file['error'] !== UPLOAD_ERR_OK) {
    http_response_code(400);
    echo json_encode([
        'success' => false,
        'message' => 'Error al subir archivo: ' . $imagen_file['error']
    ]);
    exit;
}

// ============================================================================
// Crear directorios y guardar imagen
// ============================================================================

try {
    // Crear estructura de carpetas: /uploads/productos/usuario_id/
    $upload_dir = "../../uploads/productos/{$usuario_id}/";
    
    if (!is_dir($upload_dir)) {
        if (!mkdir($upload_dir, 0755, true)) {
            throw new Exception("No se pudo crear directorio de uploads");
        }
    }
    
    // Generar nombre de archivo único: codigo_producto.ext
    $ext = strtolower(pathinfo($imagen_file['name'], PATHINFO_EXTENSION));
    $filename = sanitize_filename($codigo_producto) . '.' . $ext;
    $filepath = $upload_dir . $filename;
    
    // Mover archivo subido
    if (!move_uploaded_file($imagen_file['tmp_name'], $filepath)) {
        throw new Exception("Error al guardar archivo");
    }
    
    // ========================================================================
    // Conectar a BD y guardar referencia
    // ========================================================================
    
    $conn = mysqli_connect('localhost', 'u369606320_visoo', getenv('VISO_DB_PASSWORD'), 'u369606320_visoo');
    
    if (!$conn) {
        throw new Exception("Conexión BD fallida: " . mysqli_connect_error());
    }
    
    mysqli_set_charset($conn, 'utf8mb4');
    
    // ========================================================================
    // CREAR TABLA DE IMÁGENES SI NO EXISTE
    // ========================================================================
    
    $create_table_query = "CREATE TABLE IF NOT EXISTS `producto_imagenes` (
        `id` INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
        `usuario_id` VARCHAR(50) NOT NULL,
        `codigo_producto` VARCHAR(100) NOT NULL,
        `imagen_url` VARCHAR(500) NOT NULL,
        `fecha_subida` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY `unique_producto_imagen` (`usuario_id`, `codigo_producto`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";
    
    if (!mysqli_query($conn, $create_table_query)) {
        throw new Exception("Error creando tabla: " . mysqli_error($conn));
    }
    
    // ========================================================================
    // GUARDAR/ACTUALIZAR REFERENCIA EN BD
    // ========================================================================
    
    $imagen_url = "https://api.yhana.cloud/uploads/productos/{$usuario_id}/{$filename}";
    
    // Usar INSERT...ON DUPLICATE KEY UPDATE para UPSERT
    $insert_query = "INSERT INTO `producto_imagenes` 
        (`usuario_id`, `codigo_producto`, `imagen_url`, `fecha_subida`)
    VALUES 
        ('" . mysqli_real_escape_string($conn, $usuario_id) . "',
         '" . mysqli_real_escape_string($conn, $codigo_producto) . "',
         '" . mysqli_real_escape_string($conn, $imagen_url) . "',
         NOW())
    ON DUPLICATE KEY UPDATE 
        `imagen_url` = VALUES(`imagen_url`),
        `fecha_subida` = NOW()";
    
    if (!mysqli_query($conn, $insert_query)) {
        throw new Exception("Error guardando referencia: " . mysqli_error($conn));
    }
    
    // ========================================================================
    // Respuesta de éxito
    // ========================================================================
    
    http_response_code(200);
    echo json_encode([
        'success' => true,
        'message' => 'Imagen subida correctamente',
        'imagen_url' => $imagen_url,
        'codigo_producto' => $codigo_producto,
        'fecha_subida' => date('Y-m-d H:i:s')
    ]);
    
    mysqli_close($conn);
    
} catch (Exception $e) {
    error_log("[UPLOAD] Error subiendo imagen: " . $e->getMessage());
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => 'Error del servidor: ' . $e->getMessage()
    ]);
}

// ============================================================================
// Funciones auxiliares
// ============================================================================

function sanitize_filename($filename) {
    // Remover caracteres especiales, mantener solo alphanumericos y guiones
    $filename = preg_replace('/[^a-zA-Z0-9_\-]/', '_', $filename);
    // Remover múltiples guiones/guiones bajos consecutivos
    $filename = preg_replace('/[_\-]{2,}/', '_', $filename);
    return $filename;
}

?>
