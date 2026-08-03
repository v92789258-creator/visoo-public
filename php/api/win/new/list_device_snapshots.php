<?php
/**
 * list_device_snapshots.php
 *
 * Lists snapshot folders for one main user.
 *
 * Params:
 * - usuario_madre (required)
 * - include_meta=1 (optional)
 */

require_once __DIR__ . DIRECTORY_SEPARATOR . '_cloud_common.php';

$input = read_json_input();
$usuario_madre = trim((string)($input['usuario_madre'] ?? $input['username'] ?? ''));
$include_meta_raw = (string)($input['include_meta'] ?? '');
$include_meta = ($include_meta_raw === '1' || strtolower($include_meta_raw) === 'true');

if ($usuario_madre === '') {
    respond_json(array(
        'success' => false,
        'error' => 'Missing usuario_madre'
    ), 400);
}

$folders = list_device_folders($usuario_madre);
$items = array();

foreach ($folders as $folder) {
    $meta = get_device_meta($folder);
    $files = glob($folder . DIRECTORY_SEPARATOR . '*.json');
    if (!is_array($files)) {
        $files = array();
    }

    $datasets = array();
    foreach ($files as $path) {
        $base = basename($path);
        if ($base === 'meta.json') {
            continue;
        }
        if (substr($base, -5) !== '.json') {
            continue;
        }
        $name = substr($base, 0, -5);
        $safe = safe_dataset_name($name);
        if ($safe === '') {
            continue;
        }
        $datasets[] = build_dataset_summary($path);
    }

    $items[] = array(
        'folder' => basename($folder),
        'usuario_madre' => extract_usuario_from_folder($folder),
        'codigo_dispositivo' => extract_codigo_from_folder($folder),
        'dataset_count' => count($datasets),
        'datasets' => $datasets,
        'meta' => $include_meta ? $meta : null
    );
}

usort($items, function ($a, $b) {
    $a_ts = 0;
    $b_ts = 0;

    if (is_array($a['meta']) && isset($a['meta']['updated_epoch'])) {
        $a_ts = intval($a['meta']['updated_epoch']);
    }
    if (is_array($b['meta']) && isset($b['meta']['updated_epoch'])) {
        $b_ts = intval($b['meta']['updated_epoch']);
    }

    if ($a_ts === $b_ts) {
        return strcmp((string)$a['codigo_dispositivo'], (string)$b['codigo_dispositivo']);
    }
    return ($a_ts > $b_ts) ? -1 : 1;
});

respond_json(array(
    'success' => true,
    'usuario_madre' => normalize_usuario($usuario_madre),
    'total' => count($items),
    'devices' => $items
), 200);

?>
