<?php
header('Content-Type: application/json');

function has_column($conn, $table, $column) {
    $table_safe = mysqli_real_escape_string($conn, $table);
    $column_safe = mysqli_real_escape_string($conn, $column);
    $sql = "SHOW COLUMNS FROM `$table_safe` LIKE '$column_safe'";
    $res = @mysqli_query($conn, $sql);
    return ($res && mysqli_num_rows($res) > 0);
}

$input = file_get_contents('php://input');
$data = json_decode($input, true);

if (!$data || !isset($data['usuario_id'])) {
    echo json_encode(['success' => false, 'clientes' => []]);
    exit;
}

$usuario_id = $data['usuario_id'];
$codigo_dispositivo = strtoupper(trim((string)($data['codigo_dispositivo'] ?? '')));

$conn = @mysqli_connect('localhost', 'u369606320_visoo', getenv('VISO_DB_PASSWORD'), 'u369606320_visoo');
if (!$conn) {
    echo json_encode(['success' => false, 'clientes' => []]);
    exit;
}

@mysqli_set_charset($conn, 'utf8mb4');

$has_codigo = has_column($conn, 'clientes', 'codigo_dispositivo');
$has_nombre = has_column($conn, 'clientes', 'dispositivo_nombre');
$has_tipo = has_column($conn, 'clientes', 'tipo_dispositivo');

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

$usuario_id_escaped = @mysqli_real_escape_string($conn, $usuario_id);
$query = "SELECT $select_fields FROM clientes WHERE id_usuario='$usuario_id_escaped'";

if ($codigo_dispositivo !== '' && $has_codigo) {
    $codigo_esc = mysqli_real_escape_string($conn, $codigo_dispositivo);
    $query .= " AND codigo_dispositivo='$codigo_esc'";
}

$query .= " ORDER BY fecha_actualizacion DESC";

$result = @mysqli_query($conn, $query);
$clientes = [];

if ($result) {
    while ($row = mysqli_fetch_assoc($result)) {
        $clientes[] = array(
            'id' => intval($row['id']),
            'nombre' => $row['nombre'],
            'dni' => $row['dni'],
            'edad' => intval($row['edad']),
            'genero' => $row['genero'],
            'fecha_nacimiento' => $row['fecha_nacimiento'],
            'fecha_registro' => $row['fecha_registro'],
            'codigo_dispositivo' => $has_codigo ? ($row['codigo_dispositivo'] ?? '') : '',
            'dispositivo_nombre' => $has_nombre ? ($row['dispositivo_nombre'] ?? '') : '',
            'tipo_dispositivo' => $has_tipo ? ($row['tipo_dispositivo'] ?? 'madre') : 'madre'
        );
    }
}

@mysqli_close($conn);

echo json_encode(['success' => true, 'clientes' => $clientes]);
exit;
?>
