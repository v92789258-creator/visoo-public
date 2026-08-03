<?php
/**
 * get_productos.php
 *
 * GET:
 *   - action=list (default)
 *   - usuario_id / username
 *   - codigo_dispositivo (optional)
 *   - solo_madre=1 (optional)
 *
 * POST JSON:
 *   - action=schema
 *   - action=upsert
 *   - action=replace_all
 *   - action=delete
 */

error_reporting(E_ALL);
ini_set('display_errors', '0');
ini_set('log_errors', '1');
header('Content-Type: application/json; charset=utf-8');

function respond($payload) {
    echo json_encode($payload, JSON_UNESCAPED_UNICODE);
    exit;
}

function read_json_payload() {
    $raw = file_get_contents('php://input');
    if (!is_string($raw) || trim($raw) === '') {
        return array();
    }
    $decoded = json_decode($raw, true);
    return is_array($decoded) ? $decoded : array();
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

function has_index($conn, $table, $index_name) {
    $table_safe = mysqli_real_escape_string($conn, $table);
    $index_safe = mysqli_real_escape_string($conn, $index_name);
    $sql = "SELECT 1
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = '$table_safe'
              AND INDEX_NAME = '$index_safe'
            LIMIT 1";
    $res = @mysqli_query($conn, $sql);
    return ($res && mysqli_num_rows($res) > 0);
}

function ensure_productos_table($conn) {
    $sql = "CREATE TABLE IF NOT EXISTS `productos` (
        `id` INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
        `id_usuario` VARCHAR(50) NOT NULL,
        `codigo` VARCHAR(100) NOT NULL,
        `nombre` VARCHAR(255) NOT NULL,
        `marca` VARCHAR(100) DEFAULT '',
        `categoria` VARCHAR(100) DEFAULT '',
        `seccion` VARCHAR(100) DEFAULT '',
        `material` VARCHAR(100) DEFAULT '',
        `colors` LONGTEXT DEFAULT NULL,
        `talla` VARCHAR(50) DEFAULT '',
        `tipo_lente` VARCHAR(100) DEFAULT '',
        `stock` INT(11) DEFAULT 0,
        `costo` DECIMAL(10,2) DEFAULT 0.00,
        `venta` DECIMAL(10,2) DEFAULT 0.00,
        `precio_regular` DECIMAL(10,2) DEFAULT 0.00,
        `caracteristicas_polarizado` TINYINT(1) DEFAULT 0,
        `caracteristicas_uv` TINYINT(1) DEFAULT 0,
        `caracteristicas_antireflejo` TINYINT(1) DEFAULT 0,
        `caracteristicas_fotocromatico` TINYINT(1) DEFAULT 0,
        `caracteristicas_blue_light` TINYINT(1) DEFAULT 0,
        `variantes` LONGTEXT DEFAULT NULL,
        `image_path` LONGTEXT DEFAULT NULL,
        `codigo_dispositivo` VARCHAR(80) NOT NULL DEFAULT '',
        `dispositivo_nombre` VARCHAR(255) DEFAULT '',
        `tipo_dispositivo` VARCHAR(20) DEFAULT 'madre',
        `created_at` DATETIME DEFAULT NULL,
        `fecha_registro` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        `fecha_actualizacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY `uq_usuario_codigo_branch` (`id_usuario`, `codigo`, `codigo_dispositivo`),
        KEY `idx_usuario` (`id_usuario`),
        KEY `idx_usuario_branch` (`id_usuario`, `codigo_dispositivo`),
        KEY `idx_codigo` (`codigo`),
        KEY `idx_nombre` (`nombre`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";
    @mysqli_query($conn, $sql);

    ensure_column($conn, 'productos', 'seccion', "VARCHAR(100) DEFAULT ''");
    ensure_column($conn, 'productos', 'variantes', "LONGTEXT NULL");
    ensure_column($conn, 'productos', 'image_path', "LONGTEXT NULL");
    ensure_column($conn, 'productos', 'codigo_dispositivo', "VARCHAR(80) NOT NULL DEFAULT ''");
    ensure_column($conn, 'productos', 'dispositivo_nombre', "VARCHAR(255) DEFAULT ''");
    ensure_column($conn, 'productos', 'tipo_dispositivo', "VARCHAR(20) DEFAULT 'madre'");
    ensure_column($conn, 'productos', 'caracteristicas_polarizado', "TINYINT(1) DEFAULT 0");
    ensure_column($conn, 'productos', 'caracteristicas_uv', "TINYINT(1) DEFAULT 0");
    ensure_column($conn, 'productos', 'caracteristicas_antireflejo', "TINYINT(1) DEFAULT 0");
    ensure_column($conn, 'productos', 'caracteristicas_fotocromatico', "TINYINT(1) DEFAULT 0");
    ensure_column($conn, 'productos', 'caracteristicas_blue_light', "TINYINT(1) DEFAULT 0");

    @mysqli_query($conn, "UPDATE productos SET codigo_dispositivo='' WHERE codigo_dispositivo IS NULL");
    @mysqli_query($conn, "UPDATE productos SET dispositivo_nombre='' WHERE dispositivo_nombre IS NULL");
    @mysqli_query($conn, "UPDATE productos SET tipo_dispositivo='madre' WHERE tipo_dispositivo IS NULL OR tipo_dispositivo=''");

    if (has_index($conn, 'productos', 'uq_usuario_codigo') && !has_index($conn, 'productos', 'uq_usuario_codigo_branch')) {
        @mysqli_query($conn, "ALTER TABLE `productos` DROP INDEX `uq_usuario_codigo`");
    }
    if (!has_index($conn, 'productos', 'uq_usuario_codigo_branch')) {
        @mysqli_query($conn, "ALTER TABLE `productos` ADD UNIQUE KEY `uq_usuario_codigo_branch` (`id_usuario`, `codigo`, `codigo_dispositivo`)");
    }
}

function resolve_photo_column($conn) {
    if (has_column($conn, 'productos', 'caracteristicas_fotocromatico')) {
        return 'caracteristicas_fotocromatico';
    }
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

function db_connect() {
    $conn = mysqli_connect('localhost', 'phpmyadmin', getenv('VISO_DB_PASSWORD'), 'visoo');
    if (!$conn) {
        respond(array('success' => false, 'error' => 'Conexion BD: ' . mysqli_connect_error()));
    }
    mysqli_set_charset($conn, 'utf8mb4');
    ensure_productos_table($conn);
    return $conn;
}

function norm_text($value) {
    return trim((string)($value ?? ''));
}

function norm_upper($value) {
    return strtoupper(norm_text($value));
}

function norm_float($value) {
    if ($value === null || $value === '') {
        return 0.0;
    }
    return floatval($value);
}

function norm_int($value) {
    if ($value === null || $value === '') {
        return 0;
    }
    return intval($value);
}

function norm_bool($value) {
    if (is_bool($value)) {
        return $value ? 1 : 0;
    }
    $text = strtolower(trim((string)$value));
    return in_array($text, array('1', 'true', 'yes', 'si', 'on'), true) ? 1 : 0;
}

function norm_json_array($value) {
    if (is_array($value)) {
        return json_encode(array_values($value), JSON_UNESCAPED_UNICODE);
    }
    return json_encode(array(), JSON_UNESCAPED_UNICODE);
}

function norm_json_object($value) {
    if (is_array($value)) {
        return json_encode($value, JSON_UNESCAPED_UNICODE);
    }
    return json_encode(new stdClass(), JSON_UNESCAPED_UNICODE);
}

function decode_json_array($raw) {
    if (!is_string($raw) || trim($raw) === '') {
        return array();
    }
    $decoded = json_decode($raw, true);
    return is_array($decoded) ? array_values($decoded) : array();
}

function decode_json_object($raw) {
    if (!is_string($raw) || trim($raw) === '') {
        return array();
    }
    $decoded = json_decode($raw, true);
    return is_array($decoded) ? $decoded : array();
}

function resolve_usuario_ref($payload) {
    $usuario_id = norm_text($payload['usuario_id'] ?? '');
    $username = norm_text($payload['username'] ?? '');
    $usuario_ref = norm_text($payload['usuario_ref'] ?? '');
    if ($usuario_id !== '') {
        return $usuario_id;
    }
    if ($username !== '') {
        return $username;
    }
    return $usuario_ref;
}

function normalize_branch_code($value) {
    $code = norm_upper($value);
    return ($code === '__GLOBAL__') ? '' : $code;
}

function parse_producto($item, $default_branch_code = '', $default_branch_name = '', $default_branch_type = 'madre') {
    $caracteristicas = is_array($item['caracteristicas'] ?? null) ? $item['caracteristicas'] : array();
    $variantes = is_array($item['variantes'] ?? null) ? $item['variantes'] : array();

    $foto_key_utf = json_decode('"fotocrom\u00e1tico"', true);
    $foto_val = 0;
    if (array_key_exists('fotocromatico', $caracteristicas)) {
        $foto_val = norm_bool($caracteristicas['fotocromatico']);
    } elseif (is_string($foto_key_utf) && array_key_exists($foto_key_utf, $caracteristicas)) {
        $foto_val = norm_bool($caracteristicas[$foto_key_utf]);
    }

    $branch_code = normalize_branch_code($item['codigo_dispositivo'] ?? $default_branch_code);
    $branch_name = norm_text($item['dispositivo_nombre'] ?? $default_branch_name);
    $branch_type = norm_text($item['tipo_dispositivo'] ?? $default_branch_type);
    if ($branch_type === '') {
        $branch_type = ($branch_code !== '') ? 'hijo' : 'madre';
    }

    return array(
        'codigo' => norm_text($item['codigo'] ?? ''),
        'nombre' => norm_text($item['nombre'] ?? ''),
        'marca' => norm_text($item['marca'] ?? ''),
        'categoria' => norm_text($item['categoria'] ?? ''),
        'seccion' => norm_text($item['seccion'] ?? ($item['categoria'] ?? '')),
        'material' => norm_text($item['material'] ?? ''),
        'colors' => norm_json_array($item['colors'] ?? array()),
        'talla' => norm_text($item['talla'] ?? ''),
        'tipo_lente' => norm_text($item['tipo_lente'] ?? ''),
        'stock' => norm_int($item['stock'] ?? 0),
        'costo' => norm_float($item['costo'] ?? 0),
        'venta' => norm_float($item['venta'] ?? 0),
        'precio_regular' => norm_float($item['precio_regular'] ?? 0),
        'caracteristicas_polarizado' => norm_bool($caracteristicas['polarizado'] ?? 0),
        'caracteristicas_uv' => norm_bool($caracteristicas['uv'] ?? 0),
        'caracteristicas_antireflejo' => norm_bool($caracteristicas['antireflejo'] ?? 0),
        'caracteristicas_fotocromatico' => $foto_val,
        'caracteristicas_blue_light' => norm_bool($caracteristicas['blue_light'] ?? 0),
        'variantes' => norm_json_object($variantes),
        'image_path' => norm_text($item['image_path'] ?? ($item['imagen'] ?? '')),
        'codigo_dispositivo' => $branch_code,
        'dispositivo_nombre' => $branch_name,
        'tipo_dispositivo' => $branch_type,
        'created_at' => norm_text($item['created_at'] ?? ''),
    );
}

function upsert_producto($conn, $usuario_ref, $item, $default_branch_code = '', $default_branch_name = '', $default_branch_type = 'madre') {
    $producto = parse_producto($item, $default_branch_code, $default_branch_name, $default_branch_type);
    if ($usuario_ref === '' || $producto['codigo'] === '' || $producto['nombre'] === '') {
        return false;
    }

    $sql = "INSERT INTO productos (
                id_usuario, codigo, nombre, marca, categoria, seccion, material, colors, talla, tipo_lente,
                stock, costo, venta, precio_regular,
                caracteristicas_polarizado, caracteristicas_uv, caracteristicas_antireflejo,
                caracteristicas_fotocromatico, caracteristicas_blue_light,
                variantes, image_path, codigo_dispositivo, dispositivo_nombre, tipo_dispositivo, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULLIF(?, ''))
            ON DUPLICATE KEY UPDATE
                nombre=VALUES(nombre),
                marca=VALUES(marca),
                categoria=VALUES(categoria),
                seccion=VALUES(seccion),
                material=VALUES(material),
                colors=VALUES(colors),
                talla=VALUES(talla),
                tipo_lente=VALUES(tipo_lente),
                stock=VALUES(stock),
                costo=VALUES(costo),
                venta=VALUES(venta),
                precio_regular=VALUES(precio_regular),
                caracteristicas_polarizado=VALUES(caracteristicas_polarizado),
                caracteristicas_uv=VALUES(caracteristicas_uv),
                caracteristicas_antireflejo=VALUES(caracteristicas_antireflejo),
                caracteristicas_fotocromatico=VALUES(caracteristicas_fotocromatico),
                caracteristicas_blue_light=VALUES(caracteristicas_blue_light),
                variantes=VALUES(variantes),
                image_path=VALUES(image_path),
                dispositivo_nombre=VALUES(dispositivo_nombre),
                tipo_dispositivo=VALUES(tipo_dispositivo),
                created_at=COALESCE(VALUES(created_at), created_at),
                fecha_actualizacion=CURRENT_TIMESTAMP";

    $stmt = mysqli_prepare($conn, $sql);
    if (!$stmt) {
        return false;
    }

    mysqli_stmt_bind_param(
        $stmt,
        'ssssssssssidddiiiiissssss',
        $usuario_ref,
        $producto['codigo'],
        $producto['nombre'],
        $producto['marca'],
        $producto['categoria'],
        $producto['seccion'],
        $producto['material'],
        $producto['colors'],
        $producto['talla'],
        $producto['tipo_lente'],
        $producto['stock'],
        $producto['costo'],
        $producto['venta'],
        $producto['precio_regular'],
        $producto['caracteristicas_polarizado'],
        $producto['caracteristicas_uv'],
        $producto['caracteristicas_antireflejo'],
        $producto['caracteristicas_fotocromatico'],
        $producto['caracteristicas_blue_light'],
        $producto['variantes'],
        $producto['image_path'],
        $producto['codigo_dispositivo'],
        $producto['dispositivo_nombre'],
        $producto['tipo_dispositivo'],
        $producto['created_at']
    );

    $ok = mysqli_stmt_execute($stmt);
    mysqli_stmt_close($stmt);
    return $ok;
}

function fetch_productos($conn, $usuario_ref, $codigo_dispositivo = null, $solo_madre = false) {
    $usuario_ref = norm_text($usuario_ref);
    if ($usuario_ref === '') {
        return array();
    }

    $photo_col = resolve_photo_column($conn);
    $photo_select = "0 AS caracteristicas_fotocromatico";
    if ($photo_col !== null) {
        $photo_select = "COALESCE(`$photo_col`, 0) AS caracteristicas_fotocromatico";
    }

    $select_fields = "id, id_usuario, codigo, nombre, marca, categoria, seccion, material, colors, talla, tipo_lente,
                      stock, costo, venta, precio_regular,
                      caracteristicas_polarizado, caracteristicas_uv, caracteristicas_antireflejo,
                      $photo_select, caracteristicas_blue_light, variantes, image_path, created_at,
                      fecha_registro, fecha_actualizacion, codigo_dispositivo, dispositivo_nombre, tipo_dispositivo";

    $sql = "SELECT $select_fields FROM productos WHERE id_usuario=?";
    $types = 's';
    $params = array($usuario_ref);

    $branch_code = null;
    if ($codigo_dispositivo !== null) {
        $branch_code = normalize_branch_code($codigo_dispositivo);
    }

    if ($branch_code !== null && $branch_code !== '') {
        $sql .= " AND codigo_dispositivo=?";
        $types .= 's';
        $params[] = $branch_code;
    } elseif ($solo_madre) {
        $sql .= " AND COALESCE(codigo_dispositivo, '')=''";
    }

    $sql .= " ORDER BY fecha_registro DESC, nombre ASC";
    $stmt = mysqli_prepare($conn, $sql);
    if (!$stmt) {
        return array();
    }

    if (count($params) === 1) {
        mysqli_stmt_bind_param($stmt, $types, $params[0]);
    } else {
        mysqli_stmt_bind_param($stmt, $types, $params[0], $params[1]);
    }
    if (!mysqli_stmt_execute($stmt)) {
        mysqli_stmt_close($stmt);
        return array();
    }

    $result = mysqli_stmt_get_result($stmt);
    $productos = array();
    while ($row = mysqli_fetch_assoc($result)) {
        $is_foto = !empty($row['caracteristicas_fotocromatico']);
        $foto_key_utf = json_decode('"fotocrom\u00e1tico"', true);
        $caracteristicas = array(
            'polarizado' => !empty($row['caracteristicas_polarizado']),
            'uv' => !empty($row['caracteristicas_uv']),
            'antireflejo' => !empty($row['caracteristicas_antireflejo']),
            'fotocromatico' => $is_foto,
            'blue_light' => !empty($row['caracteristicas_blue_light'])
        );
        if (is_string($foto_key_utf) && $foto_key_utf !== 'fotocromatico') {
            $caracteristicas[$foto_key_utf] = $is_foto;
        }

        $productos[] = array(
            'id' => intval($row['id']),
            'codigo' => $row['codigo'],
            'nombre' => $row['nombre'],
            'marca' => $row['marca'],
            'categoria' => $row['categoria'],
            'seccion' => $row['seccion'],
            'material' => $row['material'],
            'colors' => decode_json_array($row['colors']),
            'talla' => $row['talla'],
            'tipo_lente' => $row['tipo_lente'],
            'stock' => intval($row['stock']),
            'costo' => floatval($row['costo']),
            'venta' => floatval($row['venta']),
            'precio_regular' => floatval($row['precio_regular']),
            'caracteristicas' => $caracteristicas,
            'variantes' => decode_json_object($row['variantes']),
            'image_path' => norm_text($row['image_path']),
            'imagen' => norm_text($row['image_path']),
            'created_at' => $row['created_at'],
            'fecha_registro' => $row['fecha_registro'],
            'fecha_actualizacion' => $row['fecha_actualizacion'],
            'codigo_dispositivo' => norm_text($row['codigo_dispositivo']),
            'dispositivo_nombre' => norm_text($row['dispositivo_nombre']),
            'tipo_dispositivo' => norm_text($row['tipo_dispositivo'] ?: 'madre')
        );
    }

    mysqli_stmt_close($stmt);
    return $productos;
}

function handle_get_list() {
    $usuario_ref = resolve_usuario_ref($_GET);
    if ($usuario_ref === '') {
        respond(array('success' => false, 'error' => 'Falta parametro usuario_id/username'));
    }

    $codigo_dispositivo = isset($_GET['codigo_dispositivo']) ? $_GET['codigo_dispositivo'] : null;
    $solo_madre = norm_text($_GET['solo_madre'] ?? '') === '1';

    $conn = db_connect();
    $productos = fetch_productos($conn, $usuario_ref, $codigo_dispositivo, $solo_madre);
    mysqli_close($conn);

    respond(array(
        'success' => true,
        'productos' => $productos,
        'total' => count($productos)
    ));
}

function handle_post_action() {
    $payload = read_json_payload();
    $action = strtolower(norm_text($payload['action'] ?? ''));
    if ($action === '') {
        $action = 'list';
    }

    $usuario_ref = resolve_usuario_ref($payload);
    $codigo_dispositivo = normalize_branch_code($payload['codigo_dispositivo'] ?? '');
    $dispositivo_nombre = norm_text($payload['dispositivo_nombre'] ?? '');
    $tipo_dispositivo = norm_text($payload['tipo_dispositivo'] ?? '');
    if ($tipo_dispositivo === '') {
        $tipo_dispositivo = ($codigo_dispositivo !== '') ? 'hijo' : 'madre';
    }

    $conn = db_connect();

    if ($action === 'schema') {
        mysqli_close($conn);
        respond(array('success' => true, 'message' => 'Tabla productos lista'));
    }

    if ($action === 'list') {
        if ($usuario_ref === '') {
            mysqli_close($conn);
            respond(array('success' => false, 'error' => 'usuario_id/username vacio'));
        }
        $solo_madre = !empty($payload['solo_madre']);
        $branch_param = array_key_exists('codigo_dispositivo', $payload) ? $codigo_dispositivo : null;
        $productos = fetch_productos($conn, $usuario_ref, $branch_param, $solo_madre);
        mysqli_close($conn);
        respond(array('success' => true, 'productos' => $productos, 'total' => count($productos)));
    }

    if ($usuario_ref === '') {
        mysqli_close($conn);
        respond(array('success' => false, 'error' => 'usuario_id/username vacio'));
    }

    if ($action === 'upsert') {
        $producto = is_array($payload['producto'] ?? null) ? $payload['producto'] : array();
        $ok = upsert_producto($conn, $usuario_ref, $producto, $codigo_dispositivo, $dispositivo_nombre, $tipo_dispositivo);
        mysqli_close($conn);
        if (!$ok) {
            respond(array('success' => false, 'error' => 'No se pudo guardar producto'));
        }
        respond(array('success' => true, 'message' => 'Producto guardado'));
    }

    if ($action === 'delete') {
        $codigo = norm_text($payload['codigo'] ?? '');
        if ($codigo === '') {
            mysqli_close($conn);
            respond(array('success' => false, 'error' => 'codigo vacio'));
        }

        $sql = "DELETE FROM productos WHERE id_usuario=? AND codigo=? AND codigo_dispositivo=?";
        $stmt = mysqli_prepare($conn, $sql);
        if (!$stmt) {
            mysqli_close($conn);
            respond(array('success' => false, 'error' => 'No se pudo preparar delete'));
        }
        mysqli_stmt_bind_param($stmt, 'sss', $usuario_ref, $codigo, $codigo_dispositivo);
        $ok = mysqli_stmt_execute($stmt);
        $affected = $ok ? mysqli_stmt_affected_rows($stmt) : 0;
        mysqli_stmt_close($stmt);
        mysqli_close($conn);
        respond(array('success' => $ok, 'deleted' => max(0, intval($affected))));
    }

    if ($action === 'replace_all') {
        $productos = is_array($payload['productos'] ?? null) ? $payload['productos'] : array();

        mysqli_begin_transaction($conn);
        try {
            $delete_sql = "DELETE FROM productos WHERE id_usuario=? AND codigo_dispositivo=?";
            $delete_stmt = mysqli_prepare($conn, $delete_sql);
            if (!$delete_stmt) {
                throw new Exception('No se pudo preparar limpieza');
            }
            mysqli_stmt_bind_param($delete_stmt, 'ss', $usuario_ref, $codigo_dispositivo);
            if (!mysqli_stmt_execute($delete_stmt)) {
                mysqli_stmt_close($delete_stmt);
                throw new Exception('No se pudo limpiar inventario anterior');
            }
            mysqli_stmt_close($delete_stmt);

            $saved = 0;
            foreach ($productos as $item) {
                if (!is_array($item)) {
                    continue;
                }
                if (upsert_producto($conn, $usuario_ref, $item, $codigo_dispositivo, $dispositivo_nombre, $tipo_dispositivo)) {
                    $saved++;
                } else {
                    throw new Exception('No se pudo guardar uno de los productos');
                }
            }

            mysqli_commit($conn);
            mysqli_close($conn);
            respond(array('success' => true, 'message' => 'Inventario reemplazado', 'saved' => $saved));
        } catch (Exception $e) {
            mysqli_rollback($conn);
            mysqli_close($conn);
            respond(array('success' => false, 'error' => $e->getMessage()));
        }
    }

    mysqli_close($conn);
    respond(array('success' => false, 'error' => 'Accion no soportada'));
}

try {
    if ($_SERVER['REQUEST_METHOD'] === 'GET') {
        handle_get_list();
    }
    handle_post_action();
} catch (Exception $e) {
    respond(array('success' => false, 'error' => 'Exception: ' . $e->getMessage()));
}

?>
