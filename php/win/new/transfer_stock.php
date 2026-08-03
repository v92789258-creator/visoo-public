<?php
header("Content-Type: application/json; charset=utf-8");

$input = json_decode(file_get_contents("php://input"), true);
$usuario_madre = preg_replace("/[^A-Za-z0-9]/", "", $input["usuario_madre"] ?? "");
$codigo_destino = preg_replace("/[^A-Za-z0-9\-]/", "", $input["codigo_destino"] ?? "");
$producto_data = $input["producto"] ?? null;
$cantidad = intval($input["cantidad"] ?? 0);        

if (!$usuario_madre || !$codigo_destino || !$producto_data || $cantidad <= 0) {
    echo json_encode(["status" => "error", "message" => "Datos incompletos para la transferencia"]);
    exit;
}


// Ruta del inventario de la sucursal destino
$target_path = "../../../_cloud_store/viso-" . $usuario_madre . "+" . $codigo_destino . "/productos.json";

if (!file_exists($target_path)) {
    // Si no existe el archivo, lo inicializamos vacio
    $inventario_destino = [];
    $dir = dirname($target_path);
    if (!is_dir($dir)) mkdir($dir, 0777, true);
} else {
    $inventario_destino = json_decode(file_get_contents($target_path), true) ?: [];
}

$encontrado = false;
$codigo_prod = $producto_data['codigo'] ?? '';

foreach ($inventario_destino as &$p) {
    if ($p['codigo'] === $codigo_prod) {
        $p['stock'] = intval($p['stock']) + $cantidad;
        $encontrado = true;
        break;
    }
}

if (!$encontrado) {
    // Si el producto no existe en la otra sucursal, lo agregamos completo
    $nuevo_p = $producto_data;
    $nuevo_p['stock'] = $cantidad; // Solo la cantidad transferida
    $inventario_destino[] = $nuevo_p;
}

if (file_put_contents($target_path, json_encode($inventario_destino, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT))) {
    echo json_encode(["status" => "success", "message" => "Stock transferido correctamente a la sucursal destino"]);
} else {
    echo json_encode(["status" => "error", "message" => "No se pudo actualizar el inventario destino"]);
}
?>
