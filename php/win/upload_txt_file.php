<?php
header("Content-Type: application/json; charset=utf-8");

$input = json_decode(file_get_contents("php://input"), true);
$usuario = $input["usuario"] ?? "";
$filename = $input["filename"] ?? "configuracion_optica.txt";
$content = $input["content"] ?? "";

if (!$usuario || !$content) {
    echo json_encode(["status" => "error", "message" => "Datos incompletos"]);
    exit;
}

// Ruta: _cloud_store/viso-usuario/data/archivo.txt
$user_dir = "../../_cloud_store/viso-" . preg_replace("/[^A-Za-z0-9]/", "", $usuario) . "/data";
if (!is_dir($user_dir)) {
    mkdir($user_dir, 0777, true);
}

$file_path = $user_dir . "/" . $filename;
if (file_put_contents($file_path, $content)) {
    echo json_encode(["status" => "success", "message" => "Archivo TXT guardado correctamente"]);
} else {
    echo json_encode(["status" => "error", "message" => "No se pudo escribir el archivo"]);
}