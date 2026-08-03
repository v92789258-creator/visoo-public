<?php
/**
 * list_device_events.php
 *
 * Lista eventos emitidos por dispositivos hijos para un usuario madre.
 * Endpoint sugerido:
 *   https://api.yhana.cloud/win/new/list_device_events.php?usuario_madre=alex9121
 */

require_once __DIR__ . DIRECTORY_SEPARATOR . '_cloud_common.php';

$input = read_json_input();
$usuario_madre = trim((string)($input['usuario_madre'] ?? $input['username'] ?? ''));
if ($usuario_madre === '') {
    respond_json(array(
        'success' => false,
        'error' => 'Missing usuario_madre'
    ), 400);
}

$since_epoch = intval($input['since_epoch'] ?? 0);
if ($since_epoch < 0) {
    $since_epoch = 0;
}

$limit = intval($input['limit'] ?? 50);
if ($limit <= 0) {
    $limit = 50;
}
$limit = min($limit, 200);

$type_filter = strtolower(trim((string)($input['type'] ?? '')));

$events = read_device_events($usuario_madre);
$filtered = array();
foreach ($events as $event) {
    if (!is_array($event)) {
        continue;
    }

    $event_epoch = intval($event['epoch'] ?? 0);
    if ($event_epoch > 0 && $since_epoch > 0 && $event_epoch <= $since_epoch) {
        continue;
    }

    if ($type_filter !== '') {
        $event_type = strtolower(trim((string)($event['type'] ?? '')));
        if ($event_type !== $type_filter) {
            continue;
        }
    }

    $filtered[] = $event;
}

usort($filtered, function($a, $b) {
    $ea = intval($a['epoch'] ?? 0);
    $eb = intval($b['epoch'] ?? 0);
    if ($ea === $eb) {
        return 0;
    }
    return ($ea < $eb) ? 1 : -1;
});

if (count($filtered) > $limit) {
    $filtered = array_slice($filtered, 0, $limit);
}

respond_json(array(
    'success' => true,
    'usuario_madre' => normalize_usuario($usuario_madre),
    'count' => count($filtered),
    'events' => $filtered
), 200);

