<?php
/**
 * Endpoint para actualizar fechas de licencia
 * POST /api/win/update_license_dates.php
 * 
 * Actualiza la fecha de vigencia en tabla claves_activacion
 * Body JSON:
 * {
 *   "id_usuario": "45453073",
 *   "fecha_inicio": "2025-12-02",
 *   "fecha_vencimiento": "2026-12-02"
 * }
 */

header('Content-Type: application/json; charset=utf-8');

try {
    // Obtener datos del request
    $input = json_decode(file_get_contents('php://input'), true);
    
    if (!$input) {
        http_response_code(400);
        echo json_encode(['error' => 'Request vacío']);
        exit;
    }
    
    $id_usuario = $input['id_usuario'] ?? null;
    $fecha_vencimiento = $input['fecha_vencimiento'] ?? null;
    $fecha_inicio = $input['fecha_inicio'] ?? null;
    
    // Validar campos
    if (!$id_usuario || !$fecha_vencimiento) {
        http_response_code(400);
        echo json_encode(['error' => 'Faltan id_usuario o fecha_vencimiento']);
        exit;
    }
    
    // Validar formato de fechas
    if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $fecha_vencimiento)) {
        http_response_code(400);
        echo json_encode(['error' => 'Formato de fecha inválido']);
        exit;
    }
    
    // Conectar a BD
    $db_host = 'localhost';
    $db_user = 'u369606320_visoo';
    $db_pass = getenv('VISO_DB_PASSWORD');
    $db_name = 'u369606320_visoo';
    
    $conn = new mysqli($db_host, $db_user, $db_pass, $db_name);
    
    if ($conn->connect_error) {
        http_response_code(500);
        echo json_encode(['error' => 'Error de conexión']);
        exit;
    }
    
    $conn->set_charset("utf8mb4");
    
    // Buscar el usuario y obtener su clave_usada
    $stmt = $conn->prepare("SELECT clave_usada FROM usuarios WHERE dni = ? OR id = ? LIMIT 1");
    $stmt->bind_param("ss", $id_usuario, $id_usuario);
    $stmt->execute();
    $result = $stmt->get_result();
    
    if ($result->num_rows === 0) {
        http_response_code(404);
        echo json_encode(['error' => 'Usuario no encontrado']);
        $stmt->close();
        $conn->close();
        exit;
    }
    
    $user = $result->fetch_assoc();
    $clave_usada = $user['clave_usada'];
    $stmt->close();
    
    if (!$clave_usada) {
        http_response_code(400);
        echo json_encode(['error' => 'Usuario sin clave asignada']);
        $conn->close();
        exit;
    }
    
    // Actualizar vigencia en claves_activacion
    $estado = 'vigente';
    $stmt = $conn->prepare("
        UPDATE claves_activacion
        SET vigencia = ?, estado = ?
        WHERE clave_usada = ?
    ");
    
    $stmt->bind_param("sss", $fecha_vencimiento, $estado, $clave_usada);
    
    if ($stmt->execute()) {
        http_response_code(200);
        echo json_encode([
            'success' => true,
            'message' => 'Fechas actualizadas correctamente',
            'data' => [
                'id_usuario' => $id_usuario,
                'fecha_vencimiento' => $fecha_vencimiento,
                'estado' => $estado
            ]
        ]);
    } else {
        http_response_code(500);
        echo json_encode(['error' => 'Error al actualizar: ' . $stmt->error]);
    }
    
    $stmt->close();
    $conn->close();
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Excepción: ' . $e->getMessage()]);
}
?>
