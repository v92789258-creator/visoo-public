<?php
/**
 * manual_backup_portal.php
 *
 * Vista de respaldo manual por dispositivo.
 * Parametros:
 * - usuario_madre (required)
 * - codigo_dispositivo (required)
 */

require_once __DIR__ . DIRECTORY_SEPARATOR . '_cloud_common.php';
header('Content-Type: text/html; charset=utf-8');

function h($value) {
    return htmlspecialchars((string)$value, ENT_QUOTES, 'UTF-8');
}

$input = read_json_input();
$usuario_madre = trim((string)($input['usuario_madre'] ?? $input['username'] ?? ''));
$codigo_dispositivo = normalize_codigo_dispositivo($input['codigo_dispositivo'] ?? '');

$is_valid = ($usuario_madre !== '' && $codigo_dispositivo !== 'UNKNOWN_DEVICE');
$user_row = $is_valid ? find_usuario_auth_row($usuario_madre) : null;
$tiene_respaldo = (is_array($user_row) && isset($user_row['respaldo']) && (int)$user_row['respaldo'] === 1);

$device_folder = $is_valid ? get_device_folder($usuario_madre, $codigo_dispositivo) : '';
$device_exists = ($device_folder !== '' && is_dir($device_folder));
$meta = $device_exists ? get_device_meta($device_folder) : array();

$datasets = array();
if ($device_exists) {
    $files = glob($device_folder . DIRECTORY_SEPARATOR . '*.json');
    if (!is_array($files)) {
        $files = array();
    }

    foreach ($files as $path) {
        $base = basename($path);
        if ($base === 'meta.json' || substr($base, -5) !== '.json') {
            continue;
        }
        $dataset = safe_dataset_name(substr($base, 0, -5));
        if ($dataset === '') {
            continue;
        }
        $datasets[] = build_dataset_summary($path);
    }
}

usort($datasets, function ($a, $b) {
    return strcmp((string)($a['dataset'] ?? ''), (string)($b['dataset'] ?? ''));
});

$dataset_count = count($datasets);
$total_rows = 0;
$total_bytes = 0;
foreach ($datasets as $ds) {
    $rows = isset($ds['rows']) ? intval($ds['rows']) : 0;
    $size = isset($ds['size_bytes']) ? intval($ds['size_bytes']) : 0;
    if ($rows > 0) {
        $total_rows += $rows;
    }
    if ($size > 0) {
        $total_bytes += $size;
    }
}

