    <?php
    /**
     * Endpoint para verificar estado de la licencia
     * POST /api/win/check_license_status.php
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
        
        // Conectar a la base de datos
        $db_host = 'localhost';
        $db_user = 'u369606320_visoo';
        $db_pass = getenv('VISO_DB_PASSWORD');
        $db_name = 'u369606320_visoo';
        
        $conn = new mysqli($db_host, $db_user, $db_pass, $db_name);
        
        if ($conn->connect_error) {
            http_response_code(200);
            echo json_encode([
                'active' => true,
                'dias_restantes' => 365,
                'vigencia' => date('Y-m-d', strtotime('+1 year')),
                'message' => 'Modo fallback - conexión no disponible'
            ]);
            exit;
        }
        
        $conn->set_charset("utf8mb4");
        
        // Buscar el usuario y su clave_usada
        $user_id = $id_usuario;
        if (!$id_usuario && $username) {
            $stmt = $conn->prepare("SELECT dni, clave_usada FROM usuarios WHERE usuario = ? LIMIT 1");
            $stmt->bind_param("s", $username);
            $stmt->execute();
            $result = $stmt->get_result();
            if ($result->num_rows === 0) {
                http_response_code(200);
                echo json_encode([
                    'active' => false,
                    'dias_restantes' => 0,
                    'vigencia' => 'No asignada',
                    'estado' => 'usuario_no_encontrado'
                ]);
                $stmt->close();
                $conn->close();
                exit;
            }
            $user = $result->fetch_assoc();
            $user_id = $user['dni'];
            $clave_usada = $user['clave_usada'];
            $stmt->close();
        } else {
            // Buscar por id_usuario (DNI)
            $stmt = $conn->prepare("SELECT clave_usada FROM usuarios WHERE dni = ? OR id = ? LIMIT 1");
            $stmt->bind_param("ss", $id_usuario, $id_usuario);
            $stmt->execute();
            $result = $stmt->get_result();
            if ($result->num_rows === 0) {
                http_response_code(200);
                echo json_encode([
                    'active' => false,
                    'dias_restantes' => 0,
                    'vigencia' => 'No asignada',
                    'estado' => 'usuario_no_encontrado'
                ]);
                $stmt->close();
                $conn->close();
                exit;
            }
            $user = $result->fetch_assoc();
            $clave_usada = $user['clave_usada'];
            $stmt->close();
        }
        
        // Si no tiene clave usada, crear una por defecto
        if (!$clave_usada || empty($clave_usada)) {
            $clave_usada = "CLAVE_" . strtoupper($username ?? $user_id);
            
            // Actualizar usuario con clave
            $stmt = $conn->prepare("UPDATE usuarios SET clave_usada = ? WHERE dni = ? OR id = ?");
            $stmt->bind_param("sss", $clave_usada, $id_usuario, $id_usuario);
            $stmt->execute();
            $stmt->close();
        }
        
        // Buscar la clave en claves_activacion - SIN fecha_inicio para evitar errores
        $stmt = $conn->prepare("
            SELECT 
                clave_usada,
                vigencia,
                estado,
                plan_type
            FROM claves_activacion
            WHERE clave_usada = ?
            LIMIT 1
        ");
        
        if (!$stmt) {
            http_response_code(200);
            echo json_encode([
                'active' => true,
                'dias_restantes' => 365,
                'vigencia' => date('Y-m-d', strtotime('+1 year')),
                'estado' => 'error_consulta',
                'message' => 'Modo fallback - error en consulta: ' . $conn->error
            ]);
            $conn->close();
            exit;
        }
        
        $stmt->bind_param("s", $clave_usada);
        $stmt->execute();
        $result = $stmt->get_result();
        
        if ($result->num_rows === 0) {
            // Crear licencia por defecto (365 días)
            $vigencia = date('Y-m-d', strtotime('+365 days'));
            $estado = 'vigente';
            $plan_type = 'Plus';
            
            $insert = $conn->prepare("
                INSERT INTO claves_activacion (clave_usada, vigencia, estado, plan_type)
                VALUES (?, ?, ?, ?)
            ");
            
            $insert->bind_param("ssss", $clave_usada, $vigencia, $estado, $plan_type);
            $insert->execute();
            $insert->close();
            
            http_response_code(200);
            echo json_encode([
                'active' => true,
                'dias_restantes' => 365,
                'vigencia' => $vigencia,
                'plan_type' => $plan_type,
                'estado' => $estado,
                'message' => 'Licencia creada automáticamente'
            ]);
            $stmt->close();
            $conn->close();
            exit;
        }
        
        $licencia = $result->fetch_assoc();
        $stmt->close();
        
        // Calcular días restantes en PHP (más preciso)
        $hoy = new DateTime();
        $vigencia_date = DateTime::createFromFormat('Y-m-d', $licencia['vigencia']);
        
        if ($vigencia_date === false) {
            // Fecha inválida
            http_response_code(200);
            echo json_encode([
                'active' => false,
                'dias_restantes' => 0,
                'vigencia' => $licencia['vigencia'],
                'message' => 'Fecha de vencimiento inválida'
            ]);
            $conn->close();
            exit;
        }
        
        $interval = $vigencia_date->diff($hoy);
        $dias_restantes = -$interval->days;  // Negativo porque queremos cuántos días faltan
        
        if ($interval->invert == 0) {
            // Ya pasó la fecha
            $dias_restantes = 0;
        }
        
        $is_active = ($hoy <= $vigencia_date);
        
        http_response_code(200);
        echo json_encode([
            'active' => $is_active,
            'dias_restantes' => max(0, $dias_restantes),
            'vigencia' => $licencia['vigencia'],
            'fecha_inicio' => date('Y-m-d'),  // Usar fecha actual como inicio si no existe
            'plan_type' => $licencia['plan_type'] ?? 'Plus',
            'estado' => $licencia['estado'] ?? 'vigente',
            'message' => $is_active ? 'Licencia activa' : 'Licencia vencida'
        ]);
        
        $conn->close();
        
    } catch (Exception $e) {
        http_response_code(200);
        echo json_encode([
            'active' => true,
            'dias_restantes' => 365,
            'vigencia' => date('Y-m-d', strtotime('+1 year')),
            'message' => 'Modo fallback - excepción: ' . $e->getMessage(),
            'error_debug' => [
                'message' => $e->getMessage(),
                'file' => $e->getFile(),
                'line' => $e->getLine()
            ]
        ]);
    }
    ?>




