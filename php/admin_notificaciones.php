<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Administrador de Notificaciones VISO</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        .header {
            background: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .header h1 {
            color: #1a1a1a;
            font-size: 28px;
            margin-bottom: 5px;
        }

        .header p {
            color: #666;
            font-size: 14px;
        }

        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }

        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
        }

        .card {
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .card h2 {
            color: #1a1a1a;
            font-size: 18px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
        }

        .form-group {
            margin-bottom: 15px;
        }

        label {
            display: block;
            color: #333;
            font-weight: 600;
            margin-bottom: 6px;
            font-size: 13px;
        }

        input[type="text"],
        input[type="password"],
        textarea,
        select {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 13px;
            font-family: inherit;
            transition: border-color 0.3s;
        }

        input[type="text"]:focus,
        input[type="password"]:focus,
        textarea:focus,
        select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        textarea {
            resize: vertical;
            min-height: 100px;
        }

        button {
            background: #667eea;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.3s;
            width: 100%;
        }

        button:hover {
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }

        button:active {
            transform: translateY(0);
        }

        .alert {
            padding: 12px 15px;
            border-radius: 6px;
            margin-bottom: 15px;
            font-size: 13px;
            font-weight: 500;
        }

        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }

        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }

        .alert-warning {
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeeba;
        }

        .alert-info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }

        .notificaciones-list {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }

        .notificacion-item {
            padding: 15px;
            border-bottom: 1px solid #f0f0f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .notificacion-item:last-child {
            border-bottom: none;
        }

        .notif-content {
            flex: 1;
            padding-right: 15px;
        }

        .notif-title {
            color: #1a1a1a;
            font-weight: 600;
            margin-bottom: 4px;
            font-size: 14px;
        }

        .notif-message {
            color: #666;
            font-size: 13px;
            margin-bottom: 6px;
        }

        .notif-meta {
            display: flex;
            gap: 15px;
            font-size: 12px;
        }

        .notif-type {
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 11px;
        }

        .notif-type.success {
            background: #d4edda;
            color: #155724;
        }

        .notif-type.warning {
            background: #fff3cd;
            color: #856404;
        }

        .notif-type.error {
            background: #f8d7da;
            color: #721c24;
        }

        .notif-type.info {
            background: #d1ecf1;
            color: #0c5460;
        }

        .notif-status {
            color: #666;
            font-size: 12px;
        }

        .notif-actions {
            display: flex;
            gap: 8px;
        }

        .notif-actions button {
            width: auto;
            padding: 6px 12px;
            font-size: 12px;
            background: #f0f0f0;
            color: #333;
            border: 1px solid #ddd;
        }

        .notif-actions button:hover {
            background: #e0e0e0;
            box-shadow: none;
            transform: none;
        }

        .notif-actions button.delete {
            background: #f8d7da;
            color: #721c24;
        }

        .notif-actions button.delete:hover {
            background: #f5c6cb;
        }

        .empty-state {
            text-align: center;
            padding: 40px;
            color: #999;
        }

        .empty-state p {
            font-size: 14px;
        }

        h3 {
            color: #1a1a1a;
            font-size: 16px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📢 Administrador de Notificaciones VISO</h1>
            <p>Gestiona las notificaciones que ven los usuarios en tiempo real</p>
        </div>

        <div class="grid">
            <!-- Formulario para agregar notificación -->
            <div class="card">
                <h2>Crear Notificación</h2>
                <form method="POST" action="">
                    <input type="hidden" name="action" value="create">
                    
                    <div class="form-group">
                        <label>Título *</label>
                        <input type="text" name="titulo" required maxlength="255" placeholder="Ej: ¡Sistema actualizado!">
                    </div>

                    <div class="form-group">
                        <label>Mensaje *</label>
                        <textarea name="mensaje" required placeholder="Escribe el mensaje descriptivo..."></textarea>
                    </div>

                    <div class="form-group">
                        <label>Tipo *</label>
                        <select name="tipo" required>
                            <option value="info">ℹ️ Información</option>
                            <option value="success">✓ Éxito</option>
                            <option value="warning">⚠️ Advertencia</option>
                            <option value="error">✕ Error</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label>Enlace (opcional)</label>
                        <input type="text" name="enlace" placeholder="Ej: https://ejemplo.com" maxlength="500">
                    </div>

                    <div class="form-group">
                        <label>Acción (opcional)</label>
                        <select name="accion">
                            <option value="">-- Sin acción --</option>
                            <option value="open_app">Abrir VISO</option>
                            <option value="open_url">Abrir enlace</option>
                        </select>
                    </div>

                    <button type="submit">Crear Notificación</button>
                </form>
            </div>

            <!-- Panel de información -->
            <div class="card">
                <h2>Información</h2>
                <div style="color: #666; font-size: 13px; line-height: 1.6;">
                    <p><strong>Base de datos:</strong> u369606320_visoo</p>
                    <p><strong>Usuario:</strong> u369606320_visoo</p>
                    <p><strong>Tabla:</strong> notificaciones</p>
                    <p style="margin-top: 15px;"><strong>API Endpoint:</strong></p>
                    <code style="display: block; background: #f5f5f5; padding: 8px; border-radius: 4px; margin-top: 5px;">https://api.yhana.cloud/api/win/notis.php</code>
                    <p style="margin-top: 15px;">
                        <strong>Tipo de notificaciones:</strong>
                    </p>
                    <ul style="margin-left: 20px; margin-top: 8px;">
                        <li><span style="color: #0c5460;">info</span> - Información general</li>
                        <li><span style="color: #155724;">success</span> - Acciones exitosas</li>
                        <li><span style="color: #856404;">warning</span> - Advertencias</li>
                        <li><span style="color: #721c24;">error</span> - Errores</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- Lista de notificaciones -->
        <div class="notificaciones-list">
            <div style="padding: 20px; border-bottom: 2px solid #f0f0f0;">
                <h3>Notificaciones Activas</h3>
            </div>
            
            <?php
            // Configuración de base de datos
            $db_host = 'localhost';
            $db_user = 'u369606320_visoo';
            $db_pass = getenv('VISO_DB_PASSWORD');
            $db_name = 'u369606320_visoo';

            $conn = new mysqli($db_host, $db_user, $db_pass, $db_name);
            $conn->set_charset("utf8mb4");

            // Procesar acciones
            if ($_SERVER['REQUEST_METHOD'] === 'POST') {
                $action = $_POST['action'] ?? '';

                if ($action === 'create') {
                    $titulo = $_POST['titulo'] ?? '';
                    $mensaje = $_POST['mensaje'] ?? '';
                    $tipo = $_POST['tipo'] ?? 'info';
                    $enlace = $_POST['enlace'] ?? '';
                    $accion = $_POST['accion'] ?? '';

                    if ($titulo && $mensaje) {
                        $stmt = $conn->prepare("INSERT INTO notificaciones (titulo, mensaje, tipo, enlace, accion, activo) VALUES (?, ?, ?, ?, ?, 1)");
                        $stmt->bind_param("sssss", $titulo, $mensaje, $tipo, $enlace, $accion);
                        
                        if ($stmt->execute()) {
                            echo '<div class="alert alert-success">✓ Notificación creada exitosamente</div>';
                        } else {
                            echo '<div class="alert alert-error">✕ Error al crear la notificación</div>';
                        }
                        $stmt->close();
                    }
                } elseif ($action === 'toggle') {
                    $id = (int)$_POST['id'];
                    $stmt = $conn->prepare("UPDATE notificaciones SET activo = !activo WHERE id = ?");
                    $stmt->bind_param("i", $id);
                    $stmt->execute();
                    $stmt->close();
                } elseif ($action === 'delete') {
                    $id = (int)$_POST['id'];
                    $stmt = $conn->prepare("DELETE FROM notificaciones WHERE id = ?");
                    $stmt->bind_param("i", $id);
                    $stmt->execute();
                    $stmt->close();
                }
            }

            // Obtener todas las notificaciones
            $result = $conn->query("SELECT * FROM notificaciones ORDER BY fecha_creacion DESC");

            if ($result->num_rows > 0) {
                while ($row = $result->fetch_assoc()) {
                    $status = $row['activo'] ? 'Activa' : 'Inactiva';
                    $status_color = $row['activo'] ? '#4CAF50' : '#999';
                    $fecha = date('d/m/Y H:i', strtotime($row['fecha_creacion']));
                    ?>
                    <div class="notificacion-item">
                        <div class="notif-content">
                            <div class="notif-title"><?php echo htmlspecialchars($row['titulo']); ?></div>
                            <div class="notif-message"><?php echo htmlspecialchars($row['mensaje']); ?></div>
                            <div class="notif-meta">
                                <span class="notif-type <?php echo $row['tipo']; ?>">
                                    <?php echo strtoupper($row['tipo']); ?>
                                </span>
                                <span class="notif-status" style="color: <?php echo $status_color; ?>;">
                                    <?php echo $status; ?>
                                </span>
                                <span class="notif-status"><?php echo $fecha; ?></span>
                            </div>
                        </div>
                        <div class="notif-actions">
                            <form method="POST" action="" style="display:inline;">
                                <input type="hidden" name="action" value="toggle">
                                <input type="hidden" name="id" value="<?php echo $row['id']; ?>">
                                <button type="submit" title="<?php echo $row['activo'] ? 'Desactivar' : 'Activar'; ?>">
                                    <?php echo $row['activo'] ? '🔴 Desactivar' : '🟢 Activar'; ?>
                                </button>
                            </form>
                            <form method="POST" action="" style="display:inline;">
                                <input type="hidden" name="action" value="delete">
                                <input type="hidden" name="id" value="<?php echo $row['id']; ?>">
                                <button type="submit" class="delete" onclick="return confirm('¿Eliminar esta notificación?');">
                                      Eliminar
                                </button>
                            </form>
                        </div>
                    </div>
                    <?php
                }
            } else {
                echo '<div class="empty-state"><p>No hay notificaciones creadas</p></div>';
            }

            $conn->close();
            ?>
        </div>
    </div>
</body>
</html>
