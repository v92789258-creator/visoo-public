<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

$db_host = 'localhost';
$db_name = 'visoo';
$db_user = 'phpmyadmin';
$db_pass = getenv('VISO_DB_PASSWORD');

function respond($status, $data) {
    http_response_code($status);
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function column_exists($pdo, $table, $column) {
    $stmt = $pdo->prepare(
        "SELECT COUNT(*) 
         FROM information_schema.columns 
         WHERE table_schema = ? AND table_name = ? AND column_name = ?"
    );
    $stmt->execute(['visoo', $table, $column]);
    return (int)$stmt->fetchColumn() > 0;
}

try {
    $pdo = new PDO(
        "mysql:host={$db_host};dbname={$db_name};charset=utf8mb4",
        $db_user,
        $db_pass,
        [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]
    );
} catch (Throwable $e) {
    respond(500, [
        'success' => false,
        'error' => 'Error de conexión a BD',
    ]);
}

$input = json_decode(file_get_contents('php://input'), true);
if (!is_array($input)) {
    $input = [];
}

$username = trim((string)($_GET['user'] ?? $_GET['username'] ?? $_POST['user'] ?? $_POST['username'] ?? $input['user'] ?? $input['username'] ?? ''));
$password = trim((string)($_GET['pass'] ?? $_GET['password'] ?? $_POST['pass'] ?? $_POST['password'] ?? $input['pass'] ?? $input['password'] ?? ''));
$dni = trim((string)($_GET['dni'] ?? $_POST['dni'] ?? $input['dni'] ?? ''));

if ($username === '' || $password === '' || $dni === '') {
    respond(400, [
        'success' => false,
        'error' => 'Faltan user, pass o dni',
        'example' => '?user=cliente1&pass=123456&dni=12345678',
    ]);
}

if (strlen($username) < 3) {
    respond(400, [
        'success' => false,
        'error' => 'El usuario debe tener al menos 3 caracteres',
    ]);
}

if (strlen($password) < 4) {
    respond(400, [
        'success' => false,
        'error' => 'La contraseña debe tener al menos 4 caracteres',
    ]);
}

try {
    $stmt = $pdo->prepare("SELECT id FROM usuarios WHERE usuario = ? OR dni = ? LIMIT 1");
    $stmt->execute([$username, $dni]);
    if ($stmt->fetch()) {
        respond(409, [
            'success' => false,
            'error' => 'El usuario o DNI ya existe',
        ]);
    }

    $fields = ['usuario', 'password', 'dni'];
    $placeholders = ['?', '?', '?'];
    $values = [$username, password_hash($password, PASSWORD_BCRYPT), $dni];

    if (column_exists($pdo, 'usuarios', 'activo')) {
        $fields[] = 'activo';
        $placeholders[] = '?';
        $values[] = 1;
    }
    if (column_exists($pdo, 'usuarios', 'rol')) {
        $fields[] = 'rol';
        $placeholders[] = '?';
        $values[] = 'user';
    }
    if (column_exists($pdo, 'usuarios', 'apellidos')) {
        $fields[] = 'apellidos';
        $placeholders[] = '?';
        $values[] = '';
    }
    if (column_exists($pdo, 'usuarios', 'nombres')) {
        $fields[] = 'nombres';
        $placeholders[] = '?';
        $values[] = $username;
    }
    if (column_exists($pdo, 'usuarios', 'correo')) {
        $fields[] = 'correo';
        $placeholders[] = '?';
        $values[] = '';
    }
    if (column_exists($pdo, 'usuarios', 'respaldo')) {
        $fields[] = 'respaldo';
        $placeholders[] = '?';
        $values[] = 0;
    }
    if (column_exists($pdo, 'usuarios', 'clave_activacion')) {
        $fields[] = 'clave_activacion';
        $placeholders[] = '?';
        $values[] = '';
    }
    if (column_exists($pdo, 'usuarios', 'clave_usada')) {
        $fields[] = 'clave_usada';
        $placeholders[] = '?';
        $values[] = '';
    }

    $sql = "INSERT INTO usuarios (" . implode(', ', $fields) . ") VALUES (" . implode(', ', $placeholders) . ")";
    $stmt = $pdo->prepare($sql);
    $stmt->execute($values);

    respond(201, [
        'success' => true,
        'message' => 'Cuenta creada correctamente',
        'username' => $username,
        'dni' => $dni,
    ]);
} catch (Throwable $e) {
    respond(500, [
        'success' => false,
        'error' => 'Error al crear cuenta: ' . $e->getMessage(),
    ]);
}
