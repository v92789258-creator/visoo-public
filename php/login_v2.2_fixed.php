<?php
/**
 * API LOGIN VISO - Versión Corregida para estructura existente
 * URL: https://api.yhana.cloud/api/win/login.php/usuarios/login
 * Autor: Sistema VISO
 * Fecha: 2025-12-02
 */

// Headers
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Preflight OPTIONS
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

// Configuración de BD
$db_host = 'localhost';
$db_user = 'u369606320_visoo';
$db_pass = getenv('VISO_DB_PASSWORD');
$db_name = 'u369606320_visoo';

try {
    // Conectar a BD
    $pdo = new PDO(
        "mysql:host=$db_host;dbname=$db_name;charset=utf8mb4",
        $db_user,
        $db_pass,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
    
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode([
        'error' => 'Error de conexión a BD',
        'details' => $e->getMessage()
    ]);
    exit;
}

// GET: Health check
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    http_response_code(200);
    echo json_encode(['status' => 'OK', 'message' => 'Login API funcionando']);
    exit;
}

// POST: Obtener datos
$input = json_decode(file_get_contents('php://input'), true);
if (!$input) {
    $input = $_POST;
}

// Obtener ruta
$path = $_SERVER['REQUEST_URI'];
$is_login = strpos($path, 'login') !== false;
$is_registrar = strpos($path, 'registrar') !== false;

try {
    
    // ========== REGISTRAR ==========
    if ($is_registrar) {
        $username = $input['username'] ?? '';
        $password = $input['password'] ?? '';
        $email = $input['email'] ?? '';
        $dni = $input['id_usuario'] ?? '';  // id_usuario es el DNI
        $nombres = $input['nombre_optica'] ?? '';
        
        if (!$username || !$password || !$dni) {
            http_response_code(400);
            echo json_encode(['error' => 'Faltan: username, password, id_usuario']);
            exit;
        }
        
        // Validar formato DNI (9 dígitos)
        if (!preg_match('/^\d{8}$/', $dni)) {
            http_response_code(400);
            echo json_encode(['error' => 'DNI debe tener 8 dígitos']);
            exit;
        }
        
        // Verificar que el usuario no exista
        $stmt = $pdo->prepare("SELECT id FROM usuarios WHERE usuario = ? OR dni = ?");
        $stmt->execute([$username, $dni]);
        
        if ($stmt->rowCount() > 0) {
            http_response_code(409);
            echo json_encode(['error' => 'Usuario o DNI ya existe']);
            exit;
        }
        
        // Hash de contraseña
        $hash = password_hash($password, PASSWORD_BCRYPT);
        
        // Insertar usuario
        $stmt = $pdo->prepare(
            "INSERT INTO usuarios (correo, usuario, password, dni, nombres, rol) 
             VALUES (?, ?, ?, ?, ?, 'user')"
        );
        $stmt->execute([$email, $username, $hash, $dni, $nombres]);
        
        http_response_code(201);
        echo json_encode([
            'mensaje' => 'Usuario registrado exitosamente',
            'id_usuario' => $dni,
            'username' => $username
        ]);
        exit;
    }
    
    
    // ========== LOGIN ==========
    if ($is_login) {
        $username = $input['username'] ?? '';
        $password = $input['password'] ?? '';
        
        if (!$username || !$password) {
            http_response_code(400);
            echo json_encode(['error' => 'Faltan: username, password']);
            exit;
        }
        
        // Buscar usuario por campo 'usuario'
        $stmt = $pdo->prepare(
            "SELECT id, usuario, password, dni, nombres, apellidos, activo 
             FROM usuarios 
             WHERE usuario = ? 
             LIMIT 1"
        );
        $stmt->execute([$username]);
        $user = $stmt->fetch(PDO::FETCH_ASSOC);
        
        if (!$user) {
            http_response_code(401);
            echo json_encode(['error' => 'Credenciales inválidas']);
            exit;
        }
        
        // Verificar si la cuenta está activa
        if (isset($user['activo']) && (int)$user['activo'] === 0) {
            http_response_code(403);
            echo json_encode(['error' => 'Cuenta suspendida o inactiva. Contacte a soporte.']);
            exit;
        }
        
        // Verificar contraseña
        if (!password_verify($password, $user['password'])) {
            http_response_code(401);
            echo json_encode(['error' => 'Credenciales inválidas']);
            exit;
        }
        
        // Generar token
        $token = bin2hex(random_bytes(32));
        
        // Respuesta exitosa
        http_response_code(200);
        echo json_encode([
            'mensaje' => 'Login exitoso',
            'id_usuario' => $user['dni'],      // DNI como ID
            'id' => (int)$user['id'],          // ID de BD
            'token' => $token,
            'username' => $user['usuario'],
            'nombres' => $user['nombres'],
            'apellidos' => $user['apellidos']
        ]);
        exit;
    }
    
    
    // Default - GET sin ruta específica
    http_response_code(200);
    echo json_encode(['status' => 'OK', 'message' => 'API Login VISO v2.2']);
    
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode([
        'error' => 'Error en BD: ' . $e->getMessage(),
        'code' => $e->getCode()
    ]);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'error' => 'Error: ' . $e->getMessage(),
        'code' => $e->getCode()
    ]);
}

?>
