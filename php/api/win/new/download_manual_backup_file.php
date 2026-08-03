<?php
/**
 * download_manual_backup_file.php
 *
 * Descarga un dataset JSON individual como archivo.
 *
 * Parametros:
 * - usuario_madre (required)
 * - codigo_dispositivo (required)
 * - dataset (required)
 * - password (optional fallback)
 */

require_once __DIR__ . DIRECTORY_SEPARATOR . '_cloud_common.php';

$input = read_json_input();
$usuario_madre_raw = trim((string)($input['usuario_madre'] ?? $input['username'] ?? ''));
$codigo_dispositivo = normalize_codigo_dispositivo($input['codigo_dispositivo'] ?? '');
$dataset = safe_dataset_name($input['dataset'] ?? '');
$download_password = (string)($input['password'] ?? '');

if ($usuario_madre_raw === '' || $codigo_dispositivo === 'UNKNOWN_DEVICE' || $dataset === '') {
    respond_json(array(
        'success' => false,
        'error' => 'Missing usuario_madre, codigo_dispositivo or dataset'
    ), 400);
}

$remaining_auth = 0;
$auth_active = is_download_auth_active($usuario_madre_raw, $remaining_auth);
if (!$auth_active) {
    $auth_reason = '';
    if ($download_password !== '' && verify_usuario_password($usuario_madre_raw, $download_password, $auth_reason)) {
        set_download_auth_active($usuario_madre_raw, 900);
    } else {
        respond_json(array(
            'success' => false,
            'error' => 'Sesion de descarga expirada. Verifica la contrasena con OK.',
            'detail' => $auth_reason !== '' ? $auth_reason : ''
        ), 401);
    }
}

$usuario_madre = normalize_usuario($usuario_madre_raw);
$device_folder = get_device_folder($usuario_madre, $codigo_dispositivo);
if (!is_dir($device_folder)) {
    respond_json(array(
        'success' => false,
        'error' => 'Device snapshot folder not found'
    ), 404);
}

$file_path = dataset_file_path($device_folder, $dataset);
if ($file_path === '' || !is_file($file_path)) {
    respond_json(array(
        'success' => false,
        'error' => 'Dataset file not found',
        'dataset' => $dataset
    ), 404);
}

$size = @filesize($file_path);
if ($size === false) {
    $size = 0;
}

$download_name = $dataset . '-' . $codigo_dispositivo . '.json';

header('Content-Type: application/json; charset=utf-8');
header('Content-Disposition: attachment; filename="' . $download_name . '"');
header('Content-Length: ' . intval($size));
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');
header('Expires: 0');

@readfile($file_path);
exit;
