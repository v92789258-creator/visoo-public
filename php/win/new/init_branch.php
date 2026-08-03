<?php
header("Content-Type: application/json; charset=utf-8");

$input = json_decode(file_get_contents("php://input"), true);
$usuario_madre = preg_replace("/[^A-Za-z0-9]/", "", $input["usuario_madre"] ?? "");
$codigo_sucursal = preg_replace("/[^A-Za-z0-9\-]/", "", $input["codigo_sucursal"] ?? "");

if (!$usuario_madre || !$codigo_sucursal) {
    echo json_encode(["status" => "error", "message" => "Faltan identificadores"]);
    exit;
}

// Ruta: _cloud_store/viso-usuario+codigo/
$branch_dir = "../../../_cloud_store/viso-" . $usuario_madre . "+" . $codigo_sucursal;

if (!is_dir($branch_dir)) {
    if (mkdir($branch_dir, 0777, true)) {
        // Crear archivos base vacios para evitar errores 404
        $files = ["productos.json", "clientes.json", "ventas.json", "pagos.json", "graduaciones.json"];
        foreach ($files as $f) {
            file_put_contents($branch_dir . "/" . $f, "[]");
        }
        echo json_encode(["status" => "success", "message" => "Estructura de sucursal creada en la nube"]);
    } else {
        echo json_encode(["status" => "error", "message" => "No se pudo crear el directorio"]);
    }
} else {
    echo json_encode(["status" => "success", "message" => "La sucursal ya existia"]);
}
?>
