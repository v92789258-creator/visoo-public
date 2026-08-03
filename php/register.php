<?php
/**
 * PÁGINA DE REGISTRO - api.yhana.cloud/register.php
 * Interfaz web para que los usuarios se registren en VISO
 * 
 * Características:
 * - Formulario responsive
 * - Validación en cliente y servidor
 * - Integración con login.php API
 * - Diseño moderno y limpio
 */
?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Registrarse en VISO</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .container {
            width: 100%;
            max-width: 450px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 40px;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
        }

        .logo {
            font-size: 32px;
            font-weight: 700;
            color: #2196F3;
            margin-bottom: 10px;
        }

        .header h1 {
            font-size: 24px;
            color: #263238;
            margin-bottom: 8px;
            font-weight: 600;
        }

        .header p {
            color: #666;
            font-size: 14px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            font-size: 13px;
            font-weight: 600;
            color: #263238;
            margin-bottom: 8px;
        }

        input[type="text"],
        input[type="email"],
        input[type="password"],
        input[type="tel"],
        textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            font-family: inherit;
            transition: border-color 0.3s;
        }

        input[type="text"]:focus,
        input[type="email"]:focus,
        input[type="password"]:focus,
        input[type="tel"]:focus,
        textarea:focus {
            outline: none;
            border-color: #2196F3;
            box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
        }

        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }

        .form-row .form-group {
            margin-bottom: 0;
        }

        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #2196F3, #1976D2);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            margin-top: 10px;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(33, 150, 243, 0.3);
        }

        button:active {
            transform: translateY(0);
        }

        .login-link {
            text-align: center;
            margin-top: 20px;
            color: #666;
            font-size: 14px;
        }

        .login-link a {
            color: #2196F3;
            text-decoration: none;
            font-weight: 600;
        }

        .login-link a:hover {
            text-decoration: underline;
        }

        .alert {
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 14px;
            display: none;
        }

        .alert-success {
            background: #e8f5e9;
            color: #2e7d32;
            border: 1px solid #81c784;
        }

        .alert-error {
            background: #ffebee;
            color: #c62828;
            border: 1px solid #ef5350;
        }

        .alert.show {
            display: block;
        }

        .spinner {
            display: none;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 0.8s linear infinite;
            margin: 0 auto;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        button.loading {
            opacity: 0.7;
            pointer-events: none;
        }

        button.loading .spinner {
            display: inline-block;
            margin-right: 8px;
            vertical-align: middle;
        }

        .info-box {
            background: #e3f2fd;
            border-left: 4px solid #2196F3;
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 20px;
            font-size: 13px;
            color: #1565c0;
        }

        input[type="number"] {
            width: 100%;
            padding: 12px;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            font-family: inherit;
        }

        input[type="number"]:focus {
            outline: none;
            border-color: #2196F3;
            box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">👁️ VISO</div>
            <h1>Crear Cuenta</h1>
            <p>Regístrate para comenzar a usar VISO</p>
        </div>

        <div class="info-box">
            ℹ️ <strong>Nota:</strong> Tu ID de 9 dígitos es único y se usa para identificar tu empresa en el sistema.
        </div>

        <div class="alert alert-success" id="successAlert"></div>
        <div class="alert alert-error" id="errorAlert"></div>

        <form id="registerForm" onsubmit="handleRegister(event)">
            <!-- ID de Usuario -->
            <div class="form-group">
                <label for="id_usuario">ID de Empresa (9 dígitos) *</label>
                <input type="number" id="id_usuario" name="id_usuario" placeholder="123456789" required min="100000000" max="999999999">
                <small style="color: #999; font-size: 12px; display: block; margin-top: 4px;">Ej: 123456789</small>
            </div>

            <!-- Nombre de usuario -->
            <div class="form-group">
                <label for="username">Nombre de Usuario *</label>
                <input type="text" id="username" name="username" placeholder="tu_usuario" required minlength="3">
                <small style="color: #999; font-size: 12px; display: block; margin-top: 4px;">Mínimo 3 caracteres</small>
            </div>

            <!-- Contraseña -->
            <div class="form-group">
                <label for="password">Contraseña *</label>
                <input type="password" id="password" name="password" placeholder="Contraseña segura" required minlength="6">
                <small style="color: #999; font-size: 12px; display: block; margin-top: 4px;">Mínimo 6 caracteres</small>
            </div>

            <!-- Email -->
            <div class="form-group">
                <label for="email">Email (opcional)</label>
                <input type="email" id="email" name="email" placeholder="tu@email.com">
            </div>

            <!-- Nombre de Óptica -->
            <div class="form-group">
                <label for="nombre_optica">Nombre de la Óptica (opcional)</label>
                <input type="text" id="nombre_optica" name="nombre_optica" placeholder="Nombre de tu negocio">
            </div>

            <!-- Botón -->
            <button type="submit" id="submitBtn">
                <span class="spinner"></span>
                Crear Cuenta
            </button>
        </form>

        <div class="login-link">
            ¿Ya tienes cuenta? <a href="#" onclick="alert('Por favor, inicia VISO en tu computadora para hacer login.')">Inicia sesión en VISO</a>
        </div>
    </div>

    <script>
        async function handleRegister(event) {
            event.preventDefault();

            const form = document.getElementById('registerForm');
            const btn = document.getElementById('submitBtn');
            const successAlert = document.getElementById('successAlert');
            const errorAlert = document.getElementById('errorAlert');

            // Limpiar alertas previas
            successAlert.classList.remove('show');
            errorAlert.classList.remove('show');

            // Obtener valores del formulario
            const id_usuario = document.getElementById('id_usuario').value.trim();
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value.trim();
            const email = document.getElementById('email').value.trim();
            const nombre_optica = document.getElementById('nombre_optica').value.trim();

            // Validaciones básicas
            if (!id_usuario || !username || !password) {
                showError('Por favor, completa todos los campos obligatorios.');
                return;
            }

            if (!/^\d{9}$/.test(id_usuario)) {
                showError('El ID debe ser exactamente 9 dígitos.');
                return;
            }

            if (username.length < 3) {
                showError('El usuario debe tener al menos 3 caracteres.');
                return;
            }

            if (password.length < 6) {
                showError('La contraseña debe tener al menos 6 caracteres.');
                return;
            }

            if (email && !isValidEmail(email)) {
                showError('Por favor, ingresa un email válido.');
                return;
            }

            // Mostrar estado de carga
            btn.classList.add('loading');
            btn.disabled = true;

            try {
                // Enviar al API
                const response = await fetch('https://api.yhana.cloud/api/win/login.php/usuarios/registrar', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        id_usuario: id_usuario,
                        username: username,
                        password: password,
                        email: email,
                        nombre_optica: nombre_optica
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    successAlert.textContent = '✅ ¡Cuenta creada exitosamente! Ya puedes iniciar VISO con tus credenciales.';
                    successAlert.classList.add('show');
                    form.reset();
                    btn.textContent = 'Cuenta Creada ✓';
                } else {
                    showError(data.error || 'Error al registrar. Intenta de nuevo.');
                }
            } catch (error) {
                console.error('Error:', error);
                showError('Error de conexión. Verifica tu conexión a internet e intenta de nuevo.');
            } finally {
                btn.classList.remove('loading');
                btn.disabled = false;
            }
        }

        function showError(message) {
            const errorAlert = document.getElementById('errorAlert');
            errorAlert.textContent = '❌ ' + message;
            errorAlert.classList.add('show');
        }

        function isValidEmail(email) {
            const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return re.test(email);
        }

        // Auto-format ID a medida que se escribe
        document.getElementById('id_usuario').addEventListener('input', function(e) {
            // Limitar a 9 dígitos
            if (this.value.length > 9) {
                this.value = this.value.slice(0, 9);
            }
        });
    </script>
</body>
</html>
