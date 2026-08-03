<?php
/**
 * sync_data_inv.php
 * Sincroniza productos/inventario y registra origen por dispositivo.
 */

error_reporting(E_ALL);
ini_set('display_errors', '0');
ini_set('log_errors', '1');
header('Content-Type: application/json; charset=utf-8');

function respond($payload) {
    echo json_encode($payload, JSON_UNESCAPED_UNICODE);
    exit;
}

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

function ensure_column($conn, $table, $column, $definition) {
    if (has_column($conn, $table, $column)) {
        return true;
    }

    $table_safe = mysqli_real_escape_string($conn, $table);
    $column_safe = mysqli_real_escape_string($conn, $column);
    $sql = "ALTER TABLE `$table_safe` ADD COLUMN `$column_safe` $definition";
    return @mysqli_query($conn, $sql);
}

function ensure_productos_table($conn) {
    $sql = "CREATE TABLE IF NOT EXISTS `productos` (
        `id` INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
        `id_usuario` VARCHAR(50) NOT NULL,
        `codigo` VARCHAR(100) NOT NULL,
        `nombre` VARCHAR(255) NOT NULL,
        `marca` VARCHAR(100),
        `categoria` VARCHAR(100),
        `material` VARCHAR(100),
        `colors` TEXT,
        `talla` VARCHAR(50),
        `tipo_lente` VARCHAR(100),
        `stock` INT(11) DEFAULT 0,
        `costo` DECIMAL(10,2) DEFAULT 0.00,
        `venta` DECIMAL(10,2) DEFAULT 0.00,
        `precio_regular` DECIMAL(10,2) DEFAULT 0.00,
        `caracteristicas_polarizado` TINYINT(1) DEFAULT 0,
        `caracteristicas_uv` TINYINT(1) DEFAULT 0,
        `caracteristicas_antireflejo` TINYINT(1) DEFAULT 0,
        `caracteristicas_fotocromatico` TINYINT(1) DEFAULT 0,
        `caracteristicas_blue_light` TINYINT(1) DEFAULT 0,
        `created_at` DATETIME,
        `codigo_dispositivo` VARCHAR(80) DEFAULT NULL,
        `dispositivo_nombre` VARCHAR(255) DEFAULT NULL,
        `tipo_dispositivo` VARCHAR(20) DEFAULT 'madre',
        `fecha_registro` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        `fecha_actualizacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY `uq_usuario_codigo` (`id_usuario`, `codigo`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";
    @mysqli_query($conn, $sql);

    ensure_column($conn, 'productos', 'caracteristicas_polarizado', "TINYINT(1) DEFAULT 0");
    ensure_column($conn, 'productos', 'caracteristicas_uv', "TINYINT(1) DEFAULT 0");
    ensure_column($conn, 'productos', 'caracteristicas_antireflejo', "TINYINT(1) DEFAULT 0");
    ensure_column($conn, 'productos', 'caracteristicas_fotocromatico', "TINYINT(1) DEFAULT 0");
    ensure_column($conn, 'productos', 'caracteristicas_blue_light', "TINYINT(1) DEFAULT 0");
    ensure_column($conn, 'productos', 'codigo_dispositivo', "VARCHAR(80) NULL");
    ensure_column($conn, 'productos', 'dispositivo_nombre', "VARCHAR(255) NULL");
    ensure_column($conn, 'productos', 'tipo_dispositivo', "VARCHAR(20) NULL DEFAULT 'madre'");
}

function resolve_photo_column($conn) {
    // Preferimos la columna canónica sin acentos.
    ensure_column($conn, 'productos', 'caracteristicas_fotocromatico', "TINYINT(1) DEFAULT 0");
    if (has_column($conn, 'productos', 'caracteristicas_fotocromatico')) {
        return 'caracteristicas_fotocromatico';
    }

    // Compatibilidad con cualquier variante legacy/encoding.
    $sql = "SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'productos'
              AND COLUMN_NAME LIKE 'caracteristicas_fotocrom%'
            LIMIT 1";
    $res = @mysqli_query($conn, $sql);
    if ($res) {
        $row = mysqli_fetch_assoc($res);
        if (!empty($row['COLUMN_NAME'])) {
            return $row['COLUMN_NAME'];
        }
    }

    return null;
}

function parse_productos_payload($contenido) {
    if (isset($contenido['productos']) && is_array($contenido['productos'])) {
        return $contenido['productos'];
    }

    if (is_array($contenido) && (isset($contenido['codigo']) || isset($contenido['nombre']))) {
        return array($contenido);
    }

    if (is_array($contenido)) {
        $first = reset($contenido);
        if (is_array($first) && (isset($first['codigo']) || isset($first['nombre']))) {
            return $contenido;
        }
    }

    return array();
}

function read_photo_flag($caracteristicas) {
    if (!is_array($caracteristicas)) {
        return 0;
    }

    foreach ($caracteristicas as $key => $value) {
        if (empty($value)) {
            continue;
        }
        $key_l = strtolower((string)$key);
        if (strpos($key_l, 'fotocrom') !== false) {
            return 1;
        }
    }

    return 0;
}

try {
    $raw = file_get_contents('php://input');
    $data = json_decode($raw, true);

    if (!is_array($data)) {
        respond(array('success' => false, 'error' => 'JSON invalido'));
    }

    if (!isset($data['usuario_id']) || !isset($data['tipo_dato'])) {
        respond(array('success' => false, 'error' => 'Faltan parametros requeridos'));
    }

    $usuario_id = $data['usuario_id'];
    $tipo_dato = (string)$data['tipo_dato'];
    $contenido = isset($data['contenido']) ? $data['contenido'] : array();

    if ($tipo_dato !== 'productos') {
        respond(array('success' => false, 'error' => 'tipo_dato invalido (debe ser productos)'));
    }

    if (empty($usuario_id) || $usuario_id === '0' || $usuario_id === 0) {
        respond(array('success' => false, 'error' => 'usuario_id invalido'));
    }

    $productos_array = parse_productos_payload($contenido);
    if (empty($productos_array)) {
        respond(array('success' => false, 'error' => 'No hay productos para sincronizar'));
    }

    $conn = mysqli_connect('localhost', 'u369606320_visoo', getenv('VISO_DB_PASSWORD'), 'u369606320_visoo');
    if (!$conn) {
        respond(array('success' => false, 'error' => 'Conexion BD: ' . mysqli_connect_error()));
    }
    mysqli_set_charset($conn, 'utf8mb4');

    ensure_productos_table($conn);
    $photo_col = resolve_photo_column($conn);

    if (is_numeric($usuario_id)) {
        $usuario_id_sql = intval($usuario_id);
    } else {
        $usuario_id_esc = mysqli_real_escape_string($conn, (string)$usuario_id);
        $usuario_id_sql = "'$usuario_id_esc'";
    }

    $tipo_dispositivo = strtolower(trim((string)($data['tipo_dispositivo'] ?? 'madre')));
    if ($tipo_dispositivo !== 'trabajador') {
        $tipo_dispositivo = 'madre';
    }
    $codigo_dispositivo = strtoupper(trim((string)($data['codigo_dispositivo'] ?? '')));
    $dispositivo_nombre = trim((string)($data['dispositivo_hijo_nombre'] ?? $data['dispositivo_nombre'] ?? ''));

    $codigo_disp_esc = mysqli_real_escape_string($conn, $codigo_dispositivo);
    $disp_nombre_esc = mysqli_real_escape_string($conn, $dispositivo_nombre);
    $tipo_disp_esc = mysqli_real_escape_string($conn, $tipo_dispositivo);

    $procesados = 0;
    $errores = array();

    foreach ($productos_array as $p) {
        if (!is_array($p) || !isset($p['codigo'])) {
            continue;
        }

        $codigo = mysqli_real_escape_string($conn, (string)$p['codigo']);
        if ($codigo === '') {
            continue;
        }

        $nombre = mysqli_real_escape_string($conn, (string)($p['nombre'] ?? ''));
        $marca = mysqli_real_escape_string($conn, (string)($p['marca'] ?? ''));
        $categoria = mysqli_real_escape_string($conn, (string)($p['categoria'] ?? ''));
        $material = mysqli_real_escape_string($conn, (string)($p['material'] ?? ''));
        $talla = mysqli_real_escape_string($conn, (string)($p['talla'] ?? ''));
        $tipo_lente = mysqli_real_escape_string($conn, (string)($p['tipo_lente'] ?? ''));

        $colors_raw = $p['colors'] ?? array();
        if (is_array($colors_raw)) {
            $colors_json = json_encode($colors_raw, JSON_UNESCAPED_UNICODE);
        } else {
            $colors_json = json_encode(array(), JSON_UNESCAPED_UNICODE);
        }
        $colors = mysqli_real_escape_string($conn, (string)$colors_json);

        $stock = intval($p['stock'] ?? 0);
        $costo = is_numeric($p['costo'] ?? null) ? floatval($p['costo']) : 0;
        $venta = is_numeric($p['venta'] ?? null) ? floatval($p['venta']) : 0;
        $precio_regular = is_numeric($p['precio_regular'] ?? null) ? floatval($p['precio_regular']) : 0;

        $caracteristicas = is_array($p['caracteristicas'] ?? null) ? $p['caracteristicas'] : array();
        $char_polarizado = !empty($caracteristicas['polarizado']) ? 1 : 0;
        $char_uv = !empty($caracteristicas['uv']) ? 1 : 0;
        $char_antireflejo = !empty($caracteristicas['antireflejo']) ? 1 : 0;
        $char_blue = !empty($caracteristicas['blue_light']) ? 1 : 0;
        $char_foto = read_photo_flag($caracteristicas);

        $created_at = mysqli_real_escape_string($conn, (string)($p['created_at'] ?? date('Y-m-d H:i:s')));

        $insert_cols = array(
            'id_usuario',
            'codigo',
            'nombre',
            'marca',
            'categoria',
            'material',
            'colors',
            'talla',
            'tipo_lente',
            'stock',
            'costo',
            'venta',
            'precio_regular',
            'caracteristicas_polarizado',
            'caracteristicas_uv',
            'caracteristicas_antireflejo',
            'caracteristicas_blue_light',
            'created_at',
            'codigo_dispositivo',
            'dispositivo_nombre',
            'tipo_dispositivo',
            'fecha_registro',
            'fecha_actualizacion'
        );
        $insert_vals = array(
            "$usuario_id_sql",
            "'$codigo'",
            "'$nombre'",
            "'$marca'",
            "'$categoria'",
            "'$material'",
            "'$colors'",
            "'$talla'",
            "'$tipo_lente'",
            "$stock",
            "$costo",
            "$venta",
            "$precio_regular",
            "$char_polarizado",
            "$char_uv",
            "$char_antireflejo",
            "$char_blue",
            "'$created_at'",
            "'$codigo_disp_esc'",
            "'$disp_nombre_esc'",
            "'$tipo_disp_esc'",
            "NOW()",
            "NOW()"
        );
        $update_parts = array(
            "nombre='$nombre'",
            "marca='$marca'",
            "categoria='$categoria'",
            "material='$material'",
            "colors='$colors'",
            "talla='$talla'",
            "tipo_lente='$tipo_lente'",
            "stock=$stock",
            "costo=$costo",
            "venta=$venta",
            "precio_regular=$precio_regular",
            "caracteristicas_polarizado=$char_polarizado",
            "caracteristicas_uv=$char_uv",
            "caracteristicas_antireflejo=$char_antireflejo",
            "caracteristicas_blue_light=$char_blue",
            "codigo_dispositivo='$codigo_disp_esc'",
            "dispositivo_nombre='$disp_nombre_esc'",
            "tipo_dispositivo='$tipo_disp_esc'",
            "fecha_actualizacion=NOW()"
        );

        if ($photo_col !== null) {
            $insert_cols[] = "`$photo_col`";
            $insert_vals[] = "$char_foto";
            $update_parts[] = "`$photo_col`=$char_foto";
        }

        $query = "INSERT INTO productos (" . implode(', ', $insert_cols) . ")
                  VALUES (" . implode(', ', $insert_vals) . ")
                  ON DUPLICATE KEY UPDATE " . implode(', ', $update_parts);

        if (!mysqli_query($conn, $query)) {
            $errores[] = mysqli_error($conn);
            continue;
        }

        $procesados++;
    }

    mysqli_close($conn);

    if (!empty($errores)) {
        respond(array(
            'success' => false,
            'error' => 'Exception: ' . implode('; ', array_unique($errores)),
            'productos_procesados' => $procesados
        ));
    }

    respond(array(
        'success' => true,
        'message' => 'OK productos subidos',
        'productos_procesados' => $procesados
    ));
} catch (Exception $e) {
    respond(array('success' => false, 'error' => 'Exception: ' . $e->getMessage()));
}

?>
