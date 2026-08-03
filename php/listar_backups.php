<?php
/**
 * Endpoint para listar backups de un usuario
 * POST /api/win/listar_backups.php
 * 
 * Parámetros:
 * - id: ID del usuario
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
    
    if (!$user_id) {
        http_response_code(400);
        echo json_encode(['error' => 'Falta el parámetro id']);
        exit;
    }
    
    // Conectar a la base de datos con credenciales
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
    
    // Tabla de backups: id, usuario_id, filename, upload_date, file_size, status
    // Si la tabla no existe, crearla
    $create_table = "
        CREATE TABLE IF NOT EXISTS backups (
            id INT AUTO_INCREMENT PRIMARY KEY,
            usuario_id VARCHAR(50) NOT NULL,
            filename VARCHAR(255) NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_size BIGINT,
            md5_hash VARCHAR(32),
            status ENUM('active', 'deleted') DEFAULT 'active',
            INDEX idx_usuario (usuario_id),
            INDEX idx_date (upload_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    ";
    
    $conn->query($create_table);
    
    // Listar backups activos del usuario, ordenados por fecha descendente
    $stmt = $conn->prepare("
        SELECT filename, upload_date, file_size, md5_hash 
        FROM backups 
        WHERE usuario_id = ? AND status = 'active' 
        ORDER BY upload_date DESC 
        LIMIT 10
    ");
    
    if (!$stmt) {
        http_response_code(500);
        echo json_encode(['error' => 'Error en consulta: ' . $conn->error]);
        exit;
    }
    
    $stmt->bind_param("s", $user_id);
    $stmt->execute();
    
    $result = $stmt->get_result();
    $files = [];
    
    while ($row = $result->fetch_assoc()) {
        $files[] = [
            'filename' => $row['filename'],
            'date' => $row['upload_date'],
            'size' => $row['file_size'],
            'md5' => $row['md5_hash']
        ];
    }
    
    $stmt->close();
    $conn->close();
    
    http_response_code(200);
    echo json_encode([
        'success' => true,
        'usuario_id' => $user_id,
        'files' => $files,
        'count' => count($files)
    ]);
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Error: ' . $e->getMessage()]);
}
?>
