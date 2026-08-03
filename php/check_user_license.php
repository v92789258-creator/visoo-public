<?php
// Solo JSON, sin debug
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

$db_host = 'localhost';
$db_user = 'u369606320_visoo';
$db_pass = getenv('VISO_DB_PASSWORD');
$db_name = 'u369606320_visoo';

try {
    $pdo = new PDO("mysql:host=$db_host;dbname=$db_name;charset=utf8mb4", $db_user, $db_pass, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
} catch (PDOException $e) {
    http_response_code(500);
    die(json_encode(['error' => 'BD', 'tiene_licencia' => false]));
}

$input = json_decode(file_get_contents('php://input'), true) ?? $_POST ?? $_GET;
$username = $input['username'] ?? null;
$dni = $input['dni'] ?? null;

if (!$username && !$dni) {
    http_response_code(400);
    die(json_encode(['error' => 'username o dni requerido', 'tiene_licencia' => false]));
}

try {
    $stmt = $pdo->prepare("SELECT id, usuario, dni, nombres, apellidos, clave_usada FROM usuarios WHERE usuario = ? OR dni = ? LIMIT 1");
    $stmt->execute([$username ?? '', $dni ?? '']);
    $usuario = $stmt->fetch(PDO::FETCH_ASSOC);
    
    if (!$usuario) {
        http_response_code(404);
        die(json_encode(['error' => 'Usuario no encontrado', 'tiene_licencia' => false]));
    }
    
    $respuesta = [
        'usuario' => $usuario['usuario'],
        'dni' => $usuario['dni'],
        'nombres' => $usuario['nombres'],
        'tiene_licencia' => false,
        'licencia_vigente' => false,
        'plan_type' => 'Gratis',
        'fecha_vencimiento' => null,
        'dias_restantes' => 0
    ];
    
    if (!$usuario['clave_usada']) {
        http_response_code(200);
        die(json_encode($respuesta));
    }
    
    $stmt_clave = $pdo->prepare("SELECT clave, usada, tipo, vigencia FROM claves WHERE clave = ? LIMIT 1");
    $stmt_clave->execute([$usuario['clave_usada']]);
    $clave = $stmt_clave->fetch(PDO::FETCH_ASSOC);
    
    if (!$clave || !$clave['usada']) {
        http_response_code(200);
        die(json_encode($respuesta));
    }
    
    $hoy = new DateTime('now', new DateTimeZone('America/Lima'));
    $vigencia = new DateTime($clave['vigencia'], new DateTimeZone('America/Lima'));
    
    $licencia_vigente = ($hoy <= $vigencia);
    $dias_restantes = (int)$hoy->diff($vigencia)->days;
    if ($hoy > $vigencia) {
        $dias_restantes = -$dias_restantes;
    }
    
    $plan_type = 'Limitado';
    if ($clave['tipo'] === 'siempre') $plan_type = 'Permanente';
    elseif ($clave['tipo'] === '1_mes') $plan_type = 'Mensual';
    elseif ($clave['tipo'] === '1_semana') $plan_type = 'Semanal';
    
    $respuesta = [
        'usuario' => $usuario['usuario'],
        'dni' => $usuario['dni'],
        'nombres' => $usuario['nombres'],
        'tiene_licencia' => true,
        'licencia_vigente' => $licencia_vigente,
        'plan_type' => $plan_type,
        'fecha_vencimiento' => $clave['vigencia'],
        'dias_restantes' => $dias_restantes
    ];
    
    http_response_code(200);
    die(json_encode($respuesta));
    
} catch (Exception $e) {
    http_response_code(500);
    die(json_encode(['error' => 'Error', 'tiene_licencia' => false]));
}
?>

try {
    // 1. Obtener usuario
    $stmt = $pdo->prepare("SELECT id, usuario, dni, nombres, apellidos, clave_usada FROM usuarios WHERE usuario = ? OR dni = ? LIMIT 1");
    $stmt->execute([$username ?? '', $dni ?? '']);
    $usuario = $stmt->fetch(PDO::FETCH_ASSOC);
    
    if (!$usuario) {
        http_response_code(404);
        echo json_encode([
            'error' => 'Usuario no encontrado',
            'tiene_licencia' => false
        ]);
        exit;
    }
    
    // 2. Inicializar respuesta
    $respuesta = [
        'usuario' => $usuario['usuario'],
        'dni' => $usuario['dni'],
        'nombres' => $usuario['nombres'],
        'tiene_licencia' => false,
        'licencia_vigente' => false,
        'plan_type' => 'Gratis',
        'fecha_vencimiento' => null,
        'dias_restantes' => 0
    ];
    
    // 3. Verificar si tiene clave_usada
    if (!$usuario['clave_usada']) {
        http_response_code(200);
        echo json_encode($respuesta);
        exit;
    }
    
    // 4. Buscar la clave en tabla claves
    $stmt_clave = $pdo->prepare(
        "SELECT clave, usada, tipo, vigencia, multiplataforma 
         FROM claves 
         WHERE clave = ?
         LIMIT 1"
    );
    $stmt_clave->execute([$usuario['clave_usada']]);
    $clave = $stmt_clave->fetch(PDO::FETCH_ASSOC);
    
    if (!$clave || !$clave['usada']) {
        http_response_code(200);
        echo json_encode($respuesta);
        exit;
    }
    
    // 5. Verificar vigencia
    $hoy = new DateTime('now', new DateTimeZone('America/Lima'));
    $vigencia = new DateTime($clave['vigencia'], new DateTimeZone('America/Lima'));
    
    $licencia_vigente = ($hoy <= $vigencia);
    $dias_restantes = $hoy->diff($vigencia)->days;
    if ($hoy > $vigencia) {
        $dias_restantes = -$dias_restantes; // Negativo si expiró
    }
    
    // 6. Mapear tipo de clave a plan
    $plan_type = 'Limitado';
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
    }
    
    // 7. Armar respuesta final
    $respuesta = [
        'usuario' => $usuario['usuario'],
        'dni' => $usuario['dni'],
        'nombres' => $usuario['nombres'],
        'tiene_licencia' => true,
        'licencia_vigente' => $licencia_vigente,
        'plan_type' => $plan_type,
        'fecha_vencimiento' => $clave['vigencia'],
        'dias_restantes' => (int)$dias_restantes
    ];
    
    http_response_code(200);
    echo json_encode($respuesta);
    
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode([
        'error' => 'Error en BD',
        'tiene_licencia' => false
    ]);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'error' => 'Error: ' . $e->getMessage(),
        'tiene_licencia' => false
    ]);
}


