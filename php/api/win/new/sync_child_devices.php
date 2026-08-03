<?php
/**
 * API de dispositivos hijos (cloud)
 * Endpoint sugerido: https://api.yhana.cloud/win/new/sync_child_devices.php
 *
 * Acciones:
 * - upsert   : crea/actualiza dispositivo hijo
 * - delete   : elimina por id o codigo_dispositivo
 * - validate : valida codigo de dispositivo hijo para usuario madre
 * - list     : lista dispositivos del usuario madre
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

error_reporting(E_ALL);
ini_set('display_errors', '0');
ini_set('log_errors', '1');
if (function_exists('mysqli_report')) {
    mysqli_report(MYSQLI_REPORT_OFF);
}

function respond($payload, $status_code = 200) {
    http_response_code($status_code);
    echo json_encode($payload, JSON_UNESCAPED_UNICODE);
    exit;
}

register_shutdown_function(function () {
    $err = error_get_last();
    if (!$err) {
        return;
    }
    $fatal_types = [E_ERROR, E_PARSE, E_CORE_ERROR, E_COMPILE_ERROR, E_USER_ERROR];
    if (!in_array($err['type'] ?? 0, $fatal_types, true)) {
        return;
    }
    if (!headers_sent()) {
        http_response_code(500);
        header('Content-Type: application/json; charset=utf-8');
    }
    echo json_encode([
        'success' => false,
        'error' => 'Fatal PHP',
        'detail' => (string)($err['message'] ?? 'unknown'),
        'file' => basename((string)($err['file'] ?? '')),
        'line' => (int)($err['line'] ?? 0),
    ], JSON_UNESCAPED_UNICODE);
});

function safe_upper($value) {
    return strtoupper(trim((string)$value));
}

function cloud_sanitize_token($value, $fallback = 'unknown') {
    $raw = trim((string)$value);
    if ($raw === '') {
        return $fallback;
    }
    $san = preg_replace('/[^A-Za-z0-9._-]+/', '_', $raw);
    $san = trim((string)$san, '_');
    return $san === '' ? $fallback : $san;
}

function cloud_device_folder_path($usuario_madre, $codigo_dispositivo) {
    $root = __DIR__ . DIRECTORY_SEPARATOR . '_cloud_store';
    $usuario = cloud_sanitize_token($usuario_madre, 'unknown_user');
    $codigo = strtoupper(cloud_sanitize_token($codigo_dispositivo, 'UNKNOWN_DEVICE'));
    return $root . DIRECTORY_SEPARATOR . 'viso-' . $usuario . '+' . $codigo;
}

function rrmdir_safe($dir) {
    if (!is_dir($dir)) {
        return true;
    }

    $items = @scandir($dir);
    if (!is_array($items)) {
        return false;
    }

    foreach ($items as $item) {
        if ($item === '.' || $item === '..') {
            continue;
        }
        $path = $dir . DIRECTORY_SEPARATOR . $item;
        if (is_dir($path)) {
            if (!rrmdir_safe($path)) {
                return false;
            }
        } else {
            if (!@unlink($path)) {
                return false;
            }
        }
    }

    return @rmdir($dir);
}

function delete_device_snapshot_folder($usuario_madre, $codigo_dispositivo, &$message = '') {
    $folder = cloud_device_folder_path($usuario_madre, $codigo_dispositivo);
    $store_root = __DIR__ . DIRECTORY_SEPARATOR . '_cloud_store';
    $store_real = @realpath($store_root);
    $folder_real = @realpath($folder);

    if ($folder_real === false) {
        if (is_dir($folder)) {
            $folder_real = $folder;
        } else {
            $message = 'Sin snapshot en _cloud_store';
            return true;
        }
    }

    if ($store_real !== false) {
        $prefix = rtrim($store_real, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR;
        if (strpos($folder_real, $prefix) !== 0) {
            $message = 'Ruta snapshot fuera de _cloud_store';
            return false;
        }
    }

    $ok = rrmdir_safe($folder_real);
    $message = $ok ? 'Snapshot eliminado' : 'No se pudo eliminar snapshot';
    return $ok;
}

function _env_or_empty($key) {
    $val = getenv($key);
    if ($val === false) {
        return '';
    }
    return trim((string)$val);
}

function _unique_non_empty_values($values) {
    $out = [];
    $seen = [];
    foreach ($values as $value) {
        $value = trim((string)$value);
        if ($value === '' || isset($seen[$value])) {
            continue;
        }
        $seen[$value] = true;
        $out[] = $value;
    }
    return $out;
}

function connect_visoo_db(&$attempts = null) {
    $attempts = [];

    $hosts = _unique_non_empty_values([
        _env_or_empty('VISO_DB_HOST'),
        _env_or_empty('DB_HOST'),
        _env_or_empty('MYSQL_HOST'),
        'localhost',
        '127.0.0.1',
    ]);
    $users = _unique_non_empty_values([
        _env_or_empty('VISO_DB_USER'),
        _env_or_empty('DB_USER'),
        _env_or_empty('MYSQL_USER'),
        'phpmyadmin',
        'u369606320_visoo',
    ]);
    $passwords = _unique_non_empty_values([
        _env_or_empty('VISO_DB_PASS'),
        _env_or_empty('DB_PASS'),
        _env_or_empty('MYSQL_PASSWORD'),
        getenv('VISO_DB_PASSWORD'),
    ]);
    $dbs = _unique_non_empty_values([
        _env_or_empty('VISO_DB_NAME'),
        _env_or_empty('DB_NAME'),
        _env_or_empty('MYSQL_DATABASE'),
        'visoo',
        'u369606320_visoo',
    ]);

    foreach ($hosts as $host) {
        foreach ($users as $user) {
            foreach ($passwords as $pass) {
                foreach ($dbs as $db) {
                    $conn = null;
                    try {
                        $conn = @mysqli_connect($host, $user, $pass, $db);
                    } catch (Throwable $e) {
                        $conn = null;
                    }
                    if ($conn) {
                        @mysqli_set_charset($conn, 'utf8mb4');
                        return $conn;
                    }

                    $attempts[] = "host={$host}, user={$user}, db={$db}, err=" . mysqli_connect_error();
                }
            }
        }
    }

    return null;
}

$raw_input = file_get_contents('php://input');
$input = json_decode($raw_input, true);
if (!is_array($input)) {
    $input = $_POST;
}
if (!is_array($input) || empty($input)) {
    $input = $_GET;
}

$action = strtolower(trim((string)($input['action'] ?? 'upsert')));
$usuario_madre = trim((string)($input['usuario_madre'] ?? $input['username'] ?? ''));

if ($usuario_madre === '') {
    respond([
        'success' => false,
        'error' => 'Falta usuario_madre'
    ], 400);
}

if (!function_exists('mysqli_connect')) {
    respond([
        'success' => false,
        'error' => 'Extension mysqli no disponible en el servidor'
    ], 500);
}

$conn_attempts = [];
$conn = connect_visoo_db($conn_attempts);
if (!$conn) {
    respond([
        'success' => false,
        'error' => 'Conexion BD fallida',
        'detail' => mysqli_connect_error(),
        'hints' => [
            'Configura VISO_DB_HOST, VISO_DB_USER, VISO_DB_PASS, VISO_DB_NAME en el servidor',
            'Verifica que el usuario MySQL tenga permisos sobre la BD'
        ],
        'attempts' => array_slice($conn_attempts, 0, 6)
    ], 500);
}

$create_table_sql = "CREATE TABLE IF NOT EXISTS `dispositivos_hijos` (
    `id` VARCHAR(64) NOT NULL,
    `usuario_madre` VARCHAR(120) NOT NULL,
    `nombre_optica` VARCHAR(255) NOT NULL,
    `ciudad` VARCHAR(120) DEFAULT NULL,
    `codigo_dispositivo` VARCHAR(80) NOT NULL,
    `estado` VARCHAR(20) NOT NULL DEFAULT 'activo',
    `cloud_sync_enabled` TINYINT(1) NOT NULL DEFAULT 1,
    `ultima_sincronizacion` DATETIME DEFAULT NULL,
    `created_at` DATETIME DEFAULT NULL,
    `updated_at` DATETIME DEFAULT NULL,
    `fecha_registro` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `fecha_actualizacion` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_usuario_codigo` (`usuario_madre`, `codigo_dispositivo`),
    KEY `idx_usuario_madre` (`usuario_madre`),
    KEY `idx_estado` (`estado`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";

if (!mysqli_query($conn, $create_table_sql)) {
    respond([
        'success' => false,
        'error' => 'No se pudo crear tabla dispositivos_hijos: ' . mysqli_error($conn)
    ], 500);
}

if ($action === 'upsert') {
    $id = trim((string)($input['id'] ?? ''));
    if ($id === '') {
        $id = uniqid('dh_', true);
    }

    $nombre_optica = trim((string)($input['nombre_optica'] ?? ''));
    $ciudad = trim((string)($input['ciudad'] ?? ''));
    $codigo_dispositivo = safe_upper($input['codigo_dispositivo'] ?? '');
    $estado = strtolower(trim((string)($input['estado'] ?? 'activo')));
    $cloud_sync_enabled = !empty($input['cloud_sync_enabled']) ? 1 : 0;
    $ultima_sincronizacion = trim((string)($input['ultima_sincronizacion'] ?? ''));
    $created_at = trim((string)($input['created_at'] ?? ''));
    $updated_at = trim((string)($input['updated_at'] ?? ''));

    if ($nombre_optica === '' || $codigo_dispositivo === '') {
        respond([
            'success' => false,
            'error' => 'Faltan campos requeridos: nombre_optica o codigo_dispositivo'
        ], 400);
    }

    if ($estado !== 'activo' && $estado !== 'bloqueado') {
        $estado = 'activo';
    }

    if ($created_at === '') {
        $created_at = date('Y-m-d H:i:s');
    }
    if ($updated_at === '') {
        $updated_at = date('Y-m-d H:i:s');
    }
    if ($ultima_sincronizacion === '') {
        $ultima_sincronizacion = null;
    }

    $sql = "INSERT INTO dispositivos_hijos (
                id, usuario_madre, nombre_optica, ciudad, codigo_dispositivo, estado,
                cloud_sync_enabled, ultima_sincronizacion, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON DUPLICATE KEY UPDATE
                nombre_optica = VALUES(nombre_optica),
                ciudad = VALUES(ciudad),
                estado = VALUES(estado),
                cloud_sync_enabled = VALUES(cloud_sync_enabled),
                ultima_sincronizacion = VALUES(ultima_sincronizacion),
                updated_at = VALUES(updated_at)";

    $stmt = mysqli_prepare($conn, $sql);
    if (!$stmt) {
        respond([
            'success' => false,
            'error' => 'Error preparando query upsert: ' . mysqli_error($conn)
        ], 500);
    }

    mysqli_stmt_bind_param(
        $stmt,
        'ssssssisss',
        $id,
        $usuario_madre,
        $nombre_optica,
        $ciudad,
        $codigo_dispositivo,
        $estado,
        $cloud_sync_enabled,
        $ultima_sincronizacion,
        $created_at,
        $updated_at
    );

    if (!mysqli_stmt_execute($stmt)) {
        $err = mysqli_stmt_error($stmt);
        mysqli_stmt_close($stmt);
        respond([
            'success' => false,
            'error' => 'Error guardando dispositivo hijo: ' . $err
        ], 500);
    }

    mysqli_stmt_close($stmt);
    mysqli_close($conn);

    respond([
        'success' => true,
        'message' => 'Dispositivo hijo sincronizado en nube',
        'dispositivo' => [
            'id' => $id,
            'usuario_madre' => $usuario_madre,
            'nombre_optica' => $nombre_optica,
            'ciudad' => $ciudad,
            'codigo_dispositivo' => $codigo_dispositivo,
            'estado' => $estado,
            'cloud_sync_enabled' => (bool)$cloud_sync_enabled
        ]
    ]);
}

if ($action === 'delete') {
    $id = trim((string)($input['id'] ?? ''));
    $codigo_dispositivo = safe_upper($input['codigo_dispositivo'] ?? '');
    $codigo_target_for_snapshot = $codigo_dispositivo;

    if ($id === '' && $codigo_dispositivo === '') {
        respond([
            'success' => false,
            'error' => 'Debe enviar id o codigo_dispositivo para eliminar'
        ], 400);
    }

    if ($id !== '') {
        $lookup_stmt = mysqli_prepare(
            $conn,
            "SELECT codigo_dispositivo FROM dispositivos_hijos WHERE usuario_madre = ? AND id = ? LIMIT 1"
        );
        if ($lookup_stmt) {
            mysqli_stmt_bind_param($lookup_stmt, 'ss', $usuario_madre, $id);
            mysqli_stmt_execute($lookup_stmt);
            $lookup_row = null;
            if (function_exists('mysqli_stmt_get_result')) {
                $lookup_result = mysqli_stmt_get_result($lookup_stmt);
                $lookup_row = $lookup_result ? mysqli_fetch_assoc($lookup_result) : null;
            } else {
                mysqli_stmt_bind_result($lookup_stmt, $lookup_codigo);
                if (mysqli_stmt_fetch($lookup_stmt)) {
                    $lookup_row = ['codigo_dispositivo' => $lookup_codigo];
                }
            }
            if (is_array($lookup_row) && !empty($lookup_row['codigo_dispositivo'])) {
                $codigo_target_for_snapshot = safe_upper($lookup_row['codigo_dispositivo']);
            }
            mysqli_stmt_close($lookup_stmt);
        }

        $stmt = mysqli_prepare($conn, "DELETE FROM dispositivos_hijos WHERE usuario_madre = ? AND id = ?");
        mysqli_stmt_bind_param($stmt, 'ss', $usuario_madre, $id);
    } else {
        $stmt = mysqli_prepare($conn, "DELETE FROM dispositivos_hijos WHERE usuario_madre = ? AND codigo_dispositivo = ?");
        mysqli_stmt_bind_param($stmt, 'ss', $usuario_madre, $codigo_dispositivo);
    }

    if (!$stmt) {
        respond([
            'success' => false,
            'error' => 'Error preparando query delete: ' . mysqli_error($conn)
        ], 500);
    }

    if (!mysqli_stmt_execute($stmt)) {
        $err = mysqli_stmt_error($stmt);
        mysqli_stmt_close($stmt);
        respond([
            'success' => false,
            'error' => 'Error eliminando dispositivo hijo: ' . $err
        ], 500);
    }

    $affected = mysqli_stmt_affected_rows($stmt);
    mysqli_stmt_close($stmt);

    $snapshot_deleted = false;
    $snapshot_message = 'Sin cambios';
    if ($affected > 0 && $codigo_target_for_snapshot !== '') {
        $snapshot_deleted = delete_device_snapshot_folder(
            $usuario_madre,
            $codigo_target_for_snapshot,
            $snapshot_message
        );
    }

    mysqli_close($conn);

    respond([
        'success' => true,
        'deleted' => $affected > 0,
        'message' => $affected > 0 ? 'Dispositivo hijo eliminado en nube' : 'No se encontro dispositivo para eliminar',
        'snapshot_deleted' => (bool)$snapshot_deleted,
        'snapshot_message' => $snapshot_message,
        'codigo_dispositivo' => $codigo_target_for_snapshot
    ]);
}

if ($action === 'validate') {
    $codigo_dispositivo = safe_upper($input['codigo_dispositivo'] ?? '');
    if ($codigo_dispositivo === '') {
        respond([
            'success' => false,
            'error' => 'Falta codigo_dispositivo'
        ], 400);
    }

    $stmt = mysqli_prepare(
        $conn,
        "SELECT id, usuario_madre, nombre_optica, ciudad, codigo_dispositivo, estado, cloud_sync_enabled, ultima_sincronizacion, created_at, updated_at
         FROM dispositivos_hijos
         WHERE usuario_madre = ? AND codigo_dispositivo = ?
         LIMIT 1"
    );
    if (!$stmt) {
        respond([
            'success' => false,
            'error' => 'Error preparando query validate: ' . mysqli_error($conn)
        ], 500);
    }

    mysqli_stmt_bind_param($stmt, 'ss', $usuario_madre, $codigo_dispositivo);
    mysqli_stmt_execute($stmt);
    $row = null;
    if (function_exists('mysqli_stmt_get_result')) {
        $result = mysqli_stmt_get_result($stmt);
        $row = $result ? mysqli_fetch_assoc($result) : null;
    } else {
        mysqli_stmt_bind_result(
            $stmt,
            $id,
            $usuario_row,
            $nombre_optica,
            $ciudad,
            $codigo_row,
            $estado,
            $cloud_sync_enabled,
            $ultima_sincronizacion,
            $created_at,
            $updated_at
        );
        if (mysqli_stmt_fetch($stmt)) {
            $row = [
                'id' => $id,
                'usuario_madre' => $usuario_row,
                'nombre_optica' => $nombre_optica,
                'ciudad' => $ciudad,
                'codigo_dispositivo' => $codigo_row,
                'estado' => $estado,
                'cloud_sync_enabled' => $cloud_sync_enabled,
                'ultima_sincronizacion' => $ultima_sincronizacion,
                'created_at' => $created_at,
                'updated_at' => $updated_at,
            ];
        }
    }
    mysqli_stmt_close($stmt);
    mysqli_close($conn);

    if (!$row) {
        respond([
            'success' => true,
            'found' => false,
            'message' => 'CÃ³digo de dispositivo hijo no encontrado'
        ]);
    }

    respond([
        'success' => true,
        'found' => true,
        'message' => 'CÃ³digo vÃ¡lido',
        'dispositivo' => [
            'id' => $row['id'],
            'usuario_madre' => $row['usuario_madre'],
            'nombre_optica' => $row['nombre_optica'],
            'ciudad' => $row['ciudad'],
            'codigo_dispositivo' => $row['codigo_dispositivo'],
            'estado' => strtolower((string)$row['estado']),
            'cloud_sync_enabled' => (bool)$row['cloud_sync_enabled'],
            'ultima_sincronizacion' => $row['ultima_sincronizacion'],
            'created_at' => $row['created_at'],
            'updated_at' => $row['updated_at']
        ]
    ]);
}

if ($action === 'list') {
    $stmt = mysqli_prepare(
        $conn,
        "SELECT id, nombre_optica, ciudad, codigo_dispositivo, estado, cloud_sync_enabled, ultima_sincronizacion, created_at, updated_at
         FROM dispositivos_hijos
         WHERE usuario_madre = ?
         ORDER BY fecha_actualizacion DESC"
    );
    if (!$stmt) {
        respond([
            'success' => false,
            'error' => 'Error preparando query list: ' . mysqli_error($conn)
        ], 500);
    }

    mysqli_stmt_bind_param($stmt, 's', $usuario_madre);
    mysqli_stmt_execute($stmt);
    $devices = [];
    if (function_exists('mysqli_stmt_get_result')) {
        $result = mysqli_stmt_get_result($stmt);
        if ($result) {
            while ($row = mysqli_fetch_assoc($result)) {
                $devices[] = [
                    'id' => $row['id'],
                    'nombre_optica' => $row['nombre_optica'],
                    'ciudad' => $row['ciudad'],
                    'codigo_dispositivo' => $row['codigo_dispositivo'],
                    'estado' => strtolower((string)$row['estado']),
                    'cloud_sync_enabled' => (bool)$row['cloud_sync_enabled'],
                    'ultima_sincronizacion' => $row['ultima_sincronizacion'],
                    'created_at' => $row['created_at'],
                    'updated_at' => $row['updated_at']
                ];
            }
        }
    } else {
        mysqli_stmt_bind_result(
            $stmt,
            $id,
            $nombre_optica,
            $ciudad,
            $codigo_row,
            $estado,
            $cloud_sync_enabled,
            $ultima_sincronizacion,
            $created_at,
            $updated_at
        );
        while (mysqli_stmt_fetch($stmt)) {
            $devices[] = [
                'id' => $id,
                'nombre_optica' => $nombre_optica,
                'ciudad' => $ciudad,
                'codigo_dispositivo' => $codigo_row,
                'estado' => strtolower((string)$estado),
                'cloud_sync_enabled' => (bool)$cloud_sync_enabled,
                'ultima_sincronizacion' => $ultima_sincronizacion,
                'created_at' => $created_at,
                'updated_at' => $updated_at
            ];
        }
    }

    mysqli_stmt_close($stmt);

    // Intentar leer el limite de sucursales desde tabla usuarios.
    // Fallback: al menos el total actual para no romper UI.
    $max_sucursales = max(1, count($devices));
    $limit_source = 'fallback_total';
    $limit_stmt = @mysqli_prepare(
        $conn,
        "SELECT max_sucursales
         FROM usuarios
         WHERE usuario = ? OR dni = ? OR CAST(id AS CHAR) = ?
         LIMIT 1"
    );
    if ($limit_stmt) {
        @mysqli_stmt_bind_param($limit_stmt, 'sss', $usuario_madre, $usuario_madre, $usuario_madre);
        @mysqli_stmt_execute($limit_stmt);

        $limit_row = null;
        if (function_exists('mysqli_stmt_get_result')) {
            $limit_result = @mysqli_stmt_get_result($limit_stmt);
            $limit_row = $limit_result ? @mysqli_fetch_assoc($limit_result) : null;
        } else {
            @mysqli_stmt_bind_result($limit_stmt, $max_val);
            if (@mysqli_stmt_fetch($limit_stmt)) {
                $limit_row = ['max_sucursales' => $max_val];
            }
        }

        if (is_array($limit_row) && isset($limit_row['max_sucursales'])) {
            $parsed_limit = (int)$limit_row['max_sucursales'];
            if ($parsed_limit > 0) {
                $max_sucursales = $parsed_limit;
                $limit_source = 'db_usuarios';
            }
        }
        @mysqli_stmt_close($limit_stmt);
    }

    mysqli_close($conn);

    respond([
        'success' => true,
        'dispositivos' => $devices,
        'total' => count($devices),
        'max_sucursales' => $max_sucursales,
        'cupos_disponibles' => max(0, $max_sucursales - count($devices)),
        'max_sucursales_source' => $limit_source,
        'api_version' => 'sync_child_devices:new:2026-02-27-1'
    ]);
}

mysqli_close($conn);
respond([
    'success' => false,
    'error' => 'AcciÃ³n no soportada. Use: upsert, delete, validate o list'
], 400);

