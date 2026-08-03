<?php
/**
 * verify_manual_backup_auth.php
 *
 * Gestiona autenticacion temporal para descargas de respaldo.
 *
 * Params:
 * - action: verify|status|logout (default verify)
 * - usuario_madre (required for all)
 * - password (required for verify)
 */

require_once __DIR__ . DIRECTORY_SEPARATOR . '_cloud_common.php';

if (!cloud_auth_session_start()) {
    respond_json(array(
        'success' => false,
        'error' => 'No se pudo iniciar sesion'
    ), 500);
}

$input = read_json_input();
$action = strtolower(trim((string)($input['action'] ?? 'verify')));
$usuario_ref = trim((string)($input['usuario_madre'] ?? $input['username'] ?? ''));
$password = (string)($input['password'] ?? '');

if ($usuario_ref === '') {
    respond_json(array(
        'success' => false,
        'error' => 'Missing usuario_madre'
    ), 400);
}

$ttl = 900; // 15 minutos
$remaining = 0;

if ($action === 'status') {
    $active = is_download_auth_active($usuario_ref, $remaining);
    respond_json(array(
        'success' => true,
        'active' => $active,
        'expires_in' => intval($remaining),
        'ttl' => $ttl
    ), 200);
}

if ($action === 'logout') {
    clear_download_auth_active($usuario_ref);
    respond_json(array(
        'success' => true,
        'active' => false,
        'expires_in' => 0,
        'ttl' => $ttl
    ), 200);
}

if ($action !== 'verify') {
    respond_json(array(
        'success' => false,
        'error' => 'Accion no soportada. Use verify|status|logout'
    ), 400);
}

$reason = '';
if (!verify_usuario_password($usuario_ref, $password, $reason)) {
    clear_download_auth_active($usuario_ref);
    respond_json(array(
        'success' => false,
        'error' => $reason !== '' ? $reason : 'Contrasena invalida'
    ), 401);
}

set_download_auth_active($usuario_ref, $ttl);
is_download_auth_active($usuario_ref, $remaining);

respond_json(array(
    'success' => true,
    'active' => true,
    'expires_in' => intval($remaining),
    'ttl' => $ttl,
    'message' => 'Sesion de descarga activa por 15 minutos'
), 200);

