<?php
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
        echo json_encode(['success' => false, 'error' => 'Faltan parametros requeridos']);
        exit;
    }

    $usuario_id = $data['usuario_id'];
    $tipo_dato = $data['tipo_dato'];
    $contenido = isset($data['contenido']) ? $data['contenido'] : array();

    $tipo_dispositivo = strtolower(trim((string)($data['tipo_dispositivo'] ?? 'madre')));
    if ($tipo_dispositivo !== 'trabajador') {
        $tipo_dispositivo = 'madre';
    }
    $codigo_dispositivo = strtoupper(trim((string)($data['codigo_dispositivo'] ?? '')));
    $dispositivo_nombre = trim((string)($data['dispositivo_hijo_nombre'] ?? $data['dispositivo_nombre'] ?? ''));

    if ($tipo_dato !== 'clientes' || !isset($contenido['clientes']) || !is_array($contenido['clientes'])) {
        echo json_encode(['success' => false, 'error' => 'Tipo de dato no valido o datos incompletos']);
        exit;
    }

    $conn = mysqli_connect('localhost', 'u369606320_visoo', getenv('VISO_DB_PASSWORD'), 'u369606320_visoo');
    if (!$conn) {
        echo json_encode(['success' => false, 'error' => 'Conexion BD: ' . mysqli_connect_error()]);
        exit;
    }

    mysqli_set_charset($conn, 'utf8mb4');

    // Columnas para identificar el origen por dispositivo/sucursal.
    ensure_column($conn, 'clientes', 'codigo_dispositivo', "VARCHAR(80) NULL");
    ensure_column($conn, 'clientes', 'dispositivo_nombre', "VARCHAR(255) NULL");
    ensure_column($conn, 'clientes', 'tipo_dispositivo', "VARCHAR(20) NULL DEFAULT 'madre'");

    $has_codigo = has_column($conn, 'clientes', 'codigo_dispositivo');
    $has_nombre = has_column($conn, 'clientes', 'dispositivo_nombre');
    $has_tipo = has_column($conn, 'clientes', 'tipo_dispositivo');

    if (is_numeric($usuario_id)) {
        $usuario_id_sql = intval($usuario_id);
    } else {
        $usuario_id_escaped = mysqli_real_escape_string($conn, $usuario_id);
        $usuario_id_sql = "'$usuario_id_escaped'";
    }

    $codigo_esc = mysqli_real_escape_string($conn, $codigo_dispositivo);
    $nombre_disp_esc = mysqli_real_escape_string($conn, $dispositivo_nombre);
    $tipo_disp_esc = mysqli_real_escape_string($conn, $tipo_dispositivo);

    $errors = [];

    foreach ($contenido['clientes'] as $c) {
        if (!isset($c['nombre'])) {
            continue;
        }

        $nombre = mysqli_real_escape_string($conn, $c['nombre']);
        $dni = isset($c['dni']) ? mysqli_real_escape_string($conn, $c['dni']) : '';
        $edad = isset($c['edad']) ? intval($c['edad']) : 0;
        $genero = isset($c['genero']) ? mysqli_real_escape_string($conn, $c['genero']) : 'M';
        $fecha_nacimiento = isset($c['fecha_nacimiento']) ? mysqli_real_escape_string($conn, $c['fecha_nacimiento']) : date('Y-m-d');
        $id_cliente = isset($c['id']) ? intval($c['id']) : 0;

        if ($id_cliente > 0) {
            $set_parts = [
                "nombre='$nombre'",
                "dni='$dni'",
                "edad=$edad",
                "genero='$genero'",
                "fecha_nacimiento='$fecha_nacimiento'",
                "fecha_actualizacion=NOW()"
            ];
            if ($has_codigo) {
                $set_parts[] = "codigo_dispositivo='$codigo_esc'";
            }
            if ($has_nombre) {
                $set_parts[] = "dispositivo_nombre='$nombre_disp_esc'";
            }
            if ($has_tipo) {
                $set_parts[] = "tipo_dispositivo='$tipo_disp_esc'";
            }

            $query = "UPDATE clientes SET " . implode(', ', $set_parts) . " WHERE id=$id_cliente AND id_usuario=$usuario_id_sql";
            if (!mysqli_query($conn, $query)) {
                $errors[] = 'UPDATE error: ' . mysqli_error($conn);
            }
        } else {
            $insert_cols = [
                'id_usuario', 'nombre', 'dni', 'edad', 'genero', 'fecha_nacimiento', 'fecha_registro', 'fecha_actualizacion'
            ];
            $insert_vals = [
                "$usuario_id_sql", "'$nombre'", "'$dni'", "$edad", "'$genero'", "'$fecha_nacimiento'", 'NOW()', 'NOW()'
            ];
            $update_parts = [
                "nombre='$nombre'",
                "edad=$edad",
                "genero='$genero'",
                "fecha_nacimiento='$fecha_nacimiento'",
                "fecha_actualizacion=NOW()"
            ];

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

            $query = "INSERT INTO clientes (" . implode(', ', $insert_cols) . ") " .
                     "VALUES (" . implode(', ', $insert_vals) . ") " .
                     "ON DUPLICATE KEY UPDATE " . implode(', ', $update_parts);

            if (!mysqli_query($conn, $query)) {
                $errors[] = 'UPSERT error: ' . mysqli_error($conn);
            }
        }
    }

    mysqli_close($conn);

    if ($errors) {
        echo json_encode(['success' => false, 'error' => implode('; ', $errors)]);
    } else {
        echo json_encode(['success' => true, 'message' => 'OK clientes subido exitosamente']);
    }
} catch (Exception $e) {
    echo json_encode(['success' => false, 'error' => 'Exception: ' . $e->getMessage()]);
}
exit;
?>
