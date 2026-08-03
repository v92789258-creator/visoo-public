<?php
/**
 * GET_PACIENTES.PHP
 * 
 * Obtiene lista de PACIENTES con sus GRADUACIONES para sincronización.
 * 
 * Implementa:
 * - Retorna pacientes con estructura completa
 * - Incluye historial_graduaciones para cada paciente
 * - Incluye fecha_registro para filtrado
 * - Optimizado para serialización JSON
 */

error_reporting(E_ALL);
ini_set('display_errors', '0');
ini_set('log_errors', '1');

header('Content-Type: application/json; charset=utf-8');

function has_column($conn, $table, $column) {
    $table_safe = mysqli_real_escape_string($conn, $table);
    $column_safe = mysqli_real_escape_string($conn, $column);
    $sql = "SHOW COLUMNS FROM `$table_safe` LIKE '$column_safe'";
    $res = @mysqli_query($conn, $sql);
    return ($res && mysqli_num_rows($res) > 0);
}

try {
    $usuario_id = isset($_GET['usuario_id']) ? $_GET['usuario_id'] : null;
    $codigo_dispositivo = strtoupper(trim((string)($_GET['codigo_dispositivo'] ?? '')));
    
    if (!$usuario_id) {
        echo json_encode(['success' => false, 'error' => 'Falta parámetro usuario_id']);
        exit;
    }
    
    $conn = mysqli_connect('localhost', 'u369606320_visoo', getenv('VISO_DB_PASSWORD'), 'u369606320_visoo');
    
    if (!$conn) {
        echo json_encode(['success' => false, 'error' => 'Conexión BD: ' . mysqli_connect_error()]);
        exit;
    }
    
    mysqli_set_charset($conn, 'utf8mb4');
    $has_codigo = has_column($conn, 'pacientes', 'codigo_dispositivo');
    $has_nombre = has_column($conn, 'pacientes', 'dispositivo_nombre');
    $has_tipo = has_column($conn, 'pacientes', 'tipo_dispositivo');
    
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
    // Recalcular columnas por si la estructura cambió durante esta solicitud.
    $has_codigo = has_column($conn, 'pacientes', 'codigo_dispositivo');
    $has_nombre = has_column($conn, 'pacientes', 'dispositivo_nombre');
    $has_tipo = has_column($conn, 'pacientes', 'tipo_dispositivo');
    
    // Escapar usuario_id después de conectar
    if (is_numeric($usuario_id)) {
        $usuario_id_escaped = intval($usuario_id);
        $usuario_id_sql = $usuario_id_escaped;
    } else {
        $usuario_id_escaped = mysqli_real_escape_string($conn, $usuario_id);
        $usuario_id_sql = "'$usuario_id_escaped'";
    }
    
    // ============================================================================
    // OBTENER PACIENTES
    // ============================================================================
    $select_fields = "id, id_usuario, nombre, dni, edad, genero, fecha_nacimiento, fecha_registro, fecha_actualizacion";
    if ($has_codigo) {
        $select_fields .= ", codigo_dispositivo";
    }
    if ($has_nombre) {
        $select_fields .= ", dispositivo_nombre";
    }
    if ($has_tipo) {
        $select_fields .= ", tipo_dispositivo";
    }

    $query = "SELECT $select_fields FROM pacientes WHERE id_usuario=$usuario_id_sql";
    if ($codigo_dispositivo !== '' && $has_codigo) {
        $codigo_esc = mysqli_real_escape_string($conn, $codigo_dispositivo);
        $query .= " AND codigo_dispositivo='$codigo_esc'";
    }
    $query .= " ORDER BY fecha_registro DESC, nombre ASC";
    
    $result = mysqli_query($conn, $query);
    
    if (!$result) {
        echo json_encode(['success' => false, 'error' => 'Query error: ' . mysqli_error($conn)]);
        mysqli_close($conn);
        exit;
    }
    
    $pacientes = [];
    
    while ($row = mysqli_fetch_assoc($result)) {
        $id_paciente = intval($row['id']);
        
        // ============================================================================
        // OBTENER GRADUACIONES DEL PACIENTE
        // ============================================================================
        $query_grad = "SELECT id, id_paciente, fecha, optometra, 
                              lejos_od_esferico, lejos_od_cilindro, lejos_od_eje, lejos_od_av, lejos_od_distp, lejos_od_prisma, lejos_od_adicmedia,
                              lejos_oi_esferico, lejos_oi_cilindro, lejos_oi_eje, lejos_oi_av, lejos_oi_distp, lejos_oi_prisma, lejos_oi_adicmedia,
                              cerca_od_esferico, cerca_od_cilindro, cerca_od_eje, cerca_od_av, cerca_od_prisma, cerca_od_adicmedia,
                              cerca_oi_esferico, cerca_oi_cilindro, cerca_oi_eje, cerca_oi_av, cerca_oi_prisma, cerca_oi_adicmedia,
                              fecha_registro, fecha_actualizacion 
                       FROM graduaciones 
                       WHERE id_paciente=$id_paciente
                       ORDER BY fecha DESC";
        
        $result_grad = mysqli_query($conn, $query_grad);
        $historial_graduaciones = [];
        
        if ($result_grad) {
            while ($grad_row = mysqli_fetch_assoc($result_grad)) {
                // Reconstruir estructura de objeto con columnas individuales
                $historial_graduaciones[] = [
                    'id' => intval($grad_row['id']),
                    'fecha' => $grad_row['fecha'],
                    'optometra' => $grad_row['optometra'],
                    'lejos_od' => [
                        'esferico' => $grad_row['lejos_od_esferico'],
                        'cilindro' => $grad_row['lejos_od_cilindro'],
                        'eje' => $grad_row['lejos_od_eje'],
                        'av' => $grad_row['lejos_od_av'],
                        'distp' => $grad_row['lejos_od_distp'],
                        'prisma' => $grad_row['lejos_od_prisma'],
                        'adicmedia' => $grad_row['lejos_od_adicmedia']
                    ],
                    'lejos_oi' => [
                        'esferico' => $grad_row['lejos_oi_esferico'],
                        'cilindro' => $grad_row['lejos_oi_cilindro'],
                        'eje' => $grad_row['lejos_oi_eje'],
                        'av' => $grad_row['lejos_oi_av'],
                        'distp' => $grad_row['lejos_oi_distp'],
                        'prisma' => $grad_row['lejos_oi_prisma'],
                        'adicmedia' => $grad_row['lejos_oi_adicmedia']
                    ],
                    'cerca_od' => [
                        'esferico' => $grad_row['cerca_od_esferico'],
                        'cilindro' => $grad_row['cerca_od_cilindro'],
                        'eje' => $grad_row['cerca_od_eje'],
                        'av' => $grad_row['cerca_od_av'],
                        'prisma' => $grad_row['cerca_od_prisma'],
                        'adicmedia' => $grad_row['cerca_od_adicmedia']
                    ],
                    'cerca_oi' => [
                        'esferico' => $grad_row['cerca_oi_esferico'],
                        'cilindro' => $grad_row['cerca_oi_cilindro'],
                        'eje' => $grad_row['cerca_oi_eje'],
                        'av' => $grad_row['cerca_oi_av'],
                        'prisma' => $grad_row['cerca_oi_prisma'],
                        'adicmedia' => $grad_row['cerca_oi_adicmedia']
                    ],
                    'fecha_registro' => $grad_row['fecha_registro'],
                    'fecha_actualizacion' => $grad_row['fecha_actualizacion']
                ];
            }
        }
        
        // ============================================================================
        // CONSTRUIR OBJETO PACIENTE
        // ============================================================================
        $pacientes[] = [
            'id' => $id_paciente,
            'nombre' => $row['nombre'],
            'dni' => $row['dni'],
            'edad' => intval($row['edad']),
            'genero' => $row['genero'],
            'fecha_nacimiento' => $row['fecha_nacimiento'],
            'fecha_registro' => $row['fecha_registro'],  // ← CRÍTICO para filtrado "nuevos hoy"
            'fecha_actualizacion' => $row['fecha_actualizacion'],
            'codigo_dispositivo' => $has_codigo ? ($row['codigo_dispositivo'] ?? '') : '',
            'dispositivo_nombre' => $has_nombre ? ($row['dispositivo_nombre'] ?? '') : '',
            'tipo_dispositivo' => $has_tipo ? ($row['tipo_dispositivo'] ?? 'madre') : 'madre',
            'historial_graduaciones' => $historial_graduaciones
        ];
    }
    
    mysqli_close($conn);
    
    // ============================================================================
    // RETORNAR RESPUESTA
    // ============================================================================
    echo json_encode([
        'success' => true,
        'pacientes' => $pacientes,
        'total' => count($pacientes)
    ]);
    
} catch (Exception $e) {
    echo json_encode(['success' => false, 'error' => 'Exception: ' . $e->getMessage()]);
}

exit;
?>
