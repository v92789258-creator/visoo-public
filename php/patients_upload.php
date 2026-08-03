<?php
/**
 * VISO PATIENTS UPLOAD API
 * Ubicación: /public_html/api/win/patients_upload.php
 * 
 * Sincroniza datos de pacientes desde la app VISO a BD remota
 * Tabla: pacientes
 * Campos: id_usuario, dni, nombre, fecha_nacimiento, genero, edad
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

// Crear tabla de pacientes si no existe
try {
    $pdo->exec("CREATE TABLE IF NOT EXISTS pacientes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        id_usuario VARCHAR(100) NOT NULL,
        uuid VARCHAR(36) NULL DEFAULT NULL,
        dni VARCHAR(20) NOT NULL,
        nombre VARCHAR(150) NOT NULL,
        fecha_nacimiento DATE NULL DEFAULT NULL,
        genero VARCHAR(1) NULL DEFAULT NULL,
        edad INT NULL DEFAULT NULL,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_id_usuario (id_usuario),
        INDEX idx_dni (dni),
        UNIQUE KEY unique_usuario_uuid (id_usuario, uuid)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
    
    // Intentar añadir la columna uuid si no existe (para tablas ya creadas)
    try {
        $pdo->exec("ALTER TABLE pacientes ADD COLUMN uuid VARCHAR(36) NULL DEFAULT NULL AFTER id_usuario");
        $pdo->exec("CREATE UNIQUE INDEX unique_usuario_uuid ON pacientes(id_usuario, uuid)");
        // Opcional: Eliminar el índice antiguo si existe
        try { $pdo->exec("ALTER TABLE pacientes DROP INDEX unique_usuario_dni"); } catch(Exception $e) {}
    } catch (Exception $e) {
        // La columna o el índice probablemente ya existen
    }
    
    error_log("PATIENTS_UPLOAD - Tabla pacientes verificada con soporte UUID");
} catch (Exception $e) {
    error_log("PATIENTS_UPLOAD - Error en estructura de tabla: " . $e->getMessage());
}

// GET: Health check
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    http_response_code(200);
    echo json_encode(['status' => 'OK', 'message' => 'Patients Upload API con soporte UUID funcionando']);
    exit;
}

// POST: Obtener datos
$raw_input = file_get_contents('php://input');
$data = json_decode($raw_input, true);
if (!$data) {
    $data = $_POST;
}

// Log para debugging - ANTES de validar
error_log("PATIENTS_UPLOAD - Raw Input: " . substr($raw_input, 0, 500));

// Validar datos requeridos
if (!isset($data['id_usuario']) || !isset($data['dni']) || !isset($data['nombre'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Faltan campos requeridos: id_usuario, dni, nombre']);
    exit;
}

$id_usuario = trim($data['id_usuario']);
$dni = trim($data['dni']);
$nombre = trim($data['nombre']);
$uuid = isset($data['uuid']) ? trim($data['uuid']) : null;
$fecha_nacimiento = isset($data['fecha_nacimiento']) ? trim($data['fecha_nacimiento']) : null;
$genero = isset($data['genero']) ? trim($data['genero']) : null;
$edad = isset($data['edad']) ? (int)$data['edad'] : null;

// Log para debugging - DESPUÉS de extraer
error_log("PATIENTS_UPLOAD - Procesando: $id_usuario | $dni | UUID: $uuid");

// Validar que id_usuario exista en la tabla usuarios (como username)
try {
    $stmt = $pdo->prepare("SELECT id FROM usuarios WHERE usuario = ?");
    $stmt->execute([$id_usuario]);
    $user = $stmt->fetch();
    
    if (!$user) {
        error_log("PATIENTS_UPLOAD - Usuario no encontrado: $id_usuario");
        http_response_code(404);
        echo json_encode(['error' => "Usuario no encontrado: $id_usuario"]);
        exit;
    }
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => $e->getMessage()]);
    exit;
}

// Buscar si el paciente ya existe (Priorizar búsqueda por UUID si existe, sino por DNI como fallback)
try {
    $exists = null;
    if ($uuid) {
        $stmt = $pdo->prepare("SELECT id FROM pacientes WHERE id_usuario = ? AND uuid = ?");
        $stmt->execute([$id_usuario, $uuid]);
        $exists = $stmt->fetch();
    }
    
    // Fallback: Si no hay UUID o no se encontró por UUID, pero es un DNI REAL (no anónimo), intentar por DNI
    if (!$exists && $uuid === null && $dni !== '00000000') {
        $stmt = $pdo->prepare("SELECT id FROM pacientes WHERE id_usuario = ? AND dni = ?");
        $stmt->execute([$id_usuario, $dni]);
        $exists = $stmt->fetch();
    }
    
    if ($exists) {
        // Actualizar paciente existente
        $stmt = $pdo->prepare("
            UPDATE pacientes 
            SET nombre = ?, 
                dni = ?,
                uuid = ?,
                fecha_nacimiento = ?, 
                genero = ?, 
                edad = ?, 
                fecha_actualizacion = NOW()
            WHERE id = ?
        ");
        $stmt->execute([$nombre, $dni, $uuid, $fecha_nacimiento, $genero, $edad, $exists['id']]);
        
        http_response_code(200);
        echo json_encode([
            'mensaje' => 'Paciente actualizado',
            'id_usuario' => $id_usuario,
            'dni' => $dni,
            'uuid' => $uuid,
            'operacion' => 'update'
        ]);
    } else {
        // Insertar nuevo paciente
        $stmt = $pdo->prepare("
            INSERT INTO pacientes (id_usuario, uuid, dni, nombre, fecha_nacimiento, genero, edad)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ");
        $stmt->execute([$id_usuario, $uuid, $dni, $nombre, $fecha_nacimiento, $genero, $edad]);
        
        http_response_code(201);
        echo json_encode([
            'mensaje' => 'Paciente guardado como persona nueva',
            'id_usuario' => $id_usuario,
            'dni' => $dni,
            'uuid' => $uuid,
            'operacion' => 'insert'
        ]);
    }
} catch (PDOException $e) {
    error_log("PATIENTS_UPLOAD - Error SQL: " . $e->getMessage());
    http_response_code(500);
    echo json_encode(['error' => $e->getMessage()]);
    exit;
}
?>