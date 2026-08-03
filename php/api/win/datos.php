<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

function respond($payload, $status = 200) {
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_UNICODE);
    exit;
}

$conn = @mysqli_connect('localhost', 'phpmyadmin', getenv('VISO_DB_PASSWORD'), 'visoo');
if (!$conn) {
    respond([
        'success' => false,
        'error' => 'Conexion BD: ' . mysqli_connect_error(),
    ], 500);
}
@mysqli_set_charset($conn, 'utf8mb4');

$create_table_sql = "
CREATE TABLE IF NOT EXISTS datos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_ref VARCHAR(255) NOT NULL,
    usuario_id VARCHAR(255) NOT NULL DEFAULT '',
    username VARCHAR(255) NOT NULL DEFAULT '',
    nombre_optica VARCHAR(255) NOT NULL DEFAULT '',
    slogan VARCHAR(255) NOT NULL DEFAULT '',
    direccion TEXT NULL,
    correo_electronico VARCHAR(255) NOT NULL DEFAULT '',
    whatsapp VARCHAR(64) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_datos_usuario_ref (usuario_ref),
    KEY idx_datos_usuario_id (usuario_id),
    KEY idx_datos_username (username)
)";

if (!@mysqli_query($conn, $create_table_sql)) {
    respond([
        'success' => false,
        'error' => 'No se pudo crear tabla datos: ' . mysqli_error($conn),
    ], 500);
}

$raw = file_get_contents('php://input');
$input = json_decode($raw, true);
if (!is_array($input)) {
    $input = $_POST;
}

$action = strtolower(trim((string)($input['action'] ?? 'get')));
$usuario_id = trim((string)($input['usuario_id'] ?? ''));
$username = trim((string)($input['username'] ?? ''));
$usuario_ref = trim((string)($input['usuario_ref'] ?? ''));
if ($usuario_ref === '') {
    $usuario_ref = $username !== '' ? $username : $usuario_id;
}

if ($usuario_ref === '' && $action !== 'schema') {
    respond([
        'success' => false,
        'error' => 'Falta usuario_ref/usuario_id/username',
    ], 400);
}

if ($action === 'schema') {
    respond([
        'success' => true,
        'message' => 'Tabla datos lista',
    ]);
}

if ($action === 'get') {
    $sql = "
        SELECT id, usuario_ref, usuario_id, username, nombre_optica, slogan, direccion,
               correo_electronico, whatsapp, created_at, updated_at
        FROM datos
        WHERE usuario_ref = ? OR usuario_id = ? OR username = ?
        ORDER BY id DESC
        LIMIT 1
    ";
    $stmt = @mysqli_prepare($conn, $sql);
    if (!$stmt) {
        respond([
            'success' => false,
            'error' => 'Error preparando consulta: ' . mysqli_error($conn),
        ], 500);
    }
    @mysqli_stmt_bind_param($stmt, 'sss', $usuario_ref, $usuario_id, $username);
    @mysqli_stmt_execute($stmt);
    $result = function_exists('mysqli_stmt_get_result') ? @mysqli_stmt_get_result($stmt) : false;
    $row = $result ? @mysqli_fetch_assoc($result) : null;
    @mysqli_stmt_close($stmt);

    respond([
        'success' => true,
        'found' => is_array($row),
        'datos' => is_array($row) ? $row : new stdClass(),
    ]);
}

if ($action === 'upsert') {
    $nombre_optica = trim((string)($input['nombre_optica'] ?? ''));
    $slogan = trim((string)($input['slogan'] ?? ''));
    $direccion = trim((string)($input['direccion'] ?? ''));
    $correo_electronico = trim((string)($input['correo_electronico'] ?? ''));
    $whatsapp = trim((string)($input['whatsapp'] ?? ''));

    $lookup_sql = "SELECT id FROM datos WHERE usuario_ref = ? OR usuario_id = ? OR username = ? ORDER BY id DESC LIMIT 1";
    $lookup_stmt = @mysqli_prepare($conn, $lookup_sql);
    if (!$lookup_stmt) {
        respond([
            'success' => false,
            'error' => 'Error preparando lookup: ' . mysqli_error($conn),
        ], 500);
    }
    @mysqli_stmt_bind_param($lookup_stmt, 'sss', $usuario_ref, $usuario_id, $username);
    @mysqli_stmt_execute($lookup_stmt);
    $lookup_result = function_exists('mysqli_stmt_get_result') ? @mysqli_stmt_get_result($lookup_stmt) : false;
    $existing = $lookup_result ? @mysqli_fetch_assoc($lookup_result) : null;
    @mysqli_stmt_close($lookup_stmt);

    if (is_array($existing) && isset($existing['id'])) {
        $id = (int)$existing['id'];
        $update_sql = "
            UPDATE datos
            SET usuario_ref = ?, usuario_id = ?, username = ?, nombre_optica = ?, slogan = ?,
                direccion = ?, correo_electronico = ?, whatsapp = ?, updated_at = NOW()
            WHERE id = ?
        ";
        $stmt = @mysqli_prepare($conn, $update_sql);
        if (!$stmt) {
            respond([
                'success' => false,
                'error' => 'Error preparando update: ' . mysqli_error($conn),
            ], 500);
        }
        @mysqli_stmt_bind_param(
            $stmt,
            'ssssssssi',
            $usuario_ref,
            $usuario_id,
            $username,
            $nombre_optica,
            $slogan,
            $direccion,
            $correo_electronico,
            $whatsapp,
            $id
        );
        $ok = @mysqli_stmt_execute($stmt);
        $err = @mysqli_stmt_error($stmt);
        @mysqli_stmt_close($stmt);
        if (!$ok) {
            respond([
                'success' => false,
                'error' => 'Error actualizando datos: ' . $err,
            ], 500);
        }
    } else {
        $insert_sql = "
            INSERT INTO datos (
                usuario_ref, usuario_id, username, nombre_optica, slogan,
                direccion, correo_electronico, whatsapp, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NOW(), NOW())
        ";
        $stmt = @mysqli_prepare($conn, $insert_sql);
        if (!$stmt) {
            respond([
                'success' => false,
                'error' => 'Error preparando insert: ' . mysqli_error($conn),
            ], 500);
        }
        @mysqli_stmt_bind_param(
            $stmt,
            'ssssssss',
            $usuario_ref,
            $usuario_id,
            $username,
            $nombre_optica,
            $slogan,
            $direccion,
            $correo_electronico,
            $whatsapp
        );
        $ok = @mysqli_stmt_execute($stmt);
        $err = @mysqli_stmt_error($stmt);
        @mysqli_stmt_close($stmt);
        if (!$ok) {
            respond([
                'success' => false,
                'error' => 'Error insertando datos: ' . $err,
            ], 500);
        }
    }

    respond([
        'success' => true,
        'message' => 'Datos guardados correctamente',
        'datos' => [
            'usuario_ref' => $usuario_ref,
            'usuario_id' => $usuario_id,
            'username' => $username,
            'nombre_optica' => $nombre_optica,
            'slogan' => $slogan,
            'direccion' => $direccion,
            'correo_electronico' => $correo_electronico,
            'whatsapp' => $whatsapp,
        ],
    ]);
}

respond([
    'success' => false,
    'error' => 'Accion no valida',
], 400);