$stmt->execute([$username, $dni]);
$usuario = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$usuario) {
    http_response_code(404);
    echo json_encode([
        'error' => 'Usuario no encontrado',
        'parametros_enviados' => [
            'username' => $username,
            'dni' => $dni
        ]
    ]);
    exit;
}

// 2. Mostrar datos del usuario
$resultado = [
    'usuario' => [
        'id' => $usuario['id'],
        'usuario' => $usuario['usuario'],
        'dni' => $usuario['dni'],
        'nombres' => $usuario['nombres'],
        'apellidos' => $usuario['apellidos'],
        'clave_usada' => $usuario['clave_usada'] ?? 'NULL'
    ]
];

// 3. Verificar si tiene clave_usada
if (!$usuario['clave_usada']) {
    $resultado['licencia'] = [
        'tiene_licencia' => false,
        'razon' => 'clave_usada es NULL',
        'mensaje' => 'El usuario no tiene ninguna clave asignada'
    ];
    echo json_encode($resultado, JSON_PRETTY_PRINT);
    exit;
}

// 4. Buscar la clave en tabla claves
$stmt_clave = $pdo->prepare(
    "SELECT id, clave, usada, tipo, vigencia, multiplataforma 
     FROM claves 
     WHERE clave = ? 
     LIMIT 1"
);
$stmt_clave->execute([$usuario['clave_usada']]);
$clave = $stmt_clave->fetch(PDO::FETCH_ASSOC);

if (!$clave) {
    $resultado['licencia'] = [
        'tiene_licencia' => false,
        'razon' => 'clave_no_existe',
        'clave_buscada' => $usuario['clave_usada'],
        'mensaje' => 'La clave usada no existe en tabla claves'
    ];
    echo json_encode($resultado, JSON_PRETTY_PRINT);
    exit;
}

// 5. Verificar si la clave está usada
if (!$clave['usada']) {
    $resultado['licencia'] = [
        'tiene_licencia' => false,
        'razon' => 'clave_no_usada',
        'clave_info' => $clave,
        'mensaje' => 'La clave existe pero no está marcada como usada'
    ];
    echo json_encode($resultado, JSON_PRETTY_PRINT);
    exit;
}

// 6. Verificar vigencia
$hoy = new DateTime('now', new DateTimeZone('America/Lima'));
$vigencia = new DateTime($clave['vigencia'], new DateTimeZone('America/Lima'));

$licencia_vigente = ($hoy <= $vigencia);
$dias_restantes = $hoy->diff($vigencia)->days;
if ($hoy > $vigencia) {
    $dias_restantes = -$dias_restantes; // Negativo si expiró
}

$resultado['licencia'] = [
    'tiene_licencia' => true,
    'licencia_vigente' => $licencia_vigente,
    'clave_info' => [
        'clave' => $clave['clave'],
        'tipo' => $clave['tipo'],
        'usada' => (bool)$clave['usada'],
        'vigencia' => $clave['vigencia'],
        'multiplataforma' => (bool)$clave['multiplataforma']
    ],
    'estado_licencia' => [
        'hoy' => $hoy->format('Y-m-d H:i:s'),
        'vigencia' => $vigencia->format('Y-m-d H:i:s'),
        'vigente' => $licencia_vigente ? 'SÍ' : 'NO',
        'dias_restantes' => $dias_restantes,
        'mensaje' => $licencia_vigente 
            ? "Licencia activa - {$dias_restantes} días restantes"
            : "Licencia EXPIRADA - hace {$dias_restantes} días"
    ]
];

// 7. Retornar resultado
http_response_code(200);
echo json_encode($resultado, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
?>