$download_pack_endpoint = 'download_manual_backup_zip.php';
$download_file_endpoint = 'download_manual_backup_file.php';
$verify_auth_endpoint = 'verify_manual_backup_auth.php';
?>
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>VISO Cloud Backup</title>
    <style>
        :root {
            --ink: #0d1b2a;
            --ink-soft: #42556d;
            --line: #d9e1ec;
            --paper: #ffffff;
            --bg-a: #f8fbff;
            --bg-b: #eef2f8;
            --brand-a: #0b5bd3;
            --brand-b: #12a3d8;
            --ok-bg: #ecf9f1;
            --ok-border: #c4e9d2;
            --ok-text: #1f6a3a;
            --warn-bg: #fff4ec;
            --warn-border: #ffd6bf;
            --warn-text: #7a3c12;
        }
        * {
            box-sizing: border-box;
        }
        body {
            margin: 0;
            color: var(--ink);
            font-family: "Lexend", "Trebuchet MS", "Segoe UI", sans-serif;
            background:
                radial-gradient(900px 320px at 10% -10%, #d9ecff 0%, transparent 65%),
                radial-gradient(700px 280px at 95% -15%, #d7f6ff 0%, transparent 60%),
                linear-gradient(180deg, var(--bg-a) 0%, var(--bg-b) 100%);
            min-height: 100vh;
            overflow-x: hidden;
        }
        .shell {
            max-width: 1120px;
            margin: 28px auto;
            padding: 0 18px 28px;
        }
        .hero {
            position: relative;
            overflow: hidden;
            border-radius: 20px;
            background: linear-gradient(135deg, #0d2a4d 0%, #10407a 40%, #1770af 100%);
            color: #fff;
            border: 1px solid rgba(255, 255, 255, 0.15);
            box-shadow: 0 16px 40px rgba(12, 38, 74, 0.3);
            padding: 28px 26px;
        }
        .hero::after {
            content: "";
            position: absolute;
            width: 500px;
            height: 500px;
            right: -150px;
            top: -200px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0) 70%);
            filter: blur(4px);
        }
        .hero-kicker {
            position: relative;
            z-index: 1;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            letter-spacing: 0.12em;
            font-weight: 700;
            text-transform: uppercase;
            color: #9cd1ff;
        }
        .hero h1 {
            position: relative;
            z-index: 1;
            margin: 10px 0 8px;
            font-size: clamp(28px, 4vw, 42px);
            line-height: 1.1;
            letter-spacing: -0.02em;
        }
        .hero p {
            position: relative;
            z-index: 1;
            margin: 0;
            max-width: 760px;
            font-size: 15px;
            color: rgba(236, 244, 255, 0.9);
            line-height: 1.5;
        }
        .layout {
            display: grid;
            grid-template-columns: 320px 1fr;
            gap: 20px;
            margin-top: 20px;
        }
        .panel {
            background: var(--paper);
            border: 1px solid rgba(217, 225, 236, 0.7);
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(18, 40, 67, 0.05), 0 2px 6px rgba(18, 40, 67, 0.03);
            position: relative;
            overflow: hidden;
        }
        .panel::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 4px;
            background: linear-gradient(90deg, var(--brand-a), var(--brand-b));
            opacity: 0.85;
        }
        .panel-pad {
            padding: 20px;
        }
        .section-title {
            margin: 0 0 16px;
            font-size: 17px;
            font-weight: 700;
            color: #0b1c30;
        }
        .meta-list {
            display: grid;
            gap: 12px;
        }
        .meta-item {
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 12px 16px;
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            box-shadow: 0 2px 4px rgba(15, 23, 42, 0.02);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .meta-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(15, 23, 42, 0.05);
        }
        .meta-k {
            display: block;
            color: var(--ink-soft);
            font-size: 12px;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.02em;
            font-weight: 600;
        }
        .meta-v {
            display: block;
            font-size: 14px;
            font-weight: 700;
            word-break: break-word;
            color: #0f223a;
        }
        .stats {
            display: grid;
            gap: 12px;
            margin-top: 16px;
        }
        .stat {
            border: none;
            border-radius: 14px;
            background: linear-gradient(135deg, #f0f7ff 0%, #e0f0ff 100%);
            padding: 14px 16px;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6), 0 2px 5px rgba(20, 45, 80, 0.04);
            position: relative;
            overflow: hidden;
        }
        .stat::after {
            content: '';
            position: absolute;
            right: -20px;
            bottom: -20px;
            width: 60px;
            height: 60px;
            background: rgba(47, 123, 224, 0.08);
            border-radius: 50%;
        }
        .stat strong {
            font-size: 20px;
            color: #0b459c;
            display: block;
            margin-top: 6px;
            font-weight: 800;
        }
        .status {
            margin-top: 12px;
            border-radius: 12px;
            padding: 10px 12px;
            border: 1px solid transparent;
            font-size: 14px;
            line-height: 1.35;
        }
        .status.ok {
            background: var(--ok-bg);
            border-color: var(--ok-border);
            color: var(--ok-text);
        }
        .status.warn {
            background: var(--warn-bg);
            border-color: var(--warn-border);
            color: var(--warn-text);
        }
        .actions {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px;
            flex-wrap: wrap;
        }
        .auth-box {
            margin-top: 12px;
            padding: 12px;
            border: 1px solid #cfe0f6;
            border-radius: 12px;
            background: #f6faff;
            max-width: 520px;
        }
        .auth-box label {
            display: block;
            font-size: 12px;
            color: #33506f;
            margin-bottom: 6px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .04em;
        }
        .auth-box input {
            width: 100%;
            border: 1px solid #a9c2e3;
            border-radius: 10px;
            padding: 10px 12px;
            font-size: 14px;
            font-family: "Lexend", "Trebuchet MS", "Segoe UI", sans-serif;
            background: #fff;
            color: #13273f;
            outline: none;
        }
        .auth-box input:focus {
            border-color: #2f7be0;
            box-shadow: 0 0 0 3px rgba(47, 123, 224, .18);
        }
        .auth-row {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        .auth-row input {
            flex: 1;
        }
        .auth-ok-btn {
            border: none;
            border-radius: 10px;
            background: #1f6fd8;
            color: #fff;
            font-weight: 700;
            font-size: 13px;
            padding: 10px 14px;
            cursor: pointer;
            white-space: nowrap;
        }
        .auth-ok-btn:hover {
            filter: brightness(1.05);
        }
        .auth-ok-btn:disabled {
            opacity: .6;
            cursor: wait;
        }
        .auth-state {
            margin-top: 8px;
            font-size: 12px;
            color: #1c4f96;
            font-weight: 600;
            min-height: 16px;
        }
        .auth-alert {
            display: none;
            margin-top: 8px;
            color: #8a2a06;
            background: #fff2eb;
            border: 1px solid #ffceb8;
            border-radius: 8px;
            padding: 8px 10px;
            font-size: 12px;
        }
        .auth-alert.show {
            display: block;
        }
        .hint {
            color: var(--ink-soft);
            font-size: 13px;
            margin-top: 8px;
        }
        .btn {
            appearance: none;
            border: none;
            border-radius: 12px;
            padding: 12px 16px;
            font-weight: 700;
            font-size: 14px;
            cursor: pointer;
            color: #fff;
            background: linear-gradient(120deg, var(--brand-a), var(--brand-b));
            box-shadow: 0 8px 20px rgba(16, 95, 182, 0.34);
            transition: transform .12s ease, filter .12s ease;
        }
        .btn:hover {
            transform: translateY(-1px);
            filter: brightness(1.05);
        }
        .table-wrap {
            margin-top: 14px;
            border: 1px solid var(--line);
            border-radius: 12px;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            background: #fff;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            min-width: 640px;
        }
        th, td {
            padding: 11px 12px;
            border-bottom: 1px solid var(--line);
            text-align: left;
            font-size: 13px;
        }
        th {
            background: #f4f8fe;
            color: #1b3f6d;
            text-transform: uppercase;
            letter-spacing: .02em;
            font-size: 11px;
        }
        tr:last-child td {
            border-bottom: none;
        }
        .mono {
            font-family: "Consolas", "Courier New", monospace;
            letter-spacing: 0.01em;
        }
        .empty {
            margin-top: 12px;
            padding: 16px;
            border-radius: 12px;
            border: 1px dashed #c7d4e8;
            color: var(--ink-soft);
            background: #f8fbff;
        }
        .modal {
            position: fixed;
            inset: 0;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 16px;
            background: rgba(7, 14, 25, 0.55);
            z-index: 1200;
        }
        .modal.open {
            display: flex;
        }
        .modal-card {
            width: min(560px, 100%);
            border-radius: 16px;
            border: 1px solid #c8d7eb;
            background: #fff;
            box-shadow: 0 16px 40px rgba(10, 24, 44, 0.34);
            padding: 16px;
        }
        .modal-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
            margin-bottom: 10px;
        }
        .modal-title {
            margin: 0;
            font-size: 20px;
            line-height: 1.1;
        }
        .close-btn {
            border: 1px solid #c8d7eb;
            border-radius: 10px;
            background: #fff;
            color: #21374f;
            font-weight: 700;
            cursor: pointer;
            padding: 7px 10px;
        }
        .dl-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 14px;
            margin-top: 16px;
        }
        .dl-card {
            border: 1px solid rgba(214, 225, 239, 0.8);
            border-radius: 16px;
            padding: 16px;
            background: linear-gradient(145deg, #ffffff 0%, #f4f8ff 100%);
            box-shadow: 0 4px 12px rgba(18, 40, 67, 0.03), 0 1px 2px rgba(18, 40, 67, 0.02);
            transition: all 0.2s ease;
        }
        .dl-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 16px rgba(18, 40, 67, 0.06);
            border-color: #a9c2e3;
        }
        .dl-card h3 {
            margin: 0 0 8px;
            font-size: 17px;
            color: #122c4f;
        }
        .dl-card p {
            margin: 0 0 14px;
            font-size: 13px;
            color: var(--ink-soft);
            min-height: 38px;
            line-height: 1.4;
        }
        .dl-link {
            display: inline-block;
            border-radius: 10px;
            padding: 10px 12px;
            text-decoration: none;
            font-size: 13px;
            font-weight: 700;
        }
        .dl-link.zip {
            color: #fff;
            background: linear-gradient(120deg, var(--brand-a), var(--brand-b));
        }
        .dl-link.rar {
            color: #163353;
            border: 1px solid #9cb4d2;
            background: #fff;
        }
        .row-download {
            display: inline-block;
            text-decoration: none;
            font-size: 12px;
            font-weight: 700;
            color: #0e4ea8;
            border: 1px solid #9fb8dc;
            background: #f6fbff;
            border-radius: 8px;
            padding: 7px 10px;
            white-space: nowrap;
        }
        .row-download:hover {
            filter: brightness(0.98);
        }
        .action-btn {
            appearance: none;
            border: none;
            border-radius: 10px;
            padding: 10px 12px;
            font-size: 13px;
            font-weight: 700;
            cursor: pointer;
            text-decoration: none;
        }
        .action-btn.pack-zip {
            color: #fff;
            background: linear-gradient(120deg, var(--brand-a), var(--brand-b));
        }
        .action-btn.pack-rar {
            color: #163353;
            border: 1px solid #9cb4d2;
            background: #fff;
        }
        .note {
            margin-top: 10px;
            color: var(--ink-soft);
            font-size: 12px;
        }
        @media (max-width: 960px) {
            .layout {
                grid-template-columns: 1fr;
            }
        }
        @media (max-width: 640px) {
            .shell {
                margin: 12px auto;
                padding: 0 12px 24px;
            }
            .hero {
                padding: 18px 16px;
            }
            .hero h1 {
                font-size: 26px;
            }
            .dl-grid {
                grid-template-columns: 1fr;
            }
            .actions {
                flex-direction: column;
                align-items: stretch;
            }
            .actions .btn {
                width: 100%;
                margin-top: 12px;
            }
            .auth-box {
                max-width: 100%;
            }
            .auth-row {
                flex-direction: column;
                align-items: stretch;
            }
            .auth-ok-btn {
                width: 100%;
            }
        }
    </style>
