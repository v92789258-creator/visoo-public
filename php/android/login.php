<?php
header("Content-Type: application/json; charset=utf-8");
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");

if ($_SERVER["REQUEST_METHOD"] === "OPTIONS") { exit; }

$db_host = "localhost";
$db_user = "u369606320_visoo";
$db_pass = getenv('VISO_DB_PASSWORD');
$db_name = "u369606320_visoo";

try {
    $pdo = new PDO("mysql:host=$db_host;dbname=$db_name;charset=utf8mb4", $db_user, $db_pass, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
} catch (PDOException $e) {
    echo json_encode(["status" => "error", "message" => "Error de conexión"]);
    exit;
}

$input = json_decode(file_get_contents("php://input"), true);
$username = trim($input["username"] ?? "");
$password = trim($input["password"] ?? "");

if (!$username || !$password) {
    echo json_encode(["status" => "error", "message" => "Usuario y clave requeridos"]);
    exit;
}

try {
    $stmt = $pdo->prepare("SELECT id, usuario, password, dni, nombres, activo FROM usuarios WHERE usuario = ? LIMIT 1");
    $stmt->execute([$username]);
    $user = $stmt->fetch(PDO::FETCH_ASSOC);

    if (!$user || !password_verify($password, $user["password"])) {
        echo json_encode(["status" => "error", "message" => "Credenciales incorrectas"]);
        exit;
    }

    if ((int)$user["activo"] === 0) {
        echo json_encode(["status" => "error", "message" => "Cuenta suspendida"]);
        exit;
    }

    // OBTENER SUCURSALES DEL USUARIO
    $stmt_suc = $pdo->prepare("SELECT id, nombre_optica, ciudad, codigo_dispositivo, estado FROM dispositivos_hijos WHERE usuario_madre = ? AND estado = \"activo\"");
    $stmt_suc->execute([$user["usuario"]]);
    $sucursales = $stmt_suc->fetchAll(PDO::FETCH_ASSOC);

    echo json_encode([
        "status" => "success",
        "message" => "Login exitoso",
        "user_id" => $user["dni"],
        "nombre" => $user["nombres"],
        "usuario" => $user["usuario"],
        "sucursales" => $sucursales
    ]);

} catch (PDOException $e) {
    echo json_encode(["status" => "error", "message" => "Error en el servidor: " . $e->getMessage()]);
}