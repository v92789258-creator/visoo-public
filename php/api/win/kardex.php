<?php
/**
 * kardex.php
 *
 * GET:
 *   - usuario_id / username
 *   - codigo_dispositivo (optional)
 *   - solo_madre=1 (optional)
 *
 * POST JSON:
 *   - action=schema
 *   - action=list
 *   - action=append
 *   - action=replace_all
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

function ensure_kardex_table($conn) {
    $sql = "CREATE TABLE IF NOT EXISTS `kardex` (
        `id` BIGINT(20) NOT NULL AUTO_INCREMENT PRIMARY KEY,
        `id_usuario` VARCHAR(50) NOT NULL,
        `codigo_dispositivo` VARCHAR(80) NOT NULL DEFAULT '',
        `dispositivo_nombre` VARCHAR(255) DEFAULT '',
        `tipo_dispositivo` VARCHAR(20) DEFAULT 'madre',
        `fecha` VARCHAR(40) DEFAULT '',
        `movimiento` VARCHAR(255) DEFAULT '',
        `producto` VARCHAR(255) DEFAULT '',
        `cantidad` DECIMAL(12,2) DEFAULT 0.00,
        `costo_unitario` DECIMAL(12,2) DEFAULT 0.00,
        `valor_total` DECIMAL(12,2) DEFAULT 0.00,
        `stock_final` DECIMAL(12,2) DEFAULT 0.00,
        `payload_json` LONGTEXT DEFAULT NULL,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY `idx_usuario_branch` (`id_usuario`, `codigo_dispositivo`),
        KEY `idx_producto` (`producto`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";
    @mysqli_query($conn, $sql);

    if (!has_index($conn, 'kardex', 'idx_usuario_branch')) {
        @mysqli_query($conn, "ALTER TABLE `kardex` ADD KEY `idx_usuario_branch` (`id_usuario`, `codigo_dispositivo`)");
    }
}

function db_connect() {
    $conn = @mysqli_connect('localhost', 'phpmyadmin', getenv('VISO_DB_PASSWORD'), 'visoo');
    if (!$conn) {
        respond(array('success' => false, 'error' => 'Conexion BD: ' . mysqli_connect_error()));
    }
    mysqli_set_charset($conn, 'utf8mb4');
    ensure_kardex_table($conn);
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

function parse_kardex_item($item, $default_branch_code = '', $default_branch_name = '', $default_branch_type = 'madre') {
    $branch_code = normalize_branch_code($item['codigo_dispositivo'] ?? $default_branch_code);
    $branch_name = norm_text($item['dispositivo_nombre'] ?? $default_branch_name);
    $branch_type = norm_text($item['tipo_dispositivo'] ?? $default_branch_type);
    if ($branch_type === '') {
        $branch_type = ($branch_code !== '') ? 'hijo' : 'madre';
    }

    return array(
        'fecha' => norm_text($item['fecha'] ?? ''),
        'movimiento' => norm_text($item['movimiento'] ?? ''),
        'producto' => norm_text($item['producto'] ?? ''),
        'cantidad' => norm_float($item['cantidad'] ?? 0),
        'costo_unitario' => norm_float($item['costo_unitario'] ?? 0),
        'valor_total' => norm_float($item['valor_total'] ?? 0),
        'stock_final' => norm_float($item['stock_final'] ?? 0),
        'codigo_dispositivo' => $branch_code,
        'dispositivo_nombre' => $branch_name,
        'tipo_dispositivo' => $branch_type,
        'payload_json' => json_encode(is_array($item) ? $item : array(), JSON_UNESCAPED_UNICODE),
    );
}

function insert_kardex_item($conn, $usuario_ref, $item, $default_branch_code = '', $default_branch_name = '', $default_branch_type = 'madre') {
    $entry = parse_kardex_item($item, $default_branch_code, $default_branch_name, $default_branch_type);
    if ($usuario_ref === '') {
        return false;
    }

    $sql = "INSERT INTO kardex (
                id_usuario, codigo_dispositivo, dispositivo_nombre, tipo_dispositivo,
                fecha, movimiento, producto, cantidad, costo_unitario, valor_total, stock_final, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
    $stmt = mysqli_prepare($conn, $sql);
    if (!$stmt) {
        return false;
    }

    mysqli_stmt_bind_param(
        $stmt,
        'sssssssdddds',
        $usuario_ref,
        $entry['codigo_dispositivo'],
        $entry['dispositivo_nombre'],
        $entry['tipo_dispositivo'],
        $entry['fecha'],
        $entry['movimiento'],
        $entry['producto'],
        $entry['cantidad'],
        $entry['costo_unitario'],
        $entry['valor_total'],
        $entry['stock_final'],
        $entry['payload_json']
    );
    $ok = mysqli_stmt_execute($stmt);
    mysqli_stmt_close($stmt);
    return $ok;
}

function fetch_kardex($conn, $usuario_ref, $codigo_dispositivo = null, $solo_madre = false) {
    $usuario_ref = norm_text($usuario_ref);
    if ($usuario_ref === '') {
        return array();
    }

    $sql = "SELECT id, fecha, movimiento, producto, cantidad, costo_unitario, valor_total, stock_final,
                   payload_json, codigo_dispositivo, dispositivo_nombre, tipo_dispositivo, created_at
            FROM kardex WHERE id_usuario=?";
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

    $sql .= " ORDER BY id ASC";
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
    $items = array();
    while ($row = mysqli_fetch_assoc($result)) {
        $payload = array();
        if (!empty($row['payload_json'])) {
            $decoded = json_decode($row['payload_json'], true);
            if (is_array($decoded)) {
                $payload = $decoded;
            }
        }

        $payload['id'] = intval($row['id']);
        $payload['fecha'] = $payload['fecha'] ?? $row['fecha'];
        $payload['movimiento'] = $payload['movimiento'] ?? $row['movimiento'];
        $payload['producto'] = $payload['producto'] ?? $row['producto'];
        $payload['cantidad'] = isset($payload['cantidad']) ? $payload['cantidad'] : floatval($row['cantidad']);
        $payload['costo_unitario'] = isset($payload['costo_unitario']) ? $payload['costo_unitario'] : floatval($row['costo_unitario']);
        $payload['valor_total'] = isset($payload['valor_total']) ? $payload['valor_total'] : floatval($row['valor_total']);
        $payload['stock_final'] = isset($payload['stock_final']) ? $payload['stock_final'] : floatval($row['stock_final']);
        $payload['codigo_dispositivo'] = $payload['codigo_dispositivo'] ?? norm_text($row['codigo_dispositivo']);
        $payload['dispositivo_nombre'] = $payload['dispositivo_nombre'] ?? norm_text($row['dispositivo_nombre']);
        $payload['tipo_dispositivo'] = $payload['tipo_dispositivo'] ?? norm_text($row['tipo_dispositivo']);
        $items[] = $payload;
    }
    mysqli_stmt_close($stmt);
    return $items;
}

function handle_get() {
    $usuario_ref = resolve_usuario_ref($_GET);
    if ($usuario_ref === '') {
        respond(array('success' => false, 'error' => 'Falta parametro usuario_id/username'));
    }

    $conn = db_connect();
    $codigo_dispositivo = isset($_GET['codigo_dispositivo']) ? $_GET['codigo_dispositivo'] : null;
    $solo_madre = norm_text($_GET['solo_madre'] ?? '') === '1';
    $items = fetch_kardex($conn, $usuario_ref, $codigo_dispositivo, $solo_madre);
    mysqli_close($conn);
    respond(array('success' => true, 'kardex' => $items, 'total' => count($items)));
}

function handle_post() {
    $payload = read_json_payload();
    $action = strtolower(norm_text($payload['action'] ?? 'list'));
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
        respond(array('success' => true, 'message' => 'Tabla kardex lista'));
    }

    if ($action === 'list') {
        if ($usuario_ref === '') {
            mysqli_close($conn);
            respond(array('success' => false, 'error' => 'usuario_id/username vacio'));
        }
        $branch_param = array_key_exists('codigo_dispositivo', $payload) ? $codigo_dispositivo : null;
        $solo_madre = !empty($payload['solo_madre']);
        $items = fetch_kardex($conn, $usuario_ref, $branch_param, $solo_madre);
        mysqli_close($conn);
        respond(array('success' => true, 'kardex' => $items, 'total' => count($items)));
    }

    if ($usuario_ref === '') {
        mysqli_close($conn);
        respond(array('success' => false, 'error' => 'usuario_id/username vacio'));
    }

    if ($action === 'append') {
        $entry = is_array($payload['entry'] ?? null) ? $payload['entry'] : array();
        $ok = insert_kardex_item($conn, $usuario_ref, $entry, $codigo_dispositivo, $dispositivo_nombre, $tipo_dispositivo);
        mysqli_close($conn);
        if (!$ok) {
            respond(array('success' => false, 'error' => 'No se pudo guardar movimiento kardex'));
        }
        respond(array('success' => true, 'message' => 'Movimiento kardex guardado'));
    }

    if ($action === 'replace_all') {
        $items = is_array($payload['kardex'] ?? null) ? $payload['kardex'] : array();
        mysqli_begin_transaction($conn);
        try {
            $delete_sql = "DELETE FROM kardex WHERE id_usuario=? AND codigo_dispositivo=?";
            $delete_stmt = mysqli_prepare($conn, $delete_sql);
            if (!$delete_stmt) {
                throw new Exception('No se pudo preparar limpieza kardex');
            }
            mysqli_stmt_bind_param($delete_stmt, 'ss', $usuario_ref, $codigo_dispositivo);
            if (!mysqli_stmt_execute($delete_stmt)) {
                mysqli_stmt_close($delete_stmt);
                throw new Exception('No se pudo limpiar kardex anterior');
            }
            mysqli_stmt_close($delete_stmt);

            $saved = 0;
            foreach ($items as $item) {
                if (!is_array($item)) {
                    continue;
                }
                if (!insert_kardex_item($conn, $usuario_ref, $item, $codigo_dispositivo, $dispositivo_nombre, $tipo_dispositivo)) {
                    throw new Exception('No se pudo guardar uno de los movimientos');
                }
                $saved++;
            }

            mysqli_commit($conn);
            mysqli_close($conn);
            respond(array('success' => true, 'message' => 'Kardex reemplazado', 'saved' => $saved));
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
        handle_get();
    }
    handle_post();
} catch (Exception $e) {
    respond(array('success' => false, 'error' => 'Exception: ' . $e->getMessage()));
}

?>
