<?php
header("Content-Type: application/json; charset=utf-8");
header("Access-Control-Allow-Origin: *");

$db_host = "localhost";
$db_user = "u369606320_visoo";
$db_pass = getenv('VISO_DB_PASSWORD');
$db_name = "u369606320_visoo";

$usuario_madre = $_GET["usuario"] ?? "";

if (!$usuario_madre) {
    echo json_encode(["status" => "error", "message" => "Usuario no proporcionado"]);
    exit;
}

try {
    $pdo = new PDO("mysql:host=$db_host;dbname=$db_name;charset=utf8mb4", $db_user, $db_pass, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
    
    // BÚSQUEDA REAL EN dispositivos_hijos
    $stmt = $pdo->prepare("SELECT id, nombre_optica, ciudad, codigo_dispositivo, estado FROM dispositivos_hijos WHERE usuario_madre = ? AND estado = \"activo\"");
    $stmt->execute([$usuario_madre]);
    $sucursales = $stmt->fetchAll(PDO::FETCH_ASSOC);

    echo json_encode([
        "status" => "success",
        "sucursales" => $sucursales
    ]);

} catch (PDOException $e) {
    echo json_encode(["status" => "error", "message" => $e->getMessage()]);
}