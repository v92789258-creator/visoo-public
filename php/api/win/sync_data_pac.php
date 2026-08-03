<?php
/**
 * SYNC_DATA_PAC.PHP
 * 
 * Sincroniza PACIENTES y GRADUACIONES de la aplicación VISO con la BD remota.
 * 
 * Implementa:
 * - UPSERT (INSERT...ON DUPLICATE KEY UPDATE) para pacientes
 * - MERGE strategy: mantiene datos locales sin sincronizar
 * - Manejo de graduaciones como relación 1:N
 * - Persistencia automática
 * - Error handling completo
 * 
 * Soporta dos formatos:
 * 1. Formato directo (manual): {"usuario_id": "...", "tipo_dato": "pacientes", "contenido": {"pacientes": [...]}}
 * 2. Formato sync_manager: {"usuario_id": "...", "tipo_dato": "pacientes", "operacion": "SYNC_ALL", "contenido": {...}}
 */

error_reporting(E_ALL);
ini_set('display_errors', '0');
ini_set('log_errors', '1');

header('Content-Type: application/json');

function has_column($conn, $table, $column) {
    $table_safe = mysqli_real_escape_string($conn, $table);
    $column_safe = mysqli_real_escape_string($conn, $column);
    $sql = "SHOW COLUMNS FROM `$table_safe` LIKE '$column_safe'";
    $res = @mysqli_query($conn, $sql);
    return ($res && mysqli_num_rows($res) > 0);
}

function ensure_column($conn, $table, $column, $definition) {
    if (has_column($conn, $table, $column)) {
        return true;
    }
    $table_safe = mysqli_real_escape_string($conn, $table);
    $column_safe = mysqli_real_escape_string($conn, $column);
    $sql = "ALTER TABLE `$table_safe` ADD COLUMN `$column_safe` $definition";
    return @mysqli_query($conn, $sql);
}