</head>
<body>
<div class="shell">
    <section class="hero">
        <div class="hero-kicker">VISO CLOUD BACKUP</div>
        <h1>Portal de respaldo</h1>
        <p>Descarga informacion del dispositivo actual y de sucursales hijas registradas desde un solo punto.</p>
    </section>

    <section class="layout">
        <aside class="panel panel-pad">
            <h2 class="section-title">Resumen</h2>

            <?php if (!$is_valid): ?>
                <div class="status warn">Faltan parametros requeridos: usuario_madre y codigo_dispositivo.</div>
            <?php else: ?>
                <div class="meta-list">
                    <div class="meta-item">
                        <span class="meta-k">Usuario madre</span>
                        <span class="meta-v mono"><?= h(normalize_usuario($usuario_madre)) ?></span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-k">Codigo dispositivo</span>
                        <span class="meta-v mono"><?= h($codigo_dispositivo) ?></span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-k">Ultima actualizacion</span>
                        <span class="meta-v"><?= h((string)($meta['updated_at'] ?? 'N/A')) ?></span>
                    </div>
                </div>

                <div class="stats">
                    <div class="stat"><span class="meta-k">Datasets</span><strong><?= intval($dataset_count) ?></strong></div>
                    <div class="stat"><span class="meta-k">Registros (estimado)</span><strong><?= intval($total_rows) ?></strong></div>
                    <div class="stat"><span class="meta-k">Peso total</span><strong><?= intval($total_bytes) ?> B</strong></div>
                </div>

                <?php if ($device_exists): ?>
                    <div class="status ok">Respaldo encontrado en nube para este dispositivo.</div>
                <?php else: ?>
                    <div class="status warn">No se encontro carpeta de respaldo para este dispositivo.</div>
                <?php endif; ?>
            <?php endif; ?>
        </aside>

        <main class="panel panel-pad">
            <?php if (!$is_valid): ?>
                <div class="empty" style="text-align: center; padding: 40px 20px;">
                    <h3 style="margin-top:0; color: var(--ink-soft);">Faltan Parámetros</h3>
                    <p style="margin-bottom:0;">No se puede mostrar el detalle porque faltan datos de entrada.</p>
                </div>
            <?php elseif (!$tiene_respaldo): ?>
                <div class="empty" style="text-align: center; padding: 40px 20px; border-color: #ffd6bf; background: #fff4ec;">
                    <h3 style="margin-top:0; color: #8a2a06;">Servicio no habilitado</h3>
                    <p style="margin-bottom:0; color: #7a3c12;">El servicio de respaldo no está habilitado para esta cuenta. Por favor, contacte con soporte técnico para solicitar la activación del servicio de respaldo en la nube.</p>
                </div>
            <?php else: ?>
                <div class="actions">
                    <div>
                        <h2 class="section-title" style="margin-bottom:4px;">Descarga de informacion</h2>
                        <div class="hint">Al descargar, se incluye la sucursal actual y sucursales hijas del usuario madre.</div>
                        <div class="auth-box">
                            <label for="downloadPassword">Contrasena del usuario</label>
                            <div class="auth-row">
                                <input id="downloadPassword" type="password" autocomplete="current-password" placeholder="Ingresa tu contrasena para autorizar descargas">
                                <button id="verifyPasswordBtn" class="auth-ok-btn" type="button">OK</button>
                            </div>
                            <div id="downloadAuthAlert" class="auth-alert">Debes ingresar tu contrasena para descargar.</div>
                            <div id="downloadAuthState" class="auth-state"></div>
                        </div>
                    </div>
                    <button class="btn" id="openDownloadModal" type="button" <?= (!$device_exists) ? 'disabled style="opacity:.55;cursor:not-allowed;box-shadow:none;"' : '' ?>>Descargar informacion</button>
                </div>

                <?php if ($device_exists): ?>
                    <?php if (!empty($datasets)): ?>
                        <div class="table-wrap">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Dataset</th>
                                        <th>Registros</th>
                                        <th>Bytes</th>
                                        <th>Actualizado</th>
                                        <th>Hash SHA256</th>
                                        <th>Archivo</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <?php foreach ($datasets as $ds): ?>
                                        <?php $dataset_name = (string)($ds['dataset'] ?? ''); ?>
                                        <tr>
                                            <td class="mono"><?= h($dataset_name) ?></td>
                                            <td><?= h((string)($ds['rows'] ?? '0')) ?></td>
                                            <td><?= h((string)($ds['size_bytes'] ?? '0')) ?></td>
                                            <td><?= h((string)($ds['updated_at'] ?? 'N/A')) ?></td>
                                            <td class="mono"><?= h(substr((string)($ds['sha256'] ?? ''), 0, 14)) ?>...</td>
                                            <td>
                                                <button class="row-download js-download-file" type="button" data-dataset="<?= h($dataset_name) ?>">Descargar</button>
                                            </td>
                                        </tr>
                                    <?php endforeach; ?>
                                </tbody>
                            </table>
                        </div>
                    <?php else: ?>
                        <div class="empty">No hay datasets disponibles para este dispositivo.</div>
                    <?php endif; ?>
                <?php else: ?>
                    <div class="empty">No se puede mostrar el detalle porque el respaldo no existe aun.</div>
                <?php endif; ?>
            <?php endif; ?>
        </main>
    </section>
