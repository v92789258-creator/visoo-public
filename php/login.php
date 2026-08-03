<?php
header('Content-Type: text/plain; charset=utf-8');
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

function respond($status, $message) {
    http_response_code($status);
    echo $message;
    exit;
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
    respond(500, 'credenciales invalidas');
}

$input = json_decode(file_get_contents('php://input'), true);
if (!is_array($input)) {
    $input = [];
}

$username = trim((string)($_GET['user'] ?? $_GET['username'] ?? $_POST['user'] ?? $_POST['username'] ?? $input['user'] ?? $input['username'] ?? ''));
$password = trim((string)($_GET['pass'] ?? $_GET['password'] ?? $_POST['pass'] ?? $_POST['password'] ?? $input['pass'] ?? $input['password'] ?? ''));

if ($username === '' || $password === '') {
    respond(400, 'credenciales invalidas');
}

try {
    $stmt = $pdo->prepare("SELECT id, usuario, password, dni FROM usuarios WHERE usuario = ? LIMIT 1");
    $stmt->execute([$username]);
    $user = $stmt->fetch();

    if (!$user) {
        respond(401, 'credenciales invalidas');
    }

    $stored = (string)($user['password'] ?? '');
    $ok = false;

    if ($stored !== '') {
        $info = password_get_info($stored);
        if (!empty($info['algo'])) {
            $ok = password_verify($password, $stored);
        } else {
            $ok = hash_equals($stored, $password);
        }
    }

    if (!$ok) {
        respond(401, 'credenciales invalidas');
    }

    respond(200, 'usuario correcto iniciando secion');
} catch (Throwable $e) {
    respond(500, 'credenciales invalidas');
}
