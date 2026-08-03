<?php
/**
 * GET_INVENTARIO.PHP
 * 
 * Obtiene el INVENTARIO/STOCK de productos de un usuario.
 * 
 * Parámetros:
 * - usuario_id: ID del usuario
 * - codigo_producto: (Opcional) Código del producto específico
 */

error_reporting(E_ALL);
ini_set('display_errors', '0');
ini_set('log_errors', '1');

header('Content-Type: application/json; charset=utf-8');

function has_column($conn, $table, $column) {
    $table_safe = mysqli_real_escape_string($conn, $table);
    $column_safe = mysqli_real_escape_string($conn, $column);
    $sql = "SELECT 1
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = '$table_safe'
              AND COLUMN_NAME = '$column_safe'
            LIMIT 1";
    $res = @mysqli_query($conn, $sql);
    return ($res && mysqli_num_rows($res) > 0);
}

try {
    $usuario_id = isset($_GET['usuario_id']) ? $_GET['usuario_id'] : null;
    $codigo_producto = isset($_GET['codigo_producto']) ? $_GET['codigo_producto'] : null;
    $codigo_dispositivo = strtoupper(trim((string)($_GET['codigo_dispositivo'] ?? '')));
    
    if (!$usuario_id) {
        echo json_encode(['success' => false, 'error' => 'Falta parámetro usuario_id']);
        exit;
    }
    
    $conn = mysqli_connect('localhost', 'u369606320_visoo', getenv('VISO_DB_PASSWORD'), 'u369606320_visoo');
    
    if (!$conn) {
        echo json_encode(['success' => false, 'error' => 'Conexión BD: ' . mysqli_connect_error()]);
        exit;
    }
    
    mysqli_set_charset($conn, 'utf8mb4');
    $has_codigo = has_column($conn, 'productos', 'codigo_dispositivo');
    
    // ============================================================================
    // CREAR TABLA DE PRODUCTOS SI NO EXISTE
    // ============================================================================
    // NOTA: NO hacer DROP TABLE - causaba ciclo infinito de borrado/re-carga
    // La tabla se creará solo si NO existe (CREATE TABLE IF NOT EXISTS)
    
    $create_table_query = "CREATE TABLE IF NOT EXISTS `productos` (
        `id` INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
        `id_usuario` VARCHAR(50) NOT NULL,
        `codigo` VARCHAR(100) NOT NULL UNIQUE,
        `nombre` VARCHAR(255) NOT NULL,
        `marca` VARCHAR(100),
        `categoria` VARCHAR(100),
        `material` VARCHAR(100),
        `colors` VARCHAR(255),
        `talla` VARCHAR(50),
        `tipo_lente` VARCHAR(100),
        `stock` INT(11) DEFAULT 0,
        `costo` DECIMAL(10, 2) DEFAULT 0.00,
        `venta` DECIMAL(10, 2) DEFAULT 0.00,
        `precio_regular` DECIMAL(10, 2) DEFAULT 0.00,
        `caracteristicas_polarizado` BOOLEAN DEFAULT FALSE,
        `caracteristicas_uv` BOOLEAN DEFAULT FALSE,
        `caracteristicas_antireflejo` BOOLEAN DEFAULT FALSE,
        `caracteristicas_fotocromatico` BOOLEAN DEFAULT FALSE,
        `caracteristicas_blue_light` BOOLEAN DEFAULT FALSE,
        `codigo_dispositivo` VARCHAR(80) DEFAULT NULL,
        `dispositivo_nombre` VARCHAR(255) DEFAULT NULL,
        `tipo_dispositivo` VARCHAR(20) DEFAULT 'madre',
        `created_at` DATETIME,
        `fecha_registro` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        `fecha_actualizacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        
        KEY `idx_usuario` (`id_usuario`),
        KEY `idx_codigo` (`codigo`),
        KEY `idx_nombre` (`nombre`),
        KEY `idx_categoria` (`categoria`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";
    
    if (!mysqli_query($conn, $create_table_query)) {
        if (strpos(mysqli_error($conn), 'already exists') === false) {
            error_log("Warning: Could not create productos table: " . mysqli_error($conn));
        }
    }
    $has_codigo = has_column($conn, 'productos', 'codigo_dispositivo');
    
    // Escapar usuario_id después de conectar
    if (is_numeric($usuario_id)) {
        $usuario_id_escaped = intval($usuario_id);
        $usuario_id_sql = $usuario_id_escaped;
    } else {
        $usuario_id_escaped = mysqli_real_escape_string($conn, $usuario_id);
        $usuario_id_sql = "'$usuario_id_escaped'";
    }
    
    // ============================================================================
    // OBTENER INVENTARIO DEL USUARIO (O DE UN PRODUCTO ESPECÍFICO)
    // ============================================================================
    $select_fields = "codigo, nombre, stock, costo, venta, precio_regular, 
                          categoria, created_at, fecha_actualizacion";
    if ($has_codigo) {
        $select_fields .= ", codigo_dispositivo";
    }
    $base_query = "SELECT $select_fields
                   FROM productos 
                   WHERE id_usuario=$usuario_id_sql";
    
    if ($codigo_producto) {
        $codigo_escaped = mysqli_real_escape_string($conn, $codigo_producto);
        $base_query .= " AND codigo='$codigo_escaped'";
    }
    if ($codigo_dispositivo !== '' && $has_codigo) {
        $codigo_disp_esc = mysqli_real_escape_string($conn, $codigo_dispositivo);
        $base_query .= " AND codigo_dispositivo='$codigo_disp_esc'";
    }
    
    $base_query .= " ORDER BY categoria ASC, nombre ASC";
    
    $result = mysqli_query($conn, $base_query);
    
    if (!$result) {
        echo json_encode(['success' => false, 'error' => 'Query error: ' . mysqli_error($conn)]);
        mysqli_close($conn);
        exit;
    }
    
    $inventario = [];
    $stock_total = 0;
    $valor_total = 0;
    
    while ($row = mysqli_fetch_assoc($result)) {
        $stock = intval($row['stock']);
        $costo = floatval($row['costo']);
        $venta = floatval($row['venta']);
        $valor_inventario = $stock * $costo;
        
        $stock_total += $stock;
        $valor_total += $valor_inventario;
        
        $inventario[] = [
            'codigo' => $row['codigo'],
            'nombre' => $row['nombre'],
            'stock' => $stock,
            'costo_unitario' => $costo,
            'venta_unitario' => $venta,
            'precio_regular' => floatval($row['precio_regular']),
            'valor_inventario' => $valor_inventario,
            'margen' => $venta > 0 ? round((($venta - $costo) / $venta) * 100, 2) : 0,
            'categoria' => $row['categoria'],
            'created_at' => $row['created_at'],
            'fecha_actualizacion' => $row['fecha_actualizacion'],
            'codigo_dispositivo' => $has_codigo ? ($row['codigo_dispositivo'] ?? '') : ''
        ];
    }
    
    mysqli_close($conn);
    
    // ============================================================================
    // RETORNAR RESPUESTA
    // ============================================================================
    echo json_encode([
        'success' => true,
        'usuario_id' => $usuario_id,
        'codigo_producto' => $codigo_producto ?: null,
        'inventario' => $inventario,
        'total_items' => count($inventario),
        'stock_total' => $stock_total,
        'valor_total_inventario' => round($valor_total, 2)
    ]);
    
} catch (Exception $e) {
    echo json_encode(['success' => false, 'error' => 'Exception: ' . $e->getMessage()]);
}

exit;
?>
