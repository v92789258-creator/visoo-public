<?php
/**
 * Endpoint para verificar estado de la licencia
 * POST /api/win/check_license_status.php
 * 
 * Versión independiente con credenciales embebidas
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
    $username = $input['username'] ?? null;
    
    if (!$id_usuario && !$username) {
        http_response_code(400);
        echo json_encode(['error' => 'Falta id_usuario o username']);
        exit;
    }
    
    // Conectar a la base de datos con credenciales directas
    $db_host = 'localhost';
    $db_user = 'u369606320_visoo';
    $db_pass = getenv('VISO_DB_PASSWORD');
    $db_name = 'u369606320_visoo';
    
    $conn = new mysqli($db_host, $db_user, $db_pass, $db_name);
    
    if ($conn->connect_error) {
        http_response_code(500);
        echo json_encode(['error' => 'Error de conexión: ' . $conn->connect_error]);
        exit;
    }
    
    $conn->set_charset("utf8mb4");
    
    // Buscar el usuario
    $user_id = $id_usuario;
    if (!$id_usuario && $username) {
        $stmt = $conn->prepare("SELECT dni FROM usuarios WHERE usuario = ? LIMIT 1");
        $stmt->bind_param("s", $username);
        $stmt->execute();
        $result = $stmt->get_result();
        if ($result->num_rows === 0) {
            http_response_code(200);
            echo json_encode([
                'active' => false,
                'dias_restantes' => 0,
                'vigencia' => 'No asignada',
                'estado' => 'usuario_no_encontrado',
                'message' => 'Usuario no encontrado'
            ]);
            $stmt->close();
            $conn->close();
            exit;
        }
        $user = $result->fetch_assoc();
        $user_id = $user['dni'];
        $stmt->close();
    }
    
    // Buscar la licencia del usuario en claves_activacion
    $stmt = $conn->prepare("
        SELECT 
            id_usuario,
            fecha_inicio,
            vencimiento,
            estado,
            plan_type,
            DATEDIFF(vencimiento, CURDATE()) as dias_restantes
        FROM claves_activacion
        WHERE id_usuario = ?
        LIMIT 1
    ");
    
    if (!$stmt) {
        http_response_code(500);
        echo json_encode(['error' => 'Error en query: ' . $conn->error]);
        $conn->close();
        exit;
    }
    
    $stmt->bind_param("s", $user_id);
    $stmt->execute();
    $result = $stmt->get_result();
    
    if ($result->num_rows === 0) {
        // No hay licencia registrada
        http_response_code(200);
        echo json_encode([
            'active' => false,
            'dias_restantes' => 0,
            'vigencia' => 'No asignada',
            'estado' => 'sin_licencia',
            'plan_type' => 'Sin plan',
            'message' => 'No hay licencia asignada'
        ]);
        $stmt->close();
        $conn->close();
        exit;
    }
    
    $licencia = $result->fetch_assoc();
    $stmt->close();
    
    // Calcular si está activa
    $hoy = date('Y-m-d');
    $vencimiento = $licencia['vencimiento'];
    $inicio = $licencia['fecha_inicio'];
    
    $is_active = ($hoy <= $vencimiento && $hoy >= $inicio);
    $dias_restantes = (int)$licencia['dias_restantes'];
    
    http_response_code(200);
    echo json_encode([
        'active' => $is_active,
        'dias_restantes' => $dias_restantes,
        'vigencia' => $vencimiento,
        'inicio' => $inicio,
        'plan_type' => $licencia['plan_type'],
        'estado' => $licencia['estado'],
        'fecha_inicio' => $inicio,
        'message' => $is_active ? 'Licencia activa' : 'Licencia inactiva'
    ]);
    
    $conn->close();
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Excepción: ' . $e->getMessage()]);
}
?>
