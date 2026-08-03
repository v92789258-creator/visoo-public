<?php
/**
 * Endpoint para borrar un backup específico
 * POST /api/win/borrar_backup.php
 * 
 * Parámetros:
 * - id: ID del usuario
 * - filename: Nombre del archivo a borrar
 */

header('Content-Type: application/json; charset=utf-8');

try {
    // Obtener datos del request
    $data = file_get_contents('php://input');
    parse_str($data, $input);
    
    if (empty($input) && !isset($_POST['id'])) {
        $input = $_POST;
    }
    
    $user_id = $input['id'] ?? $_POST['id'] ?? null;
    $filename = $input['filename'] ?? $_POST['filename'] ?? null;
    
    if (!$user_id || !$filename) {
        http_response_code(400);
        echo json_encode(['error' => 'Faltan parámetros: id y filename']);
        exit;
    }
    
    // Conectar a la base de datos
    $db_host = 'localhost';
    $db_user = 'u369606320_visoo';
    $db_pass = getenv('VISO_DB_PASSWORD');
    $db_name = 'u369606320_visoo';
    
    $conn = new mysqli($db_host, $db_user, $db_pass, $db_name);
    
    if ($conn->connect_error) {
        http_response_code(500);
        echo json_encode(['error' => 'Error de conexión a BD']);
        exit;
    }
    
    $conn->set_charset("utf8mb4");
    
    // Buscar el archivo (activo o no) - más flexible
    $verify_stmt = $conn->prepare("
        SELECT id FROM backups 
        WHERE usuario_id = ? AND filename = ? 
        LIMIT 1
    ");
    
    if (!$verify_stmt) {
        http_response_code(500);
        echo json_encode(['error' => 'Error en consulta']);
        exit;
    }
    
    $verify_stmt->bind_param("ss", $user_id, $filename);
    $verify_stmt->execute();
    
    $result = $verify_stmt->get_result();
    
    if ($result->num_rows == 0) {
        $verify_stmt->close();
        $conn->close();
        http_response_code(404);
        echo json_encode(['error' => 'Backup no encontrado']);
        exit;
    }
    
    $verify_stmt->close();
    
    // Marcar como deleted en lugar de borrar realmente
    $delete_stmt = $conn->prepare("
        UPDATE backups 
        SET status = 'deleted' 
        WHERE usuario_id = ? AND filename = ?
    ");
    
    if (!$delete_stmt) {
        http_response_code(500);
        echo json_encode(['error' => 'Error en actualización']);
        exit;
    }
    
    $delete_stmt->bind_param("ss", $user_id, $filename);
    $success = $delete_stmt->execute();
    
    $delete_stmt->close();
    $conn->close();
    
    if ($success) {
        http_response_code(200);
        echo json_encode([
            'success' => true,
            'message' => "Backup '$filename' marcado como eliminado",
            'usuario_id' => $user_id
        ]);
    } else {
        http_response_code(500);
        echo json_encode(['error' => 'No se pudo marcar el backup como eliminado']);
    }
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Error: ' . $e->getMessage()]);
}
?>
