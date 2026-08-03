<?php
/**
 * LOGIN VISO - Versión MÍNIMA para debugging
 * Si esto funciona, el servidor está OK
 */

header('Content-Type: application/json; charset=utf-8');

// Config
$db_host = 'localhost';
$db_user = 'u369606320_visoo';
$db_pass = getenv('VISO_DB_PASSWORD');
$db_name = 'u369606320_visoo';

// Test 1: BD
try {
    $pdo = new PDO(
        'mysql:host=' . $db_host . ';dbname=' . $db_name . ';charset=utf8mb4',
        $db_user,
        $db_pass,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
    
    $respuesta = ['estado' => 'ok', 'mensaje' => 'BD conectada'];
    http_response_code(200);
    echo json_encode($respuesta);
    
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode([
        'estado' => 'error',
        'error' => $e->getMessage(),
        'host' => $db_host,
        'user' => $db_user,
        'db' => $db_name
    ]);
}

?>
