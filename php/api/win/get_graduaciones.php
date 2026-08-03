<?php
/**
 * GET_GRADUACIONES.PHP
 * 
 * Obtiene el HISTORIAL DE GRADUACIONES de un paciente específico.
 * 
 * Parámetros:
 * - id_paciente: ID del paciente
 * - usuario_id: ID del usuario (para validación)
 */

error_reporting(E_ALL);
ini_set('display_errors', '0');
ini_set('log_errors', '1');

header('Content-Type: application/json; charset=utf-8');

try {
    $id_paciente = isset($_GET['id_paciente']) ? intval($_GET['id_paciente']) : 0;
    $usuario_id = isset($_GET['usuario_id']) ? $_GET['usuario_id'] : null;
    
    if (!$id_paciente || !$usuario_id) {
        echo json_encode(['success' => false, 'error' => 'Faltan parámetros (id_paciente, usuario_id)']);
        exit;
    }
    
    $conn = mysqli_connect('localhost', 'u369606320_visoo', getenv('VISO_DB_PASSWORD'), 'u369606320_visoo');
    
    if (!$conn) {
        echo json_encode(['success' => false, 'error' => 'Conexión BD: ' . mysqli_connect_error()]);
        exit;
    }
    
    mysqli_set_charset($conn, 'utf8mb4');
    
    // ============================================================================
    // CREAR TABLA DE GRADUACIONES SI NO EXISTE (CON COLUMNAS INDIVIDUALES)
    // ============================================================================
    // Primero dropear la tabla antigua si existe (para migrar desde JSON)
    $drop_table_query = "DROP TABLE IF EXISTS `graduaciones`";
    mysqli_query($conn, $drop_table_query);  // Ignorar error si no existe
    
    $create_table_query = "CREATE TABLE IF NOT EXISTS `graduaciones` (
        `id` INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
        `id_paciente` INT(11) NOT NULL,
        `fecha` DATE NOT NULL,
        `optometra` VARCHAR(255),
        
        -- Visión de Lejos - OD (Ojo Derecho)
        `lejos_od_esferico` VARCHAR(10),
        `lejos_od_cilindro` VARCHAR(10),
        `lejos_od_eje` VARCHAR(10),
        `lejos_od_av` VARCHAR(10),
        `lejos_od_distp` VARCHAR(10),
        `lejos_od_prisma` VARCHAR(10),
        `lejos_od_adicmedia` VARCHAR(10),
        
        -- Visión de Lejos - OI (Ojo Izquierdo)
        `lejos_oi_esferico` VARCHAR(10),
        `lejos_oi_cilindro` VARCHAR(10),
        `lejos_oi_eje` VARCHAR(10),
        `lejos_oi_av` VARCHAR(10),
        `lejos_oi_distp` VARCHAR(10),
        `lejos_oi_prisma` VARCHAR(10),
        `lejos_oi_adicmedia` VARCHAR(10),
        
        -- Visión de Cerca - OD (Ojo Derecho)
        `cerca_od_esferico` VARCHAR(10),
        `cerca_od_cilindro` VARCHAR(10),
        `cerca_od_eje` VARCHAR(10),
        `cerca_od_av` VARCHAR(10),
        `cerca_od_prisma` VARCHAR(10),
        `cerca_od_adicmedia` VARCHAR(10),
        
        -- Visión de Cerca - OI (Ojo Izquierdo)
        `cerca_oi_esferico` VARCHAR(10),
        `cerca_oi_cilindro` VARCHAR(10),
        `cerca_oi_eje` VARCHAR(10),
        `cerca_oi_av` VARCHAR(10),
        `cerca_oi_prisma` VARCHAR(10),
        `cerca_oi_adicmedia` VARCHAR(10),
        
        `fecha_registro` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        `fecha_actualizacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        
        UNIQUE KEY `unique_paciente_fecha` (`id_paciente`, `fecha`),
        KEY `idx_paciente` (`id_paciente`),
        KEY `idx_fecha` (`fecha`),
        CONSTRAINT `fk_paciente` FOREIGN KEY (`id_paciente`) 
            REFERENCES `pacientes` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";
    
    if (!mysqli_query($conn, $create_table_query)) {
        if (strpos(mysqli_error($conn), 'already exists') === false) {
            error_log("Warning: Could not create graduaciones table: " . mysqli_error($conn));
        }
    }
    
    // Escapar usuario_id después de conectar
    if (is_numeric($usuario_id)) {
        $usuario_id_escaped = intval($usuario_id);
        $usuario_id_sql = $usuario_id_escaped;
    } else {
        $usuario_id_escaped = mysqli_real_escape_string($conn, $usuario_id);
        $usuario_id_sql = "'$usuario_id_escaped'";
    }
    
    // ============================================================================
    // VALIDAR QUE EL PACIENTE PERTENECE AL USUARIO
    // ============================================================================
    $query_check = "SELECT id FROM pacientes WHERE id=$id_paciente AND id_usuario=$usuario_id_sql LIMIT 1";
    $result_check = mysqli_query($conn, $query_check);
    
    if (!$result_check || mysqli_num_rows($result_check) === 0) {
        echo json_encode(['success' => false, 'error' => 'Paciente no encontrado o acceso denegado']);
        mysqli_close($conn);
        exit;
    }
    
    // ============================================================================
    // OBTENER GRADUACIONES DEL PACIENTE
    // ============================================================================
    $query = "SELECT id, id_paciente, fecha, optometra, 
                     lejos_od_esferico, lejos_od_cilindro, lejos_od_eje, lejos_od_av, lejos_od_distp, lejos_od_prisma, lejos_od_adicmedia,
                     lejos_oi_esferico, lejos_oi_cilindro, lejos_oi_eje, lejos_oi_av, lejos_oi_distp, lejos_oi_prisma, lejos_oi_adicmedia,
                     cerca_od_esferico, cerca_od_cilindro, cerca_od_eje, cerca_od_av, cerca_od_prisma, cerca_od_adicmedia,
                     cerca_oi_esferico, cerca_oi_cilindro, cerca_oi_eje, cerca_oi_av, cerca_oi_prisma, cerca_oi_adicmedia,
                     fecha_registro, fecha_actualizacion 
              FROM graduaciones 
              WHERE id_paciente=$id_paciente
              ORDER BY fecha DESC";
    
    $result = mysqli_query($conn, $query);
    
    if (!$result) {
        echo json_encode(['success' => false, 'error' => 'Query error: ' . mysqli_error($conn)]);
        mysqli_close($conn);
        exit;
    }
    
    $graduaciones = [];
    
    while ($row = mysqli_fetch_assoc($result)) {
        $graduaciones[] = [
            'id' => intval($row['id']),
            'id_paciente' => intval($row['id_paciente']),
            'fecha' => $row['fecha'],
            'optometra' => $row['optometra'],
            'lejos_od' => [
                'esferico' => $row['lejos_od_esferico'],
                'cilindro' => $row['lejos_od_cilindro'],
                'eje' => $row['lejos_od_eje'],
                'av' => $row['lejos_od_av'],
                'distp' => $row['lejos_od_distp'],
                'prisma' => $row['lejos_od_prisma'],
                'adicmedia' => $row['lejos_od_adicmedia']
            ],
            'lejos_oi' => [
                'esferico' => $row['lejos_oi_esferico'],
                'cilindro' => $row['lejos_oi_cilindro'],
                'eje' => $row['lejos_oi_eje'],
                'av' => $row['lejos_oi_av'],
                'distp' => $row['lejos_oi_distp'],
                'prisma' => $row['lejos_oi_prisma'],
                'adicmedia' => $row['lejos_oi_adicmedia']
            ],
            'cerca_od' => [
                'esferico' => $row['cerca_od_esferico'],
                'cilindro' => $row['cerca_od_cilindro'],
                'eje' => $row['cerca_od_eje'],
                'av' => $row['cerca_od_av'],
                'prisma' => $row['cerca_od_prisma'],
                'adicmedia' => $row['cerca_od_adicmedia']
            ],
            'cerca_oi' => [
                'esferico' => $row['cerca_oi_esferico'],
                'cilindro' => $row['cerca_oi_cilindro'],
                'eje' => $row['cerca_oi_eje'],
                'av' => $row['cerca_oi_av'],
                'prisma' => $row['cerca_oi_prisma'],
                'adicmedia' => $row['cerca_oi_adicmedia']
            ],
            'fecha_registro' => $row['fecha_registro'],
            'fecha_actualizacion' => $row['fecha_actualizacion']
        ];
    }
    
    mysqli_close($conn);
    
    // ============================================================================
    // RETORNAR RESPUESTA
    // ============================================================================
    echo json_encode([
        'success' => true,
        'id_paciente' => $id_paciente,
        'graduaciones' => $graduaciones,
        'total' => count($graduaciones)
    ]);
    
} catch (Exception $e) {
    echo json_encode(['success' => false, 'error' => 'Exception: ' . $e->getMessage()]);
}

exit;
?>
