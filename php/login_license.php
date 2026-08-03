<?php
/**
 * API de Login y Verificación de Licencia en uno
 * Endpoint: https://api.yhana.cloud/api/win/login_license.php
 * Método: POST
 * 
 * Verifica usuario, contraseña y licencia en una sola llamada
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

// Configuración de BD - Hostinger
$db_host = 'localhost';
$db_user = 'u369606320_visoo';
$db_pass = getenv('VISO_DB_PASSWORD');
$db_name = 'u369606320_visoo';

try {
    $pdo = new PDO(
        "mysql:host=$db_host;dbname=$db_name;charset=utf8mb4",
        $db_user,
        $db_pass,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Error de BD',
        'tiene_licencia' => false
    ]);
    exit;
}

// Obtener parámetros (POST o JSON)
$input = json_decode(file_get_contents('php://input'), true) ?? $_POST;
$username = $input['username'] ?? null;
$password = $input['password'] ?? null;

if (!$username || !$password) {
    http_response_code(400);
    echo json_encode([
        'success' => false,
        'error' => 'Faltan: username, password',
        'tiene_licencia' => false
    ]);
    exit;
}

try {
    // 1. Verificar usuario y contraseña
    $stmt = $pdo->prepare("SELECT id, usuario, password, dni, nombres, apellidos, clave_usada, activo FROM usuarios WHERE usuario = ? LIMIT 1");
    $stmt->execute([$username]);
    $usuario = $stmt->fetch(PDO::FETCH_ASSOC);
    
    if (!$usuario || !password_verify($password, $usuario['password'])) {
        http_response_code(401);
        echo json_encode([
            'success' => false,
            'error' => 'Credenciales inválidas',
            'tiene_licencia' => false
        ]);
        exit;
    }
    
    // Verificar si la cuenta está activa
    if (isset($usuario['activo']) && (int)$usuario['activo'] === 0) {
        http_response_code(403);
        echo json_encode([
            'success' => false,
            'error' => 'Cuenta suspendida o inactiva. Contacte a soporte.',
            'tiene_licencia' => false
        ]);
        exit;
    }
    
    // 2. Verificar licencia
    $tiene_licencia = false;
    $licencia_vigente = false;
    $plan_type = 'Gratis';
    $fecha_vencimiento = null;
    $dias_restantes = 0;
    
    if ($usuario['clave_usada']) {
        $stmt_clave = $pdo->prepare("SELECT clave, usada, tipo, vigencia FROM claves WHERE clave = ? LIMIT 1");
        $stmt_clave->execute([$usuario['clave_usada']]);
        $clave = $stmt_clave->fetch(PDO::FETCH_ASSOC);
        
        if ($clave && $clave['usada']) {
            $tiene_licencia = true;
            $fecha_vencimiento = $clave['vigencia'];
            
            // Mapear tipo
            switch ($clave['tipo']) {
                case 'siempre':
                    $plan_type = 'Permanente';
                    break;
                case '1_mes':
                    $plan_type = 'Mensual';
                    break;
                case '1_semana':
                    $plan_type = 'Semanal';
                    break;
                default:
                    $plan_type = 'Limitado';
            }
            
            // Verificar vigencia
            $hoy = new DateTime('now', new DateTimeZone('America/Lima'));
            $vencimiento = new DateTime($clave['vigencia'], new DateTimeZone('America/Lima'));
            
            if ($hoy <= $vencimiento) {
                $licencia_vigente = true;
                $dias_restantes = $hoy->diff($vencimiento)->days;
            } else {
                $dias_restantes = -$hoy->diff($vencimiento)->days;
            }
        }
    }
    
    // 3. Generar token
    $token = bin2hex(random_bytes(32));
    
    // 4. Retornar respuesta completa
    http_response_code(200);
    echo json_encode([
        'success' => true,
        'mensaje' => 'Login exitoso',
        'id_usuario' => $usuario['usuario'],  // Usar username (consistente con BD)
        'id' => (int)$usuario['id'],
        'token' => $token,
        'username' => $usuario['usuario'],
        'nombres' => $usuario['nombres'],
        'apellidos' => $usuario['apellidos'],
        'tiene_licencia' => $tiene_licencia,
        'licencia_vigente' => $licencia_vigente,
        'plan_type' => $plan_type,
        'fecha_vencimiento' => $fecha_vencimiento,
        'dias_restantes' => (int)$dias_restantes
    ]);
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Error: ' . $e->getMessage(),
        'tiene_licencia' => false
    ]);
}
?>