</div>

<div class="modal" id="downloadModal" aria-hidden="true">
    <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="modalTitle">
        <div class="modal-head">
            <h3 class="modal-title" id="modalTitle">Opciones de descarga</h3>
            <button class="close-btn" type="button" id="closeDownloadModal">Cerrar</button>
        </div>
        <div class="hint">Elige formato de salida para el paquete consolidado.</div>
        <div class="dl-grid">
            <div class="dl-card">
                <h3>ZIP</h3>
                <p>Formato recomendado. Compatible con todos los sistemas.</p>
                <button class="action-btn pack-zip js-download-pack" type="button" data-format="zip">Descargar en ZIP</button>
            </div>
            <div class="dl-card">
                <h3>RAR</h3>
                <p>Formato comprimido de alta eficiencia. Requiere programa compatible para abrir.</p>
                <button class="action-btn pack-rar js-download-pack" type="button" data-format="rar">Descargar en RAR</button>
            </div>
        </div>
        <div class="note">Si RAR falla usa ZIP.</div>
    </div>
</div>

<script>
(() => {
    const openBtn = document.getElementById('openDownloadModal');
    const modal = document.getElementById('downloadModal');
    const closeBtn = document.getElementById('closeDownloadModal');
    const passwordInput = document.getElementById('downloadPassword');
    const verifyBtn = document.getElementById('verifyPasswordBtn');
    const authAlert = document.getElementById('downloadAuthAlert');
    const authState = document.getElementById('downloadAuthState');
    const packButtons = document.querySelectorAll('.js-download-pack');
    const fileButtons = document.querySelectorAll('.js-download-file');

    const usuarioMadre = <?= json_encode((string)$usuario_madre, JSON_UNESCAPED_UNICODE) ?>;
    const codigoDispositivo = <?= json_encode(normalize_codigo_dispositivo($codigo_dispositivo), JSON_UNESCAPED_UNICODE) ?>;
    const downloadPackEndpoint = <?= json_encode($download_pack_endpoint, JSON_UNESCAPED_UNICODE) ?>;
    const downloadFileEndpoint = <?= json_encode($download_file_endpoint, JSON_UNESCAPED_UNICODE) ?>;
    const verifyAuthEndpoint = <?= json_encode($verify_auth_endpoint, JSON_UNESCAPED_UNICODE) ?>;

    if (!openBtn || !modal || !closeBtn || !passwordInput || !verifyBtn || openBtn.disabled) return;

    const closeModal = () => {
        modal.classList.remove('open');
        modal.setAttribute('aria-hidden', 'true');
    };
    const openModal = () => {
        modal.classList.add('open');
        modal.setAttribute('aria-hidden', 'false');
    };

    const showAuthError = (msg) => {
        if (!authAlert) return;
        authAlert.textContent = msg || 'Debes ingresar tu contrasena para descargar.';
        authAlert.classList.add('show');
    };

    const hideAuthError = () => {
        if (!authAlert) return;
        authAlert.classList.remove('show');
    };

    let authExpiresAtMs = 0;
    let authTickTimer = null;

    const formatRemaining = (secs) => {
        const n = Math.max(0, Number(secs || 0));
        const m = Math.floor(n / 60);
        const s = n % 60;
        return `${m}:${String(s).padStart(2, '0')}`;
    };

    const setAuthState = (active, remainingSec) => {
        if (!authState) return;

        if (active) {
            authExpiresAtMs = Date.now() + (Math.max(1, Number(remainingSec || 0)) * 1000);
            authState.textContent = `Logueo activo: ${formatRemaining(Math.floor((authExpiresAtMs - Date.now()) / 1000))}`;
            authState.style.color = '#1f6a3a';
            if (authTickTimer) {
                clearInterval(authTickTimer);
            }
            authTickTimer = window.setInterval(() => {
                const left = Math.floor((authExpiresAtMs - Date.now()) / 1000);
                if (left <= 0) {
                    clearInterval(authTickTimer);
                    authTickTimer = null;
                    authExpiresAtMs = 0;
                    authState.textContent = 'Sesion expirada. Vuelve a presionar OK.';
                    authState.style.color = '#8a2a06';
                    return;
                }
                authState.textContent = `Logueo activo: ${formatRemaining(left)}`;
            }, 1000);
            return;
        }

        authExpiresAtMs = 0;
        if (authTickTimer) {
            clearInterval(authTickTimer);
            authTickTimer = null;
        }
        authState.textContent = 'Sesion no verificada.';
        authState.style.color = '#33506f';
    };

    const hasActiveLogin = () => authExpiresAtMs > Date.now();

    const postDownload = (action, fields) => {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = action;
        form.target = '_blank';
        form.style.display = 'none';

        Object.entries(fields || {}).forEach(([k, v]) => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = k;
            input.value = String(v ?? '');
            form.appendChild(input);
        });

        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);
    };

    const verifyPassword = async () => {
        hideAuthError();
        const pwd = String(passwordInput.value || '').trim();
        if (!pwd) {
            showAuthError('Ingresa tu contrasena y presiona OK.');
            passwordInput.focus();
            return;
        }

        verifyBtn.disabled = true;
        verifyBtn.textContent = 'Verificando...';

        try {
            const resp = await fetch(verifyAuthEndpoint, {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: 'verify',
                    usuario_madre: usuarioMadre,
                    password: pwd
                })
            });

            let data = null;
            try {
                data = await resp.json();
            } catch (_e) {
                data = null;
            }

            if (!resp.ok || !data || data.success !== true) {
                setAuthState(false, 0);
                showAuthError((data && data.error) ? data.error : 'Contrasena incorrecta.');
                return;
            }

            passwordInput.value = '';
            hideAuthError();
            setAuthState(true, Number(data.expires_in || 900));
        } catch (_e) {
            showAuthError('No se pudo validar la contrasena. Intenta otra vez.');
        } finally {
            verifyBtn.disabled = false;
            verifyBtn.textContent = 'OK';
        }
    };

    const checkAuthStatus = async () => {
        try {
            const resp = await fetch(verifyAuthEndpoint, {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: 'status',
                    usuario_madre: usuarioMadre
                })
            });
            const data = await resp.json();
            if (resp.ok && data && data.success === true && data.active === true) {
                setAuthState(true, Number(data.expires_in || 0));
            } else {
                setAuthState(false, 0);
            }
        } catch (_e) {
            setAuthState(false, 0);
        }
    };

    openBtn.addEventListener('click', openModal);
    closeBtn.addEventListener('click', closeModal);
    verifyBtn.addEventListener('click', verifyPassword);
    passwordInput.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter') {
            ev.preventDefault();
            verifyPassword();
        }
    });
    modal.addEventListener('click', (ev) => {
        if (ev.target === modal) closeModal();
    });
    document.addEventListener('keydown', (ev) => {
        if (ev.key === 'Escape') closeModal();
    });
    passwordInput.addEventListener('input', () => hideAuthError());

    packButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
            if (!hasActiveLogin()) {
                showAuthError('Primero valida la contrasena con OK.');
                closeModal();
                return;
            }
            const format = String(btn.getAttribute('data-format') || 'zip').toLowerCase() === 'rar' ? 'rar' : 'zip';
            postDownload(downloadPackEndpoint, {
                usuario_madre: usuarioMadre,
                codigo_dispositivo: codigoDispositivo,
                include_children: 1,
                format: format
            });
            closeModal();
        });
    });

    fileButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
            if (!hasActiveLogin()) {
                showAuthError('Primero valida la contrasena con OK.');
                return;
            }
            const dataset = String(btn.getAttribute('data-dataset') || '').trim();
            if (!dataset) return;
            postDownload(downloadFileEndpoint, {
                usuario_madre: usuarioMadre,
                codigo_dispositivo: codigoDispositivo,
                dataset: dataset
            });
        });
    });

    checkAuthStatus();
})();
</script>
</body>
</html>
