<?php
/**
 * download_manual_backup_zip.php
 *
 * Descarga respaldo de un usuario madre.
 * - Incluye carpeta solicitada (codigo_dispositivo)
 * - Opcionalmente incluye sucursales hijas registradas en BD
 * - Soporta formato zip y rar
 *
 * Parametros:
 * - usuario_madre (required)
 * - codigo_dispositivo (required)
 * - include_children=1|0 (optional, default 1)
 * - format=zip|rar (optional, default zip)
 * - password (optional fallback)
 */

require_once __DIR__ . DIRECTORY_SEPARATOR . '_cloud_common.php';

function rrmdir_safe($dir) {
    if (!is_dir($dir)) {
        return;
    }
    $items = @scandir($dir);
    if (!is_array($items)) {
        return;
    }
    foreach ($items as $item) {
        if ($item === '.' || $item === '..') {
            continue;
        }
        $path = $dir . DIRECTORY_SEPARATOR . $item;
        if (is_dir($path)) {
            rrmdir_safe($path);
        } else {
            @unlink($path);
        }
    }
    @rmdir($dir);
}

function add_dir_to_zip($zip, $source_dir, $base_len) {
    $it = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator($source_dir, FilesystemIterator::SKIP_DOTS),
        RecursiveIteratorIterator::LEAVES_ONLY
    );
    foreach ($it as $fileinfo) {
        if (!$fileinfo->isFile()) {
            continue;
        }
        $abs = $fileinfo->getRealPath();
        if ($abs === false) {
            continue;
        }
        $local = ltrim(substr($abs, $base_len), '/\\');
        if ($local === '') {
            continue;
        }
        @$zip->addFile($abs, $local);
    }
}

function create_rar_archive($staging_dir, $rar_path, &$error_msg) {
    $error_msg = '';
    if (!function_exists('exec')) {
        $error_msg = 'Funcion exec() deshabilitada en servidor';
        return false;
    }

    $binaries = array('rar', '/usr/bin/rar', '/usr/local/bin/rar', 'winrar');
    $bin_found = '';
    foreach ($binaries as $bin) {
        if (strpos($bin, DIRECTORY_SEPARATOR) !== false) {
            if (@is_file($bin) && @is_executable($bin)) {
                $bin_found = $bin;
                break;
            }
            continue;
        }
        $probe = array();
        $probe_code = 1;
        @exec('command -v ' . escapeshellarg($bin) . ' 2>/dev/null', $probe, $probe_code);
        if ($probe_code === 0 && !empty($probe)) {
            $bin_found = trim((string)$probe[0]);
            break;
        }
    }

    if ($bin_found === '') {
        $error_msg = 'No se encontro binario RAR en el servidor';
        return false;
    }

    $cmd = 'cd ' . escapeshellarg($staging_dir)
         . ' && ' . escapeshellcmd($bin_found)
         . ' a -idq -inul '
         . escapeshellarg($rar_path)
         . ' . 2>&1';

    $out = array();
    $code = 1;
    @exec($cmd, $out, $code);

    if ($code !== 0 || !is_file($rar_path) || filesize($rar_path) === 0) {
        $tail = '';
        if (!empty($out)) {
            $tail = trim(implode("\n", array_slice($out, -4)));
        }
        $error_msg = 'Fallo al crear RAR' . ($tail ? ': ' . $tail : '');
        return false;
    }

    return true;
}

$input = read_json_input();
$usuario_madre_raw = trim((string)($input['usuario_madre'] ?? $input['username'] ?? ''));
$codigo_dispositivo = normalize_codigo_dispositivo($input['codigo_dispositivo'] ?? '');
$download_password = (string)($input['password'] ?? '');