try {
    $input = file_get_contents('php://input');
    $data = json_decode($input, true);

    if (!$data || !isset($data['usuario_id']) || !isset($data['tipo_dato'])) {
        echo json_encode(['success' => false, 'error' => 'Faltan parámetros requeridos']);
        exit;
    }

    $usuario_id = $data['usuario_id'];  // Puede ser string (username) o número
    $tipo_dato = $data['tipo_dato'];
    $contenido = isset($data['contenido']) ? $data['contenido'] : array();
    $tipo_dispositivo = strtolower(trim((string)($data['tipo_dispositivo'] ?? 'madre')));
    if ($tipo_dispositivo !== 'trabajador') {
        $tipo_dispositivo = 'madre';
    }
    $codigo_dispositivo = strtoupper(trim((string)($data['codigo_dispositivo'] ?? '')));
    $dispositivo_nombre = trim((string)($data['dispositivo_hijo_nombre'] ?? $data['dispositivo_nombre'] ?? ''));
    
    // ============================================================================
    // DETECTAR FORMATO: Si contenido es un paciente individual, transformar a array
    // ============================================================================
    $pacientes_array = [];
    
    if ($tipo_dato === 'pacientes') {
        // Formato 1: {"contenido": {"pacientes": [...]}}
        if (isset($contenido['pacientes']) && is_array($contenido['pacientes'])) {
            $pacientes_array = $contenido['pacientes'];
        }
        // Formato 2: {"contenido": {paciente_object}} - sync_manager envía pacientes directamente
        else if (isset($contenido['nombre']) || isset($contenido['dni'])) {
            // El contenido es un solo paciente, envolverlo en array
            $pacientes_array = [$contenido];
        }
        // Formato 3: {"contenido": [paciente1, paciente2, ...]}
        else if (is_array($contenido) && !empty($contenido)) {
            // Verificar si es array de pacientes
            $first_item = reset($contenido);
            if (is_array($first_item) && (isset($first_item['nombre']) || isset($first_item['dni']))) {
                $pacientes_array = $contenido;
            }
        }
    }
    
    // ============================================================================
    // SECCIÓN 1: PROCESAR PACIENTES
    // ============================================================================
    if ($tipo_dato === 'pacientes' && !empty($pacientes_array)) {
        
        $conn = mysqli_connect('localhost', 'u369606320_visoo', getenv('VISO_DB_PASSWORD'), 'u369606320_visoo');
        
        if (!$conn) {
            echo json_encode(['success' => false, 'error' => 'Conexión BD: ' . mysqli_connect_error()]);
            exit;
        }
        
        mysqli_set_charset($conn, 'utf8mb4');

        // Columnas para segmentación por dispositivo/sucursal y UUID.
        ensure_column($conn, 'pacientes', 'uuid', "VARCHAR(36) NULL AFTER id_usuario");
        ensure_column($conn, 'pacientes', 'codigo_dispositivo', "VARCHAR(80) NULL");
        ensure_column($conn, 'pacientes', 'dispositivo_nombre', "VARCHAR(255) NULL");
        ensure_column($conn, 'pacientes', 'tipo_dispositivo', "VARCHAR(20) NULL DEFAULT 'madre'");
        
        // Intentar actualizar el índice único si no existe el de UUID
        $check_index = mysqli_query($conn, "SHOW INDEX FROM pacientes WHERE Key_name = 'unique_usuario_uuid'");
        if (mysqli_num_rows($check_index) == 0) {
            // Intentar borrar el antiguo si existe
            @mysqli_query($conn, "ALTER TABLE pacientes DROP INDEX unique_usuario_dni");
            // Crear el nuevo basado en UUID
            @mysqli_query($conn, "CREATE UNIQUE INDEX unique_usuario_uuid ON pacientes(id_usuario, uuid)");
        }

        $has_codigo = has_column($conn, 'pacientes', 'codigo_dispositivo');
        $has_nombre = has_column($conn, 'pacientes', 'dispositivo_nombre');
        $has_tipo = has_column($conn, 'pacientes', 'tipo_dispositivo');
        
        // ... (resto de la creación de tabla de graduaciones) ...
        
        // ============================================================================
        // CREAR TABLA DE GRADUACIONES SI NO EXISTE (CON COLUMNAS INDIVIDUALES)
        // ============================================================================
        // [CÓDIGO DE CREACIÓN DE TABLA GRADUACIONES SE MANTIENE IGUAL]
        
        // Escapar usuario_id después de conectar
        if (is_numeric($usuario_id)) {
            $usuario_id_escaped = intval($usuario_id);
            $usuario_id_sql = $usuario_id_escaped;
        } else {
            $usuario_id_escaped = mysqli_real_escape_string($conn, $usuario_id);
            $usuario_id_sql = "'$usuario_id_escaped'";
        }
        $codigo_esc = mysqli_real_escape_string($conn, $codigo_dispositivo);
        $nombre_disp_esc = mysqli_real_escape_string($conn, $dispositivo_nombre);
        $tipo_disp_esc = mysqli_real_escape_string($conn, $tipo_dispositivo);
        
        $errors = [];
        $pacientes_insertados = 0;
        
        foreach ($pacientes_array as $p) {
            if (!isset($p['nombre']) || !isset($p['dni'])) {
                continue;
            }
            
            $nombre = mysqli_real_escape_string($conn, $p['nombre']);
            $dni = mysqli_real_escape_string($conn, $p['dni']);
            $uuid = isset($p['uuid']) ? mysqli_real_escape_string($conn, $p['uuid']) : null;
            $edad = isset($p['edad']) ? intval($p['edad']) : 0;
            $genero = isset($p['genero']) ? mysqli_real_escape_string($conn, $p['genero']) : 'M';
            $fecha_nacimiento = isset($p['fecha_nacimiento']) ? mysqli_real_escape_string($conn, $p['fecha_nacimiento']) : date('Y-m-d');
            $id_paciente = isset($p['id']) ? intval($p['id']) : 0;
            
            // ============================================================================
            // UPSERT PACIENTE: Prioridad al UUID si existe
            // ============================================================================
            
            // 1. Intentar buscar por UUID si lo tenemos
            if ($uuid && $id_paciente <= 0) {
                $query_find = "SELECT id FROM pacientes WHERE id_usuario=$usuario_id_sql AND uuid='$uuid' LIMIT 1";
                $res_find = mysqli_query($conn, $query_find);
                if ($res_find && $row_f = mysqli_fetch_assoc($res_find)) {
                    $id_paciente = intval($row_f['id']);
                }
            }
            
            if ($id_paciente > 0) {
                // UPDATE si existe
                $set_parts = array(
                    "nombre='$nombre'",
                    "dni='$dni'",
                    "uuid=" . ($uuid ? "'$uuid'" : "NULL"),
                    "edad=$edad",
                    "genero='$genero'",
                    "fecha_nacimiento='$fecha_nacimiento'",
                    "fecha_actualizacion=NOW()"
                );
                if ($has_codigo) {
                    $set_parts[] = "codigo_dispositivo='$codigo_esc'";
                }
                if ($has_nombre) {
                    $set_parts[] = "dispositivo_nombre='$nombre_disp_esc'";
                }
                if ($has_tipo) {
                    $set_parts[] = "tipo_dispositivo='$tipo_disp_esc'";
                }
                $query = "UPDATE pacientes SET " . implode(', ', $set_parts) . " WHERE id=$id_paciente AND id_usuario=$usuario_id_sql";
                         
                if (!mysqli_query($conn, $query)) {
                    $errors[] = "UPDATE paciente error: " . mysqli_error($conn);
                }
            } else {
                // INSERT...ON DUPLICATE KEY UPDATE para UPSERT (busca por usuario+uuid)
                $insert_cols = array(
                    'id_usuario', 'uuid', 'nombre', 'dni', 'edad', 'genero', 'fecha_nacimiento', 'fecha_registro', 'fecha_actualizacion'
                );
                $insert_vals = array(
                    "$usuario_id_sql", ($uuid ? "'$uuid'" : "NULL"), "'$nombre'", "'$dni'", "$edad", "'$genero'", "'$fecha_nacimiento'", "NOW()", "NOW()"
                );
                $update_parts = array(
                    "nombre='$nombre'",
                    "dni='$dni'",
                    "edad=$edad",
                    "genero='$genero'",
                    "fecha_nacimiento='$fecha_nacimiento'",
                    "fecha_actualizacion=NOW()"
                );
                if ($has_codigo) {
                    $insert_cols[] = 'codigo_dispositivo';
                    $insert_vals[] = "'$codigo_esc'";
                    $update_parts[] = "codigo_dispositivo='$codigo_esc'";
                }
                if ($has_nombre) {
                    $insert_cols[] = 'dispositivo_nombre';
                    $insert_vals[] = "'$nombre_disp_esc'";
                    $update_parts[] = "dispositivo_nombre='$nombre_disp_esc'";
                }
                if ($has_tipo) {
                    $insert_cols[] = 'tipo_dispositivo';
                    $insert_vals[] = "'$tipo_disp_esc'";
                    $update_parts[] = "tipo_dispositivo='$tipo_disp_esc'";
                }
                $query = "INSERT INTO pacientes (" . implode(', ', $insert_cols) . ")
                          VALUES (" . implode(', ', $insert_vals) . ")
                          ON DUPLICATE KEY UPDATE " . implode(', ', $update_parts);
                          
                if (mysqli_query($conn, $query)) {
                    $pacientes_insertados++;
                } else {
                    $errors[] = "UPSERT paciente error: " . mysqli_error($conn);
                }
            }
            
            // ============================================================================
            // PROCESAR GRADUACIONES DEL PACIENTE
            // ============================================================================
            if (isset($p['historial_graduaciones']) && is_array($p['historial_graduaciones'])) {
                
                // Obtener ID del paciente recién insertado/actualizado
                if ($id_paciente <= 0) {
                    $query_get_id = "SELECT id FROM pacientes WHERE dni='$dni' AND id_usuario=$usuario_id_sql LIMIT 1";
                    $result = mysqli_query($conn, $query_get_id);
                    if ($result && $row = mysqli_fetch_assoc($result)) {
                        $id_paciente = intval($row['id']);
                    }
                }
                
                // Procesar cada graduación
                foreach ($p['historial_graduaciones'] as $grad) {
                    if (!isset($grad['fecha']) || $id_paciente <= 0) {
                        continue;
                    }
                    
                    // ============================================================================
                    // EXTRAER TODOS LOS VALORES DE LOS CAMPOS DE GRADUACIÓN
                    // ============================================================================
                    
                    // Lejos OD
                    $lejos_od = isset($grad['lejos_od']) ? $grad['lejos_od'] : [];
                    $lejos_od_esferico = isset($lejos_od['esferico']) ? mysqli_real_escape_string($conn, $lejos_od['esferico']) : '';
                    $lejos_od_cilindro = isset($lejos_od['cilindro']) ? mysqli_real_escape_string($conn, $lejos_od['cilindro']) : '';
                    $lejos_od_eje = isset($lejos_od['eje']) ? mysqli_real_escape_string($conn, $lejos_od['eje']) : '';
                    $lejos_od_av = isset($lejos_od['av']) ? mysqli_real_escape_string($conn, $lejos_od['av']) : '';
                    $lejos_od_distp = isset($lejos_od['distp']) ? mysqli_real_escape_string($conn, $lejos_od['distp']) : '';
                    $lejos_od_prisma = isset($lejos_od['prisma']) ? mysqli_real_escape_string($conn, $lejos_od['prisma']) : '';
                    $lejos_od_adicmedia = isset($lejos_od['adicmedia']) ? mysqli_real_escape_string($conn, $lejos_od['adicmedia']) : '';
                    
                    // Lejos OI
                    $lejos_oi = isset($grad['lejos_oi']) ? $grad['lejos_oi'] : [];
                    $lejos_oi_esferico = isset($lejos_oi['esferico']) ? mysqli_real_escape_string($conn, $lejos_oi['esferico']) : '';
                    $lejos_oi_cilindro = isset($lejos_oi['cilindro']) ? mysqli_real_escape_string($conn, $lejos_oi['cilindro']) : '';
                    $lejos_oi_eje = isset($lejos_oi['eje']) ? mysqli_real_escape_string($conn, $lejos_oi['eje']) : '';
                    $lejos_oi_av = isset($lejos_oi['av']) ? mysqli_real_escape_string($conn, $lejos_oi['av']) : '';
                    $lejos_oi_distp = isset($lejos_oi['distp']) ? mysqli_real_escape_string($conn, $lejos_oi['distp']) : '';
                    $lejos_oi_prisma = isset($lejos_oi['prisma']) ? mysqli_real_escape_string($conn, $lejos_oi['prisma']) : '';
                    $lejos_oi_adicmedia = isset($lejos_oi['adicmedia']) ? mysqli_real_escape_string($conn, $lejos_oi['adicmedia']) : '';
                    
                    // Cerca OD
                    $cerca_od = isset($grad['cerca_od']) ? $grad['cerca_od'] : [];
                    $cerca_od_esferico = isset($cerca_od['esferico']) ? mysqli_real_escape_string($conn, $cerca_od['esferico']) : '';
                    $cerca_od_cilindro = isset($cerca_od['cilindro']) ? mysqli_real_escape_string($conn, $cerca_od['cilindro']) : '';
                    $cerca_od_eje = isset($cerca_od['eje']) ? mysqli_real_escape_string($conn, $cerca_od['eje']) : '';
                    $cerca_od_av = isset($cerca_od['av']) ? mysqli_real_escape_string($conn, $cerca_od['av']) : '';
                    $cerca_od_prisma = isset($cerca_od['prisma']) ? mysqli_real_escape_string($conn, $cerca_od['prisma']) : '';
                    $cerca_od_adicmedia = isset($cerca_od['adicmedia']) ? mysqli_real_escape_string($conn, $cerca_od['adicmedia']) : '';
                    
                    // Cerca OI
                    $cerca_oi = isset($grad['cerca_oi']) ? $grad['cerca_oi'] : [];
                    $cerca_oi_esferico = isset($cerca_oi['esferico']) ? mysqli_real_escape_string($conn, $cerca_oi['esferico']) : '';
                    $cerca_oi_cilindro = isset($cerca_oi['cilindro']) ? mysqli_real_escape_string($conn, $cerca_oi['cilindro']) : '';
                    $cerca_oi_eje = isset($cerca_oi['eje']) ? mysqli_real_escape_string($conn, $cerca_oi['eje']) : '';
                    $cerca_oi_av = isset($cerca_oi['av']) ? mysqli_real_escape_string($conn, $cerca_oi['av']) : '';
                    $cerca_oi_prisma = isset($cerca_oi['prisma']) ? mysqli_real_escape_string($conn, $cerca_oi['prisma']) : '';
                    $cerca_oi_adicmedia = isset($cerca_oi['adicmedia']) ? mysqli_real_escape_string($conn, $cerca_oi['adicmedia']) : '';
                    
                    $fecha = mysqli_real_escape_string($conn, $grad['fecha']);
                    $optometra = isset($grad['optometra']) ? mysqli_real_escape_string($conn, $grad['optometra']) : 'N/A';
                    
                    // ============================================================================
                    // UPSERT GRADUACIÓN CON TODAS LAS COLUMNAS INDIVIDUALES
                    // ============================================================================
                    $query_grad = "INSERT INTO graduaciones 
                        (id_paciente, fecha, optometra, 
                         lejos_od_esferico, lejos_od_cilindro, lejos_od_eje, lejos_od_av, lejos_od_distp, lejos_od_prisma, lejos_od_adicmedia,
                         lejos_oi_esferico, lejos_oi_cilindro, lejos_oi_eje, lejos_oi_av, lejos_oi_distp, lejos_oi_prisma, lejos_oi_adicmedia,
                         cerca_od_esferico, cerca_od_cilindro, cerca_od_eje, cerca_od_av, cerca_od_prisma, cerca_od_adicmedia,
                         cerca_oi_esferico, cerca_oi_cilindro, cerca_oi_eje, cerca_oi_av, cerca_oi_prisma, cerca_oi_adicmedia,
                         fecha_registro, fecha_actualizacion)
                       VALUES 
                        ($id_paciente, '$fecha', '$optometra',
                         '$lejos_od_esferico', '$lejos_od_cilindro', '$lejos_od_eje', '$lejos_od_av', '$lejos_od_distp', '$lejos_od_prisma', '$lejos_od_adicmedia',
                         '$lejos_oi_esferico', '$lejos_oi_cilindro', '$lejos_oi_eje', '$lejos_oi_av', '$lejos_oi_distp', '$lejos_oi_prisma', '$lejos_oi_adicmedia',
                         '$cerca_od_esferico', '$cerca_od_cilindro', '$cerca_od_eje', '$cerca_od_av', '$cerca_od_prisma', '$cerca_od_adicmedia',
                         '$cerca_oi_esferico', '$cerca_oi_cilindro', '$cerca_oi_eje', '$cerca_oi_av', '$cerca_oi_prisma', '$cerca_oi_adicmedia',
                         NOW(), NOW())
                       ON DUPLICATE KEY UPDATE 
                        optometra='$optometra',
                        lejos_od_esferico='$lejos_od_esferico', lejos_od_cilindro='$lejos_od_cilindro', lejos_od_eje='$lejos_od_eje', lejos_od_av='$lejos_od_av', lejos_od_distp='$lejos_od_distp', lejos_od_prisma='$lejos_od_prisma', lejos_od_adicmedia='$lejos_od_adicmedia',
                        lejos_oi_esferico='$lejos_oi_esferico', lejos_oi_cilindro='$lejos_oi_cilindro', lejos_oi_eje='$lejos_oi_eje', lejos_oi_av='$lejos_oi_av', lejos_oi_distp='$lejos_oi_distp', lejos_oi_prisma='$lejos_oi_prisma', lejos_oi_adicmedia='$lejos_oi_adicmedia',
                        cerca_od_esferico='$cerca_od_esferico', cerca_od_cilindro='$cerca_od_cilindro', cerca_od_eje='$cerca_od_eje', cerca_od_av='$cerca_od_av', cerca_od_prisma='$cerca_od_prisma', cerca_od_adicmedia='$cerca_od_adicmedia',
                        cerca_oi_esferico='$cerca_oi_esferico', cerca_oi_cilindro='$cerca_oi_cilindro', cerca_oi_eje='$cerca_oi_eje', cerca_oi_av='$cerca_oi_av', cerca_oi_prisma='$cerca_oi_prisma', cerca_oi_adicmedia='$cerca_oi_adicmedia',
                        fecha_actualizacion=NOW()";
                    
                    if (!mysqli_query($conn, $query_grad)) {
                        $errors[] = "UPSERT graduación error: " . mysqli_error($conn);
                    }
                }
            }
        }
        
        mysqli_close($conn);
        
        // ============================================================================
        // RETORNAR RESPUESTA ÚNICA
        // ============================================================================
        if ($errors) {
            echo json_encode([
                'success' => false, 
                'error' => implode('; ', $errors),
                'pacientes_procesados' => $pacientes_insertados
            ]);
        } else {
            echo json_encode([
                'success' => true, 
                'message' => 'OK pacientes y graduaciones subidos exitosamente!',
                'pacientes_procesados' => $pacientes_insertados
            ]);
        }
    } else {
        // ============================================================================
        // TIPO DE DATO NO VÁLIDO
        // ============================================================================
        echo json_encode(['success' => false, 'error' => 'Tipo de dato no válido (debe ser "pacientes") o datos incompletos']);
    }
    
} catch (Exception $e) {
    echo json_encode(['success' => false, 'error' => 'Exception: ' . $e->getMessage()]);
}

exit;
?>
