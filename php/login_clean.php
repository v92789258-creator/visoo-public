<?php
/**
 * VISO LOGIN API - Compatible con estructura existente
 * Ubicación: /public_html/api/win/login.php
 * 
 * Usa la tabla usuarios existente con campos:
 * id, correo, usuario, password, dni, nombres, apellidos, etc.
 */

// Headers
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Preflight
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

// Configuración
$db_host = 'localhost';
$db_user = 'u369606320_visoo';
$db_pass = getenv('VISO_DB_PASSWORD');
$db_name = 'u369606320_visoo';

// Conectar
try {
    $pdo = new PDO(
        "mysql:host=$db_host;dbname=$db_name;charset=utf8mb4",
        $db_user,
        $db_pass
    );
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['error' => 'BD Error: ' . $e->getMessage()]);
    exit;
}

// Crear tabla de pacientes
try {
    $pdo->exec("CREATE TABLE IF NOT EXISTS pacientes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        id_usuario VARCHAR(9) NOT NULL,
        dni VARCHAR(8) NOT NULL,
        nombre VARCHAR(150) NOT NULL,
        fecha_nacimiento DATE,
        genero VARCHAR(20),
        edad INT,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_id_usuario (id_usuario),
        INDEX idx_dni (dni),
        UNIQUE KEY unique_usuario_dni (id_usuario, dni),
        FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
} catch (Exception $e) {
    // Tabla ya existe
}

// GET: Health check
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    http_response_code(200);
    echo json_encode(['status' => 'OK', 'message' => 'API VISO funcionando']);
    exit;
}

// POST: Obtener datos
$data = json_decode(file_get_contents('php://input'), true);
if (!$data) {
    $data = $_POST;
}

// Obtener ruta
$path = $_SERVER['REQUEST_URI'];
$is_login = strpos($path, 'login') !== false;
$is_registrar = strpos($path, 'registrar') !== false;
$is_guardar_paciente = false; // Deshabilitado - usar endpoint separado

// REGISTRAR
if ($is_registrar) {
    $id_usuario = $data['id_usuario'] ?? '';
    $username = $data['username'] ?? '';
    $password = $data['password'] ?? '';
    $email = $data['email'] ?? '';
    $optica = $data['nombre_optica'] ?? '';
    
    if (!$id_usuario || !$username || !$password) {
        http_response_code(400);
        echo json_encode(['error' => 'Faltan campos: id_usuario, username, password']);
        exit;
    }
    
    // Usar los datos como vienen (id_usuario puede ser el DNI o ID)
    try {
        $hash = password_hash($password, PASSWORD_BCRYPT);
        
        // Insertar usando la estructura existente
        // Mapear: id_usuario→DNI, username→usuario, email→correo, optica→nombres
        $stmt = $pdo->prepare(
            "INSERT INTO usuarios (correo, usuario, password, dni, nombres, apellidos) 
             VALUES (?, ?, ?, ?, ?, ?)"
        );
        $stmt->execute([
            $email,           // correo
            $username,        // usuario
            $hash,            // password
            $id_usuario,      // dni
            $optica,          // nombres
            ''                // apellidos
        ]);
        
        http_response_code(201);
        echo json_encode([
            'mensaje' => 'Usuario registrado',
            'id_usuario' => $id_usuario,
            'username' => $username
        ]);
    } catch (PDOException $e) {
        if (strpos($e->getMessage(), 'Duplicate') !== false) {
            http_response_code(409);
            echo json_encode(['error' => 'Usuario ya existe']);
        } else {
            http_response_code(500);
            echo json_encode(['error' => $e->getMessage()]);
        }
    }
    exit;
}

// LOGIN
if ($is_login) {
    $username = $data['username'] ?? '';
    $password = $data['password'] ?? '';
    
    if (!$username || !$password) {
        http_response_code(400);
        echo json_encode(['error' => 'Faltan username o password']);
        exit;
    }
    
    try {
        // Buscar por campo 'usuario' (no 'username')
        $stmt = $pdo->prepare("SELECT id, usuario, password, dni, activo FROM usuarios WHERE usuario = ?");
        $stmt->execute([$username]);
        $row = $stmt->fetch(PDO::FETCH_ASSOC);
        
        if (!$row) {
            http_response_code(401);
            echo json_encode(['error' => 'Credenciales inválidas']);
            exit;
        }
        
        // Verificar si la cuenta está activa
        if (isset($row['activo']) && (int)$row['activo'] === 0) {
            http_response_code(403);
            echo json_encode(['error' => 'Cuenta suspendida o inactiva. Contacte a soporte.']);
            exit;
        }
        
        // Verificar contraseña
        if (!password_verify($password, $row['password'])) {
            http_response_code(401);
            echo json_encode(['error' => 'Credenciales inválidas']);
            exit;
        }
        
        // Generar token
        $token = bin2hex(random_bytes(32));
        
        // Retornar ID de usuario (usar 'id' o 'dni')
        http_response_code(200);
        echo json_encode([
            'mensaje' => 'Login exitoso',
            'id_usuario' => (string)$row['dni'],  // Usar DNI como ID
            'id' => (int)$row['id'],              // ID de BD también
            'token' => $token,
            'username' => $row['usuario']
        ]);
    } catch (Exception $e) {
        http_response_code(500);
        echo json_encode(['error' => $e->getMessage()]);
    }
    exit;
}

// GUARDAR PACIENTE
if ($is_guardar_paciente) {
    // Deshabilitado - usar endpoint separado (patients_upload.php)
    http_response_code(405);
    echo json_encode(['error' => 'Usar endpoint separado: /api/win/patients_upload.php']);
    exit;
}

// Default
http_response_code(200);
echo json_encode(['status' => 'OK']);
?>

