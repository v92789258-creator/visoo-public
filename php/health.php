<?php
/**
 * VISO Simple Health Check
 * Ubicación: /public_html/health.php
 * 
 * Prueba conexión a BD y funciones básicas
 */

header('Content-Type: application/json; charset=utf-8');

$response = [];

// Test 1: PHP funciona
$response['php_version'] = phpversion();

// Test 2: PDO disponible
$response['pdo_available'] = extension_loaded('pdo') ? 'sí' : 'no';

// Test 3: MySQL disponible
$response['mysql_available'] = extension_loaded('pdo_mysql') ? 'sí' : 'no';

// Test 4: Conectar a BD
try {
    $pdo = new PDO(
        "mysql:host=localhost;dbname=u369606320_visoo;charset=utf8mb4",
        'u369606320_visoo',
        getenv('VISO_DB_PASSWORD')
    );
    $response['bd_conexion'] = 'OK';
    
    // Test 5: Tabla existe
    $stmt = $pdo->query("SELECT COUNT(*) FROM usuarios");
    $count = $stmt->fetchColumn();
    $response['usuarios_tabla'] = "OK ($count registros)";
    
} catch (Exception $e) {
    $response['bd_error'] = $e->getMessage();
}

// Test 6: JSON encoding
$response['json_encode'] = 'OK';

http_response_code(200);
echo json_encode($response, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
?>
