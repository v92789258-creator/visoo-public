<?php
header('Content-Type: application/json; charset=utf-8');

try {
    error_log("BACKUP: Inicio");
    
    $user_id = $_SERVER['HTTP_X_USER_VISO'] ?? null;
    error_log("BACKUP: user_id = " . ($user_id ?? 'NULL'));
    
    if (!$user_id) {
        http_response_code(400);
        echo json_encode(['error' => 'Falta ID']);
        error_log("BACKUP: Error - sin ID");
        exit;
    }
    
    if (!isset($_FILES['archivo'])) {
        http_response_code(400);
        echo json_encode(['error' => 'Sin archivo']);
        error_log("BACKUP: Error - sin archivo");
        exit;
    }
    
    $file = $_FILES['archivo'];
    error_log("BACKUP: Archivo recibido: " . $file['name'] . ", error=" . $file['error']);
    
    if ($file['error'] != UPLOAD_ERR_OK) {
        http_response_code(400);
        echo json_encode(['error' => 'Error en upload']);
        exit;
    }
    
    // BD
    @$conn = new mysqli('localhost', 'u369606320_visoo', getenv('VISO_DB_PASSWORD'), 'u369606320_visoo');
    
    if (!$conn || $conn->connect_error) {
        error_log("BACKUP: Error BD");
        http_response_code(500);
        echo json_encode(['error' => 'Error BD']);
        exit;
    }
    
    $conn->set_charset("utf8mb4");
    
    // Crear tabla
    $sql = "CREATE TABLE IF NOT EXISTS backups (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario_id VARCHAR(50),
        filename VARCHAR(255),
        upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        file_size BIGINT,
        md5_hash VARCHAR(32),
        status VARCHAR(20) DEFAULT 'active',
        INDEX idx_usuario (usuario_id)
    )";
    
    @$conn->query($sql);
    error_log("BACKUP: Tabla creada/verificada");
    
    // Directorio
    $base = dirname(__FILE__) . '/../backups';
    @mkdir($base, 0777, true);
    
    $user_safe = substr(preg_replace('/[^a-z0-9]/i', '', $user_id), 0, 50);
    $dir = $base . '/' . $user_safe;
    @mkdir($dir, 0777, true);
    
    error_log("BACKUP: Directorio = $dir");
    
    // Archivo - Usar el nombre original del archivo enviado
    $fn = $file['name'];
    $path = $dir . '/' . $fn;
    
    error_log("BACKUP: Moviendo archivo a $path");
    
    if (!move_uploaded_file($file['tmp_name'], $path)) {
        http_response_code(500);
        echo json_encode(['error' => 'Error moving']);
        error_log("BACKUP: Error al mover");
        exit;
    }
    
    // BD insert
    $size = filesize($path);
    $md5 = md5_file($path);
    
    $stmt = $conn->prepare("INSERT INTO backups (usuario_id, filename, file_size, md5_hash, status) VALUES (?, ?, ?, ?, 'active')");
    
    if (!$stmt) {
        error_log("BACKUP: Error prepare: " . $conn->error);
        http_response_code(500);
        echo json_encode(['error' => 'Prepare error']);
        exit;
    }
    
    $types = "ssds";
    $stmt->bind_param($types, $user_id, $fn, $size, $md5);
    
    if (!$stmt->execute()) {
        error_log("BACKUP: Error execute: " . $stmt->error);
        http_response_code(500);
        echo json_encode(['error' => 'Execute error']);
        exit;
    }
    
    $id = $stmt->insert_id;
    $stmt->close();
    $conn->close();
    
    http_response_code(201);
    echo json_encode(['success' => true, 'message' => 'OK', 'id' => $id, 'filename' => $fn, 'size' => $size]);
    error_log("BACKUP: Éxito - ID=$id");
    
} catch (Throwable $e) {
    http_response_code(500);
    echo json_encode(['error' => $e->getMessage()]);
    error_log("BACKUP: Exception - " . $e->getMessage());
}
?>
