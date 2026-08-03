<?php
ini_set('display_errors',1);
error_reporting(E_ALL);
session_start();

// Si ya hay sesión, redirigir (Opcional, buena práctica)
if(isset($_SESSION["id"])) {
    header("Location: panel.php");
    exit;
}

require_once "conexion.php"; // AJUSTA LA RUTA SI ES NECESARIO

$mensaje = "";

if ($_SERVER["REQUEST_METHOD"] == "POST") {

    $usuario = trim($_POST["usuario"] ?? "");
    $password = trim($_POST["password"] ?? "");

    if ($usuario == "" || $password == "") {
        $mensaje = "Por favor, completa todos los campos.";
    } else {

        // Buscar usuario en la BD
        // Nota: Asegúrate de que $conn existe en conexion.php
        $stmt = $conn->prepare("SELECT id, usuario, password, activo FROM usuarios WHERE usuario=? LIMIT 1");
        $stmt->bind_param("s", $usuario);
        $stmt->execute();
        $res = $stmt->get_result();

        if ($res->num_rows == 0) {
            $mensaje = "Usuario o contraseña incorrectos.";
        } else {

            $fila = $res->fetch_assoc();

            // Verificar si la cuenta está activa
            if (isset($fila['activo']) && (int)$fila['activo'] === 0) {
                $mensaje = "Cuenta suspendida o inactiva. Contacte a soporte.";
            } 
            // Verificación de contraseña
            else if (password_verify($password, $fila["password"])) {

                // *** AQUI ESTA LA MAGIA ***
                $_SESSION["id"] = $fila["id"];           
                $_SESSION["usuario"] = $fila["usuario"]; 

                header("Location: panel.php");
                exit;

            } else {
                $mensaje = "Usuario o contraseña incorrectos.";
            }
        }
    }
}
?>
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Iniciar Sesión</title>
<!-- Fuentes e Iconos -->
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">

<style>
    :root {
        --primary-color: #2563eb;       /* Azul moderno */
        --primary-hover: #1d4ed8;
        --bg-color: #f8fafc;
        --text-color: #1e293b;
        --text-muted: #64748b;
        --input-border: #cbd5e1;
        --error-bg: #fee2e2;
        --error-text: #991b1b;
    }

    * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
    
    body, html { height: 100%; width: 100%; background-color: var(--bg-color); }
    
    .container {
        display: flex;
        min-height: 100vh;
        width: 100%;
    }

    /* --- LADO IZQUIERDO (IMAGEN) --- */
    .left {
        width: 50%;
        /* Fondo con gradiente oscuro sobre la imagen para que el texto resalte */
        background-image: linear-gradient(rgba(0,0,0,0.5), rgba(0,0,0,0.8)), url('img/r.png'); 
        /* Si no tienes img/r.png, pon una URL externa o un color sólido */
        background-size: cover;
        background-position: center;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        padding: 60px;
        color: white;
    }
    
    .left-content h2 { font-size: 2.5rem; margin-bottom: 10px; font-weight: 700; text-shadow: 0 2px 4px rgba(0,0,0,0.5); }
    .left-content p { font-size: 1.1rem; opacity: 0.9; line-height: 1.6; max-width: 90%; }

    /* --- LADO DERECHO (FORMULARIO) --- */
    .right {
        width: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 40px;
        background: #ffffff;
    }

    .form-wrapper {
        width: 100%;
        max-width: 400px; /* Ancho ideal para login */
    }

    .header-form { margin-bottom: 35px; }
    .header-form h1 { font-size: 30px; font-weight: 700; color: var(--text-color); margin-bottom: 8px; }
    .header-form p { color: var(--text-muted); font-size: 14px; }

    .input-group { margin-bottom: 20px; }
    
    label {
        display: block;
        font-size: 14px;
        font-weight: 500;
        color: var(--text-color);
        margin-bottom: 8px;
    }

    /* Wrapper para poner el icono dentro del input */
    .input-wrapper { position: relative; }

    .input-wrapper i {
        position: absolute;
        left: 15px;
        top: 50%;
        transform: translateY(-50%);
        color: var(--text-muted);
        font-size: 15px;
        transition: color 0.3s;
    }

    input {
        width: 100%;
        padding: 14px 15px 14px 45px; /* Padding izquierdo extra para el icono */
        font-size: 15px;
        border: 1px solid var(--input-border);
        border-radius: 10px;
        transition: all 0.3s ease;
        background: #fff;
        color: var(--text-color);
    }

    input:focus {
        outline: none;
        border-color: var(--primary-color);
        box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.1);
    }
    
    /* Cuando el input tiene foco, el icono cambia de color */
    input:focus + i { color: var(--primary-color); }

    button {
        width: 100%;
        padding: 14px;
        background: var(--primary-color);
        color: #fff;
        border: none;
        border-radius: 10px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        transition: background 0.3s, transform 0.2s;
        margin-top: 10px;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
    }

    button:hover {
        background: var(--primary-hover);
        transform: translateY(-2px);
    }

    /* Mensajes de Error (Alert) */
    .alert {
        padding: 12px 15px;
        border-radius: 8px;
        font-size: 14px;
        margin-bottom: 25px;
        display: flex;
        align-items: center;
        gap: 10px;
        background-color: var(--error-bg);
        color: var(--error-text);
        border: 1px solid #fca5a5;
        animation: fadeIn 0.4s ease-out;
    }

    .footer-link { margin-top: 25px; text-align: center; font-size: 14px; color: var(--text-muted); }
    .footer-link a { color: var(--primary-color); text-decoration: none; font-weight: 600; }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Responsive: En celular se pone uno debajo del otro */
    @media(max-width: 900px) {
        .container { flex-direction: column; }
        .left { width: 100%; height: 250px; padding: 30px; }
        .left-content h2 { font-size: 2rem; }
        .right { width: 100%; padding: 40px 20px; flex: 1; }
    }
</style>
</head>
<body>

<div class="container">
    
    <!-- LADO IZQUIERDO -->
    <div class="left">
        <div class="left-content">
            <h2>Bienvenido</h2>
            <p>Accede a tu panel de administración y gestiona tu cuenta de forma segura.</p>
        </div>
    </div>

    <!-- LADO DERECHO -->
    <div class="right">
        <div class="form-wrapper">
            
            <div class="header-form">
                <h1>Iniciar Sesión</h1>
                <p>Ingresa tus credenciales para continuar</p>
            </div>

            <!-- MOSTRAR MENSAJE DE ERROR -->
            <?php if ($mensaje != ""): ?>
                <div class="alert">
                    <i class="fas fa-exclamation-circle"></i>
                    <span><?= htmlspecialchars($mensaje) ?></span>
                </div>
            <?php endif; ?>

            <form method="POST">
                
                <div class="input-group">
                    <label>Usuario</label>
                    <div class="input-wrapper">
                        <!-- El input primero, el icono después (controlado por CSS absolute) -->
                        <input type="text" name="usuario" placeholder="Tu usuario" required value="<?= htmlspecialchars($usuario ?? '') ?>">
                        <i class="fas fa-user"></i>
                    </div>
                </div>

                <div class="input-group">
                    <label>Contraseña</label>
                    <div class="input-wrapper">
                        <input type="password" name="password" placeholder="Tu contraseña" required>
                        <i class="fas fa-lock"></i>
                    </div>
                </div>

                <button type="submit">Entrar</button>
            </form>

            <div class="footer-link">
                ¿No tienes cuenta? <a href="registro.php">Regístrate</a>
            </div>

        </div>
    </div>

</div>

</body>
</html>