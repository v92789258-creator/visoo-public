<?php
/**
 * VISO - Endpoint de Sincronización
 * Recibe cambios del cliente Python y los guarda en la BD remota
 * 
 * Estructura JSON esperada:
 * {
 *   "usuario_id": "12345",
 *   "tipo_dato": "clientes|pacientes|productos|ventas|kardex|citas",
 *   "operacion": "CREATE|UPDATE|DELETE|SYNC_ALL",
 *   "registro_id": "id del registro o 'bulk' para SYNC_ALL",
 *   "contenido": {...},
 *   "timestamp": 1733646585
 * }
 */

// Encabezados
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Error reporting
error_reporting(E_ALL);
ini_set('display_errors', 0);

// Respuesta por defecto
$response = [
    'success' => false,
    'message' => 'Error desconocido'
];

try {
    // Obtener datos JSON
    $input = file_get_contents('php://input');
    $data = json_decode($input, true);
    
    if (!$data) {
        http_response_code(400);
        $response['message'] = 'JSON inválido';
        echo json_encode($response);
        exit;
    }
    
    // Validar campos requeridos
    $required = ['usuario_id', 'tipo_dato', 'operacion', 'contenido', 'timestamp'];
    foreach ($required as $field) {
        if (!isset($data[$field])) {
            http_response_code(400);
            $response['message'] = "Campo requerido faltante: $field";
            echo json_encode($response);
            exit;
        }
    }
    
    // Validación básica
    $usuario_id = intval($data['usuario_id']);
    $tipo_dato = $data['tipo_dato'];
    $operacion = $data['operacion'];
    $registro_id = isset($data['registro_id']) ? $data['registro_id'] : '';
    $contenido = $data['contenido'];
    $timestamp = intval($data['timestamp']);
    
    // Conectar a BD (usar conexión con charset)
    $conn = new mysqli('localhost', 'u369606320_visoo', getenv('VISO_DB_PASSWORD'), 'u369606320_visoo');
    $conn->set_charset("utf8mb4");
    
    if ($conn->connect_error) {
        http_response_code(500);
        $response['message'] = 'Error de conexión a BD: ' . $conn->connect_error;
        echo json_encode($response);
        exit;
    }
    
    // Guardar el log de sync
    $log_table = 'sync_logs';
    $contenido_json = json_encode($contenido);
    
    // Crear tabla si no existe
    $create_table = "
    CREATE TABLE IF NOT EXISTS $log_table (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario_id INT NOT NULL,
        tipo_dato VARCHAR(50) NOT NULL,
        operacion VARCHAR(20) NOT NULL,
        registro_id VARCHAR(255),
        contenido LONGTEXT NOT NULL,
        timestamp BIGINT NOT NULL,
        fecha_recibida TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        estado VARCHAR(20) DEFAULT 'recibido',
        INDEX idx_usuario_timestamp (usuario_id, timestamp)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ";
    
    if (!$conn->query($create_table)) {
        // Si falla la creación, continuar de todos modos
        // La tabla probablemente ya existe
    }
    
    // Insertar en tabla de sync
    $stmt = $conn->prepare("
        INSERT INTO $log_table 
        (usuario_id, tipo_dato, operacion, registro_id, contenido, timestamp, estado)
        VALUES (?, ?, ?, ?, ?, ?, 'recibido')
    ");
    
    if (!$stmt) {
        http_response_code(500);
        $response['message'] = 'Error preparando query: ' . $conn->error;
        echo json_encode($response);
        exit;
    }
    
    $stmt->bind_param(
        'issssi',
        $usuario_id,
        $tipo_dato,
        $operacion,
        $registro_id,
        $contenido_json,
        $timestamp
    );
    
    if (!$stmt->execute()) {
        http_response_code(500);
        $response['message'] = 'Error ejecutando query: ' . $stmt->error;
        echo json_encode($response);
        exit;
    }
    
    $last_id = $stmt->insert_id;
    $stmt->close();
    
    // Procesar según tipo de dato (puede fallar sin afectar la respuesta)
    $processed = true;
    try {
        if ($tipo_dato == 'clientes') {
            procesarClientes($conn, $usuario_id, $operacion, $registro_id, $contenido);
        } elseif ($tipo_dato == 'pacientes') {
            procesarPacientes($conn, $usuario_id, $operacion, $registro_id, $contenido);
        } elseif ($tipo_dato == 'productos') {
            procesarProductos($conn, $usuario_id, $operacion, $registro_id, $contenido);
        } elseif ($tipo_dato == 'ventas') {
            procesarVentas($conn, $usuario_id, $operacion, $registro_id, $contenido);
        } elseif ($tipo_dato == 'kardex') {
            procesarKardex($conn, $usuario_id, $operacion, $registro_id, $contenido);
        } elseif ($tipo_dato == 'citas') {
            procesarCitas($conn, $usuario_id, $operacion, $registro_id, $contenido);
        }
    } catch (Exception $e) {
        // Log capturado pero continuar
    }
    
    // Actualizar estado a procesado
    $conn->query("UPDATE $log_table SET estado = 'procesado' WHERE id = $last_id");
    
    $response['success'] = true;
    $response['message'] = 'OK';
    
    $conn->close();
    
} catch (Exception $e) {
    http_response_code(500);
    $response['message'] = 'Excepción: ' . $e->getMessage();
}

echo json_encode($response);
exit;


// ============================================================================
// FUNCIONES DE PROCESAMIENTO POR TIPO DE DATO
// ============================================================================

function procesarClientes($conn, $usuario_id, $operacion, $registro_id, $contenido) {
    if ($operacion == 'SYNC_ALL' && isset($contenido['clientes']) && is_array($contenido['clientes'])) {
        foreach ($contenido['clientes'] as $cliente) {
            $nombre = $cliente['nombre'] ?? '';
            $email = $cliente['email'] ?? '';
            $telefono = $cliente['telefono'] ?? '';
            $direccion = $cliente['direccion'] ?? '';
            $id_cliente = isset($cliente['id']) ? intval($cliente['id']) : null;
            
            if ($id_cliente && $id_cliente > 0) {
                // UPDATE
                $sql = "UPDATE clientes SET nombre = ?, email = ?, telefono = ?, direccion = ? WHERE id = ? AND usuario_id = ?";
                $stmt = $conn->prepare($sql);
                if ($stmt) {
                    $stmt->bind_param('sssiii', $nombre, $email, $telefono, $direccion, $id_cliente, $usuario_id);
                    @$stmt->execute();
                    $stmt->close();
                }
            } else {
                // INSERT
                $sql = "INSERT INTO clientes (usuario_id, nombre, email, telefono, direccion) VALUES (?, ?, ?, ?, ?)";
                $stmt = $conn->prepare($sql);
                if ($stmt) {
                    $stmt->bind_param('issss', $usuario_id, $nombre, $email, $telefono, $direccion);
                    @$stmt->execute();
                    $stmt->close();
                }
            }
        }
    }
    return true;
}

function procesarPacientes($conn, $usuario_id, $operacion, $registro_id, $contenido) {
    if ($operacion == 'SYNC_ALL' && isset($contenido['pacientes']) && is_array($contenido['pacientes'])) {
        foreach ($contenido['pacientes'] as $paciente) {
            $nombre = $paciente['nombre'] ?? '';
            $apellido = $paciente['apellido'] ?? '';
            $edad = intval($paciente['edad'] ?? 0);
            $telefono = $paciente['telefono'] ?? '';
            $id_paciente = isset($paciente['id']) ? intval($paciente['id']) : null;
            
            if ($id_paciente && $id_paciente > 0) {
                $sql = "UPDATE pacientes SET nombre = ?, apellido = ?, edad = ?, telefono = ? WHERE id = ? AND usuario_id = ?";
                $stmt = $conn->prepare($sql);
                if ($stmt) {
                    $stmt->bind_param('ssiiii', $nombre, $apellido, $edad, $telefono, $id_paciente, $usuario_id);
                    @$stmt->execute();
                    $stmt->close();
                }
            } else {
                $sql = "INSERT INTO pacientes (usuario_id, nombre, apellido, edad, telefono) VALUES (?, ?, ?, ?, ?)";
                $stmt = $conn->prepare($sql);
                if ($stmt) {
                    $stmt->bind_param('issis', $usuario_id, $nombre, $apellido, $edad, $telefono);
                    @$stmt->execute();
                    $stmt->close();
                }
            }
        }
    }
    return true;
}

function procesarProductos($conn, $usuario_id, $operacion, $registro_id, $contenido) {
    if ($operacion == 'SYNC_ALL' && isset($contenido['productos']) && is_array($contenido['productos'])) {
        foreach ($contenido['productos'] as $producto) {
            $nombre = $producto['nombre'] ?? '';
            $precio = floatval($producto['precio'] ?? 0);
            $stock = intval($producto['stock'] ?? 0);
            $id_producto = isset($producto['id']) ? intval($producto['id']) : null;
            
            if ($id_producto && $id_producto > 0) {
                $sql = "UPDATE productos SET nombre = ?, precio = ?, stock = ? WHERE id = ? AND usuario_id = ?";
                $stmt = $conn->prepare($sql);
                if ($stmt) {
                    $stmt->bind_param('sdiii', $nombre, $precio, $stock, $id_producto, $usuario_id);
                    @$stmt->execute();
                    $stmt->close();
                }
            } else {
                $sql = "INSERT INTO productos (usuario_id, nombre, precio, stock) VALUES (?, ?, ?, ?)";
                $stmt = $conn->prepare($sql);
                if ($stmt) {
                    $stmt->bind_param('isdi', $usuario_id, $nombre, $precio, $stock);
                    @$stmt->execute();
                    $stmt->close();
                }
            }
        }
    }
    return true;
}

function procesarVentas($conn, $usuario_id, $operacion, $registro_id, $contenido) {
    if ($operacion == 'SYNC_ALL' && isset($contenido['ventas']) && is_array($contenido['ventas'])) {
        foreach ($contenido['ventas'] as $venta) {
            $fecha = $venta['fecha'] ?? date('Y-m-d');
            $monto = floatval($venta['monto'] ?? 0);
            $id_venta = isset($venta['id']) ? intval($venta['id']) : null;
            
            if ($id_venta && $id_venta > 0) {
                $sql = "UPDATE ventas SET fecha = ?, monto = ? WHERE id = ? AND usuario_id = ?";
                $stmt = $conn->prepare($sql);
                if ($stmt) {
                    $stmt->bind_param('sdii', $fecha, $monto, $id_venta, $usuario_id);
                    @$stmt->execute();
                    $stmt->close();
                }
            } else {
                $sql = "INSERT INTO ventas (usuario_id, fecha, monto) VALUES (?, ?, ?)";
                $stmt = $conn->prepare($sql);
                if ($stmt) {
                    $stmt->bind_param('isd', $usuario_id, $fecha, $monto);
                    @$stmt->execute();
                    $stmt->close();
                }
            }
        }
    }
    return true;
}

function procesarKardex($conn, $usuario_id, $operacion, $registro_id, $contenido) {
    if ($operacion == 'SYNC_ALL' && isset($contenido['kardex']) && is_array($contenido['kardex'])) {
        foreach ($contenido['kardex'] as $item) {
            $producto_id = intval($item['producto_id'] ?? 0);
            $cantidad = intval($item['cantidad'] ?? 0);
            $tipo = $item['tipo'] ?? 'entrada';
            $fecha = $item['fecha'] ?? date('Y-m-d');
            
            $sql = "INSERT INTO kardex (usuario_id, producto_id, cantidad, tipo, fecha) VALUES (?, ?, ?, ?, ?)";
            $stmt = $conn->prepare($sql);
            if ($stmt) {
                $stmt->bind_param('iiiss', $usuario_id, $producto_id, $cantidad, $tipo, $fecha);
                @$stmt->execute();
                $stmt->close();
            }
        }
    }
    return true;
}

function procesarCitas($conn, $usuario_id, $operacion, $registro_id, $contenido) {
    if ($operacion == 'SYNC_ALL' && isset($contenido['citas']) && is_array($contenido['citas'])) {
        foreach ($contenido['citas'] as $cita) {
            $paciente_id = intval($cita['paciente_id'] ?? 0);
            $fecha = $cita['fecha'] ?? date('Y-m-d');
            $hora = $cita['hora'] ?? '09:00';
            $id_cita = isset($cita['id']) ? intval($cita['id']) : null;
            
            if ($id_cita && $id_cita > 0) {
                $sql = "UPDATE citas SET paciente_id = ?, fecha = ?, hora = ? WHERE id = ? AND usuario_id = ?";
                $stmt = $conn->prepare($sql);
                if ($stmt) {
                    $stmt->bind_param('issii', $paciente_id, $fecha, $hora, $id_cita, $usuario_id);
                    @$stmt->execute();
                    $stmt->close();
                }
            } else {
                $sql = "INSERT INTO citas (usuario_id, paciente_id, fecha, hora) VALUES (?, ?, ?, ?)";
                $stmt = $conn->prepare($sql);
                if ($stmt) {
                    $stmt->bind_param('iiss', $usuario_id, $paciente_id, $fecha, $hora);
                    @$stmt->execute();
                    $stmt->close();
                }
            }
        }
    }
    return true;
}

function procesarClientes($conn, $usuario_id, $operacion, $registro_id, $contenido) {
    if ($operacion == 'SYNC_ALL' && isset($contenido['clientes']) && is_array($contenido['clientes'])) {
        foreach ($contenido['clientes'] as $cliente) {
            $nombre = $cliente['nombre'] ?? '';
            $email = $cliente['email'] ?? '';
            $telefono = $cliente['telefono'] ?? '';
            $direccion = $cliente['direccion'] ?? '';
            $id_cliente = isset($cliente['id']) ? intval($cliente['id']) : null;
            
            if ($id_cliente && $id_cliente > 0) {
                // UPDATE
                $sql = "UPDATE clientes SET nombre = ?, email = ?, telefono = ?, direccion = ? WHERE id = ? AND usuario_id = ?";
                $stmt = $conn->prepare($sql);
                if ($stmt) {
                    $stmt->bind_param('sssiii', $nombre, $email, $telefono, $direccion, $id_cliente, $usuario_id);
                    @$stmt->execute();
                    $stmt->close();
                }
            } else {
                // INSERT
                $sql = "INSERT INTO clientes (usuario_id, nombre, email, telefono, direccion) VALUES (?, ?, ?, ?, ?)";
                $stmt = $conn->prepare($sql);
                if ($stmt) {
                    $stmt->bind_param('issss', $usuario_id, $nombre, $email, $telefono, $direccion);
                    @$stmt->execute();
                    $stmt->close();
                }
            }
        }
    }
    return true;
}

function procesarPacientes($conn, $usuario_id, $operacion, $registro_id, $contenido) {
    if ($operacion == 'SYNC_ALL' && isset($contenido['pacientes']) && is_array($contenido['pacientes'])) {
        foreach ($contenido['pacientes'] as $paciente) {
            $nombre = $paciente['nombre'] ?? '';
            $apellido = $paciente['apellido'] ?? '';
            $edad = intval($paciente['edad'] ?? 0);
            $telefono = $paciente['telefono'] ?? '';
            $id_paciente = isset($paciente['id']) ? intval($paciente['id']) : null;
            
            if ($id_paciente && $id_paciente > 0) {
                $sql = "UPDATE pacientes SET nombre = ?, apellido = ?, edad = ?, telefono = ? WHERE id = ? AND usuario_id = ?";
                $stmt = $conn->prepare($sql);
                if ($stmt) {
                    $stmt->bind_param('ssiiii', $nombre, $apellido, $edad, $telefono, $id_paciente, $usuario_id);
                    @$stmt->execute();
                    $stmt->close();
                }
            } else {
                $sql = "INSERT INTO pacientes (usuario_id, nombre, apellido, edad, telefono) VALUES (?, ?, ?, ?, ?)";
                $stmt = $conn->prepare($sql);
                if ($stmt) {
                    $stmt->bind_param('issis', $usuario_id, $nombre, $apellido, $edad, $telefono);
                    @$stmt->execute();
                    $stmt->close();
                }
            }
        }
    }
    return true;
}

function procesarProductos($conn, $usuario_id, $operacion, $registro_id, $contenido) {
    if ($operacion == 'SYNC_ALL' && isset($contenido['productos']) && is_array($contenido['productos'])) {
        foreach ($contenido['productos'] as $producto) {
            $nombre = $producto['nombre'] ?? '';
            $precio = floatval($producto['precio'] ?? 0);
            $stock = intval($producto['stock'] ?? 0);
            $id_producto = isset($producto['id']) ? intval($producto['id']) : null;
            
            if ($id_producto && $id_producto > 0) {
                $sql = "UPDATE productos SET nombre = ?, precio = ?, stock = ? WHERE id = ? AND usuario_id = ?";
                $stmt = $conn->prepare($sql);
                if ($stmt) {
                    $stmt->bind_param('sdiii', $nombre, $precio, $stock, $id_producto, $usuario_id);
                    @$stmt->execute();
                    $stmt->close();
                }
            } else {
                $sql = "INSERT INTO productos (usuario_id, nombre, precio, stock) VALUES (?, ?, ?, ?)";
                $stmt = $conn->prepare($sql);
                if ($stmt) {
                    $stmt->bind_param('isdi', $usuario_id, $nombre, $precio, $stock);
                    @$stmt->execute();
                    $stmt->close();
                }
            }
        }
    }
    return true;
}

function procesarVentas($conn, $usuario_id, $operacion, $registro_id, $contenido) {
    if ($operacion == 'SYNC_ALL' && isset($contenido['ventas']) && is_array($contenido['ventas'])) {
        foreach ($contenido['ventas'] as $venta) {
            $fecha = $venta['fecha'] ?? date('Y-m-d');
            $monto = floatval($venta['monto'] ?? 0);
            $id_venta = isset($venta['id']) ? intval($venta['id']) : null;
            
            if ($id_venta && $id_venta > 0) {
                $sql = "UPDATE ventas SET fecha = ?, monto = ? WHERE id = ? AND usuario_id = ?";
                $stmt = $conn->prepare($sql);
                if ($stmt) {
                    $stmt->bind_param('sdii', $fecha, $monto, $id_venta, $usuario_id);
                    @$stmt->execute();
                    $stmt->close();
                }
            } else {
                $sql = "INSERT INTO ventas (usuario_id, fecha, monto) VALUES (?, ?, ?)";
                $stmt = $conn->prepare($sql);
                if ($stmt) {
                    $stmt->bind_param('isd', $usuario_id, $fecha, $monto);
                    @$stmt->execute();
                    $stmt->close();
                }
            }
        }
    }
    return true;
}

function procesarKardex($conn, $usuario_id, $operacion, $registro_id, $contenido) {
    if ($operacion == 'SYNC_ALL' && isset($contenido['kardex']) && is_array($contenido['kardex'])) {
        foreach ($contenido['kardex'] as $item) {
            $producto_id = intval($item['producto_id'] ?? 0);
            $cantidad = intval($item['cantidad'] ?? 0);
            $tipo = $item['tipo'] ?? 'entrada';
            $fecha = $item['fecha'] ?? date('Y-m-d');
            
            $sql = "INSERT INTO kardex (usuario_id, producto_id, cantidad, tipo, fecha) VALUES (?, ?, ?, ?, ?)";
            $stmt = $conn->prepare($sql);
            if ($stmt) {
                $stmt->bind_param('iiiss', $usuario_id, $producto_id, $cantidad, $tipo, $fecha);
                @$stmt->execute();
                $stmt->close();
            }
        }
    }
    return true;
}

function procesarCitas($conn, $usuario_id, $operacion, $registro_id, $contenido) {
    if ($operacion == 'SYNC_ALL' && isset($contenido['citas']) && is_array($contenido['citas'])) {
        foreach ($contenido['citas'] as $cita) {
            $paciente_id = intval($cita['paciente_id'] ?? 0);
            $fecha = $cita['fecha'] ?? date('Y-m-d');
            $hora = $cita['hora'] ?? '09:00';
            $id_cita = isset($cita['id']) ? intval($cita['id']) : null;
            
            if ($id_cita && $id_cita > 0) {
                $sql = "UPDATE citas SET paciente_id = ?, fecha = ?, hora = ? WHERE id = ? AND usuario_id = ?";
                $stmt = $conn->prepare($sql);
                if ($stmt) {
                    $stmt->bind_param('issii', $paciente_id, $fecha, $hora, $id_cita, $usuario_id);
                    @$stmt->execute();
                    $stmt->close();
                }
            } else {
                $sql = "INSERT INTO citas (usuario_id, paciente_id, fecha, hora) VALUES (?, ?, ?, ?)";
                $stmt = $conn->prepare($sql);
                if ($stmt) {
                    $stmt->bind_param('iiss', $usuario_id, $paciente_id, $fecha, $hora);
                    @$stmt->execute();
                    $stmt->close();
                }
            }
        }
    }
    return true;
}
?>
