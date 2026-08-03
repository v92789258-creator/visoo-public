<?php
/**
 * download_device_snapshot.php
 *
 * Downloads one dataset or all datasets for one child device folder.
 *
 * Query/body params:
 * - usuario_madre (required)
 * - codigo_dispositivo (required)
 * - dataset (optional)
 * - include_data=1 (optional, default 1 for single dataset, 0 for all)
 */

require_once __DIR__ . DIRECTORY_SEPARATOR . '_cloud_common.php';

$input = read_json_input();

$usuario_madre = trim((string)($input['usuario_madre'] ?? $input['username'] ?? ''));
$codigo_dispositivo = normalize_codigo_dispositivo($input['codigo_dispositivo'] ?? '');
$dataset = safe_dataset_name($input['dataset'] ?? '');
$include_data_raw = (string)($input['include_data'] ?? '');

if ($usuario_madre === '' || $codigo_dispositivo === 'UNKNOWN_DEVICE') {
    respond_json(array(
        'success' => false,
        'error' => 'Missing usuario_madre or codigo_dispositivo'
    ), 400);
}

$device_folder = get_device_folder($usuario_madre, $codigo_dispositivo);
if (!is_dir($device_folder)) {
    respond_json(array(
        'success' => false,
        'error' => 'Device snapshot folder not found',
        'folder' => basename($device_folder)
    ), 404);
}

$include_data = ($include_data_raw === '1' || strtolower($include_data_raw) === 'true');
if ($dataset !== '' && $include_data_raw === '') {
    $include_data = true;
}

$meta = get_device_meta($device_folder);
$files = glob($device_folder . DIRECTORY_SEPARATOR . '*.json');
if (!is_array($files)) {
    $files = array();
}

$datasets = array();
$data_payload = array();

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
    if ($dataset !== '' && $dataset !== $safe) {
        continue;
    }

    $summary = build_dataset_summary($path);
    $datasets[] = $summary;

    if ($include_data) {
        $data_payload[$safe] = read_json_file($path, array());
    }
}

if ($dataset !== '' && empty($datasets)) {
    respond_json(array(
        'success' => false,
        'error' => 'Dataset not found',
        'dataset' => $dataset,
        'folder' => basename($device_folder)
    ), 404);
}

$resp = array(
    'success' => true,
    'usuario_madre' => normalize_usuario($usuario_madre),
    'codigo_dispositivo' => $codigo_dispositivo,
    'folder' => basename($device_folder),
    'meta' => $meta,
    'datasets' => $datasets,
    'total_datasets' => count($datasets)
);

if ($dataset !== '') {
    $resp['dataset'] = $dataset;
}

if ($include_data) {
    if ($dataset !== '') {
        $resp['data'] = $data_payload[$dataset] ?? array();
    } else {
        $resp['snapshot'] = $data_payload;
    }
}

respond_json($resp, 200);

?>