if ($usuario_madre_raw === '' || $codigo_dispositivo === 'UNKNOWN_DEVICE') {
    respond_json(array(
        'success' => false,
        'error' => 'Missing usuario_madre or codigo_dispositivo'
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
$format = strtolower(trim((string)($input['format'] ?? 'zip')));
if ($format !== 'rar' && $format !== 'zip') {
    $format = 'zip';
}

$include_children_raw = strtolower(trim((string)($input['include_children'] ?? '1')));
$include_children = !in_array($include_children_raw, array('0', 'false', 'no', 'off'), true);

$requested_codes = array($codigo_dispositivo);
if ($include_children) {
    $child_codes = list_registered_child_device_codes($usuario_madre);
    if (is_array($child_codes)) {
        foreach ($child_codes as $child_code) {
            $cc = normalize_codigo_dispositivo($child_code);
            if ($cc !== '' && $cc !== 'UNKNOWN_DEVICE') {
                $requested_codes[] = $cc;
            }
        }
    }
}
$requested_codes = array_values(array_unique($requested_codes));

$folders_map = array();
$missing_codes = array();
foreach ($requested_codes as $code) {
    $folder = get_device_folder($usuario_madre, $code);
    if (is_dir($folder)) {
        $folders_map[$code] = $folder;
    } else {
        $missing_codes[] = $code;
    }
}

if (empty($folders_map)) {
    respond_json(array(
        'success' => false,
        'error' => 'No snapshot folders found for requested device(s)',
        'requested_codes' => $requested_codes
    ), 404);
}

$tmpBase = @tempnam(sys_get_temp_dir(), 'viso_backup_');
if ($tmpBase === false) {
    respond_json(array(
        'success' => false,
        'error' => 'Could not create temporary file'
    ), 500);
}
@unlink($tmpBase);

$staging_dir = $tmpBase . '_dir';
if (!@mkdir($staging_dir, 0755, true) && !is_dir($staging_dir)) {
    respond_json(array(
        'success' => false,
        'error' => 'Could not create temporary directory'
    ), 500);
}

$files_added = 0;
$per_code_files = array();
foreach ($folders_map as $code => $folder) {
    $target_subdir = $staging_dir . DIRECTORY_SEPARATOR . $code;
    @mkdir($target_subdir, 0755, true);
    $copied = 0;

    $files = glob($folder . DIRECTORY_SEPARATOR . '*.json');
    if (!is_array($files)) {
        $files = array();
    }
    foreach ($files as $src) {
        if (!is_file($src)) {
            continue;
        }
        $name = basename($src);
        if ($name === '') {
            continue;
        }
        $dst = $target_subdir . DIRECTORY_SEPARATOR . $name;
        if (@copy($src, $dst)) {
            $files_added++;
            $copied++;
        }
    }
    $per_code_files[$code] = $copied;
}

$manifest = array(
    'generated_at' => date('c'),
    'usuario_madre' => $usuario_madre,
    'requested_code' => $codigo_dispositivo,
    'include_children' => $include_children,
    'format' => $format,
    'device_codes_requested' => $requested_codes,
    'device_codes_included' => array_keys($folders_map),
    'device_codes_missing' => $missing_codes,
    'files_per_device' => $per_code_files,
    'files_added_total' => $files_added
);
@file_put_contents(
    $staging_dir . DIRECTORY_SEPARATOR . '_manifest.json',
    json_encode($manifest, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT)
);

$archive_path = $tmpBase . ($format === 'rar' ? '.rar' : '.zip');
$archive_ok = false;
$archive_error = '';

if ($format === 'zip') {
    if (!class_exists('ZipArchive')) {
        rrmdir_safe($staging_dir);
        respond_json(array(
            'success' => false,
            'error' => 'ZipArchive extension not available on server'
        ), 500);
    }
    $zip = new ZipArchive();
    $open_result = $zip->open($archive_path, ZipArchive::CREATE | ZipArchive::OVERWRITE);
    if ($open_result !== true) {
        rrmdir_safe($staging_dir);
        respond_json(array(
            'success' => false,
            'error' => 'Could not create ZIP file'
        ), 500);
    }
    add_dir_to_zip($zip, $staging_dir, strlen($staging_dir) + 1);
    $zip->close();
    $archive_ok = is_file($archive_path) && filesize($archive_path) > 0;
    if (!$archive_ok) {
        $archive_error = 'ZIP file was not generated';
    }
} else {
    $archive_ok = create_rar_archive($staging_dir, $archive_path, $archive_error);
    if (!$archive_ok) {
        rrmdir_safe($staging_dir);
        respond_json(array(
            'success' => false,
            'error' => 'RAR no disponible en servidor',
            'detail' => $archive_error
        ), 501);
    }
}

if (!$archive_ok) {
    rrmdir_safe($staging_dir);
    respond_json(array(
        'success' => false,
        'error' => $archive_error ?: 'Archive was not generated'
    ), 500);
}

$download_name = 'VISO-backup-' . $usuario_madre . '-' . date('Ymd-His') . ($format === 'rar' ? '.rar' : '.zip');
$size = @filesize($archive_path);
if ($size === false) {
    $size = 0;
}

register_shutdown_function(function () use ($archive_path, $staging_dir) {
    @unlink($archive_path);
    rrmdir_safe($staging_dir);
});

if ($format === 'rar') {
    header('Content-Type: application/vnd.rar');
} else {
    header('Content-Type: application/zip');
}
header('Content-Disposition: attachment; filename="' . $download_name . '"');
header('Content-Length: ' . intval($size));
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');
header('Expires: 0');

@readfile($archive_path);
exit;
