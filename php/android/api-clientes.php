<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

$db_host = 'localhost';
$db_user = 'u369606320_visoo';
$db_pass = getenv('VISO_DB_PASSWORD');
$db_name = 'u369606320_visoo';

function respond(int $status, array $payload): void
{
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_UNICODE);
    exit;
}

function read_json_body(): array
{
    $raw = file_get_contents('php://input');
    $data = json_decode($raw, true);
    return is_array($data) ? $data : [];
}

function normalize_date(?string $value): ?string
{
    $value = trim((string)$value);
    if ($value === '') {
        return null;
    }

    if (preg_match('/^\d{2}\/\d{2}\/\d{4}$/', $value)) {
        [$day, $month, $year] = explode('/', $value);
        if (checkdate((int)$month, (int)$day, (int)$year)) {
            return sprintf('%04d-%02d-%02d', (int)$year, (int)$month, (int)$day);
        }
    }

    if (preg_match('/^\d{4}-\d{2}-\d{2}$/', $value)) {
        [$year, $month, $day] = explode('-', $value);
        if (checkdate((int)$month, (int)$day, (int)$year)) {
            return $value;
        }
    }

    return null;
}

function calculate_age(?string $birthDate): ?int
{
    if (!$birthDate) {
        return null;
    }

    try {
        $birth = new DateTime($birthDate);
        $today = new DateTime('today');
        return $birth->diff($today)->y;
    } catch (Throwable $e) {
        return null;
    }
}

try {
    $pdo = new PDO(
        "mysql:host=$db_host;dbname=$db_name;charset=utf8mb4",
        $db_user,
        $db_pass,
        [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]
    );
} catch (Throwable $e) {
    respond(500, ['success' => false, 'error' => 'No se pudo conectar a la base de datos']);
}

try {
    $pdo->exec("
        CREATE TABLE IF NOT EXISTS clientes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            id_usuario VARCHAR(50) NOT NULL,
            nombre VARCHAR(150) NOT NULL,
            dni VARCHAR(8) NOT NULL,
            edad INT NULL DEFAULT NULL,
            genero VARCHAR(20) NULL DEFAULT NULL,
            fecha_nacimiento DATE NULL DEFAULT NULL,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_clientes_usuario (id_usuario),
            INDEX idx_clientes_dni (dni),
            UNIQUE KEY unique_usuario_dni (id_usuario, dni)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ");
} catch (Throwable $e) {
    respond(500, ['success' => false, 'error' => 'No se pudo preparar la tabla clientes']);
}

$method = $_SERVER['REQUEST_METHOD'];
$input = read_json_body();

if ($method === 'GET') {
    $usuarioId = trim((string)($_GET['usuario_id'] ?? $input['usuario_id'] ?? ''));
    $query = trim((string)($_GET['query'] ?? $input['query'] ?? ''));

    if ($usuarioId === '') {
        respond(400, ['success' => false, 'error' => 'usuario_id requerido']);
    }

    $sql = "SELECT id, id_usuario, nombre, dni, edad, genero, fecha_nacimiento, fecha_registro, fecha_actualizacion
            FROM clientes
            WHERE id_usuario = :usuario_id";
    $params = [':usuario_id' => $usuarioId];

    if ($query !== '') {
        $sql .= " AND (dni LIKE :query OR nombre LIKE :query)";
        $params[':query'] = '%' . $query . '%';
    }

    $sql .= " ORDER BY fecha_actualizacion DESC";
    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);

    $clientes = array_map(static function (array $row): array {
        return [
            'id' => (int)$row['id'],
            'id_usuario' => $row['id_usuario'],
            'nombre' => $row['nombre'],
            'nombre_completo' => $row['nombre'],
            'dni' => $row['dni'],
            'edad' => $row['edad'] !== null ? (int)$row['edad'] : null,
            'genero' => $row['genero'] ?? '',
            'fecha_nacimiento' => $row['fecha_nacimiento'] ?? '',
            'fecha_registro' => $row['fecha_registro'] ?? '',
            'fecha_actualizacion' => $row['fecha_actualizacion'] ?? '',
        ];
    }, $stmt->fetchAll());

    echo json_encode($clientes, JSON_UNESCAPED_UNICODE);
    exit;
}

