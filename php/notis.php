<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Configuración de la base de datos
$db_host = 'localhost';
$db_user = 'u369606320_visoo';
$db_pass = getenv('VISO_DB_PASSWORD');
$db_name = 'u369606320_visoo';

// Conectar a la base de datos
try {
    $conn = new mysqli($db_host, $db_user, $db_pass, $db_name);
    
    // Verificar conexión
    if ($conn->connect_error) {
        http_response_code(500);
        echo json_encode([
            'error' => 'Error de conexión a la base de datos',
            'message' => $conn->connect_error
        ]);
        exit;
    }
    
    // Configurar charset
    $conn->set_charset("utf8mb4");
    
    // Obtener notificaciones activas (ordenadas por fecha descendente)
    $sql = "SELECT id, titulo, mensaje, tipo, enlace, accion, fecha_creacion 
            FROM notificaciones 
            WHERE activo = 1 
            ORDER BY fecha_creacion DESC 
            LIMIT 50";
    
    $result = $conn->query($sql);
    
    if (!$result) {
        http_response_code(500);
        echo json_encode([
            'error' => 'Error en la consulta',
            'message' => $conn->error
        ]);
        exit;
    }
    
    $notificaciones = array();
    
    while ($row = $result->fetch_assoc()) {
        $notificaciones[] = [
            'id' => (int)$row['id'],
            'titulo' => $row['titulo'],
            'mensaje' => $row['mensaje'],
            'tipo' => $row['tipo'],
            'enlace' => $row['enlace'],
            'accion' => $row['accion'],
            'fecha' => $row['fecha_creacion']
        ];
    }
    
    // Devolver respuesta exitosa
    http_response_code(200);
    echo json_encode($notificaciones, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
    
    $conn->close();
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'error' => 'Error inesperado',
        'message' => $e->getMessage()
    ]);
}
?>