if ($method === 'POST' || $method === 'PUT') {
    $usuarioId = trim((string)($input['usuario_id'] ?? ''));
    $dni = trim((string)($input['dni'] ?? ''));
    $nombre = trim((string)($input['nombre_completo'] ?? $input['nombre'] ?? ''));
    $genero = trim((string)($input['genero'] ?? ''));
    $fechaNacimiento = normalize_date($input['fecha_nacimiento'] ?? null);

    if ($usuarioId === '' || $dni === '' || $nombre === '') {
        respond(400, ['success' => false, 'error' => 'Faltan usuario_id, dni o nombre']);
    }

    if (!preg_match('/^\d{8}$/', $dni)) {
        respond(400, ['success' => false, 'error' => 'DNI inválido']);
    }

    if (($input['fecha_nacimiento'] ?? '') !== '' && $fechaNacimiento === null) {
        respond(400, ['success' => false, 'error' => 'Fecha inválida, usa dd/MM/yyyy']);
    }

    $edad = calculate_age($fechaNacimiento);

    $stmtUser = $pdo->prepare("SELECT id FROM usuarios WHERE usuario = ? OR dni = ? OR CAST(id AS CHAR) = ? LIMIT 1");
    $stmtUser->execute([$usuarioId, $usuarioId, $usuarioId]);
    if (!$stmtUser->fetch()) {
        respond(404, ['success' => false, 'error' => "Usuario no encontrado: $usuarioId"]);
    }

    if ($method === 'POST') {
        $stmt = $pdo->prepare("
            INSERT INTO clientes (id_usuario, nombre, dni, edad, genero, fecha_nacimiento)
            VALUES (:usuario_id, :nombre, :dni, :edad, :genero, :fecha_nacimiento)
            ON DUPLICATE KEY UPDATE
                nombre = VALUES(nombre),
                edad = VALUES(edad),
                genero = VALUES(genero),
                fecha_nacimiento = VALUES(fecha_nacimiento),
                fecha_actualizacion = CURRENT_TIMESTAMP
        ");
        $stmt->execute([
            ':usuario_id' => $usuarioId,
            ':nombre' => $nombre,
            ':dni' => $dni,
            ':edad' => $edad,
            ':genero' => $genero !== '' ? $genero : null,
            ':fecha_nacimiento' => $fechaNacimiento,
        ]);

        respond(200, [
            'success' => true,
            'message' => 'Cliente guardado',
            'dni' => $dni,
            'usuario_id' => $usuarioId,
        ]);
    }

    $stmt = $pdo->prepare("
        UPDATE clientes
        SET nombre = :nombre,
            edad = :edad,
            genero = :genero,
            fecha_nacimiento = :fecha_nacimiento,
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE id_usuario = :usuario_id AND dni = :dni
    ");
    $stmt->execute([
        ':usuario_id' => $usuarioId,
        ':nombre' => $nombre,
        ':dni' => $dni,
        ':edad' => $edad,
        ':genero' => $genero !== '' ? $genero : null,
        ':fecha_nacimiento' => $fechaNacimiento,
    ]);

    if ($stmt->rowCount() === 0) {
        respond(404, ['success' => false, 'error' => 'Cliente no encontrado para actualizar']);
    }

    respond(200, [
        'success' => true,
        'message' => 'Cliente actualizado',
        'dni' => $dni,
        'usuario_id' => $usuarioId,
    ]);
}

if ($method === 'DELETE') {
    $usuarioId = trim((string)($_GET['usuario_id'] ?? $input['usuario_id'] ?? ''));
    $dni = trim((string)($_GET['dni'] ?? $input['dni'] ?? ''));

    if ($usuarioId === '' || $dni === '') {
        respond(400, ['success' => false, 'error' => 'usuario_id y dni requeridos']);
    }

    $stmt = $pdo->prepare("DELETE FROM clientes WHERE id_usuario = ? AND dni = ?");
    $stmt->execute([$usuarioId, $dni]);

    if ($stmt->rowCount() === 0) {
        respond(404, ['success' => false, 'error' => 'Cliente no encontrado']);
    }

    respond(200, [
        'success' => true,
        'message' => 'Cliente eliminado',
        'dni' => $dni,
        'usuario_id' => $usuarioId,
    ]);
}

respond(405, ['success' => false, 'error' => 'Método no permitido']);
