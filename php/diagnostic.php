<?php
/**
 * DIAGNÓSTICO - Revisar configuración del servidor
 * Guardar como: diagnostic.php
 * Subir a: https://api.yhana.cloud/diagnostic.php
 * Acceder en navegador
 */

echo "<h1>🔍 Diagnóstico VISO - api.yhana.cloud</h1>";
echo "<hr>";

// 1. Versión PHP
echo "<h2>1. PHP Version</h2>";
echo "Versión PHP: <strong>" . phpversion() . "</strong><br>";
echo "Requerida: PHP 7.4+<br>";
if (version_compare(phpversion(), '7.4', '>=')) {
    echo "✅ OK<br>";
} else {
    echo "❌ NECESITA ACTUALIZACIÓN<br>";
}

// 2. Extensiones PHP requeridas
echo "<h2>2. Extensiones Requeridas</h2>";
$extensions = ['pdo', 'pdo_mysql', 'json', 'mbstring'];
foreach ($extensions as $ext) {
    if (extension_loaded($ext)) {
        echo "✅ $ext cargado<br>";
    } else {
        echo "❌ $ext NO CARGADO<br>";
    }
}

// 3. Prueba de conexión BD
echo "<h2>3. Conexión a Base de Datos</h2>";
$db_host = 'localhost';
$db_user = 'u369606320_visoo';
$db_pass = getenv('VISO_DB_PASSWORD');
$db_name = 'u369606320_visoo';

try {
    $pdo = new PDO(
        'mysql:host=' . $db_host . ';dbname=' . $db_name . ';charset=utf8mb4',
        $db_user,
        $db_pass,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
    echo "✅ Conexión exitosa a BD<br>";
    echo "Base de datos: $db_name<br>";
    echo "Usuario: $db_user<br>";
    
    // Verificar tablas
    echo "<h3>Tablas en BD:</h3>";
    $result = $pdo->query("SHOW TABLES");
    $tables = $result->fetchAll(PDO::FETCH_COLUMN);
    if (count($tables) > 0) {
        foreach ($tables as $table) {
            echo "✅ Tabla: $table<br>";
        }
    } else {
        echo "⚠️ No hay tablas (se crearán automáticamente)<br>";
    }
    
} catch (PDOException $e) {
    echo "❌ Error de conexión: " . $e->getMessage() . "<br>";
    echo "Host: $db_host<br>";
    echo "Usuario: $db_user<br>";
    echo "Base de datos: $db_name<br>";
}

// 4. Directorio actual
echo "<h2>4. Información del Servidor</h2>";
echo "Directorio actual: <strong>" . getcwd() . "</strong><br>";
echo "Script: <strong>" . __FILE__ . "</strong><br>";
echo "Servidor: <strong>" . $_SERVER['SERVER_SOFTWARE'] ?? 'Desconocido' . "</strong><br>";

// 5. Permisos de escritura
echo "<h2>5. Permisos</h2>";
$current_dir = getcwd();
if (is_writable($current_dir)) {
    echo "✅ Directorio es escribible<br>";
} else {
    echo "❌ Directorio NO es escribible<br>";
}

// 6. Test de JSON
echo "<h2>6. Prueba JSON</h2>";
$test_json = json_encode(['test' => 'ok']);
echo "JSON test: <strong>$test_json</strong><br>";
if (json_last_error() === JSON_ERROR_NONE) {
    echo "✅ JSON funcionando<br>";
} else {
    echo "❌ Error JSON: " . json_last_error_msg() . "<br>";
}

// 7. Funciones críticas
echo "<h2>7. Funciones Críticas</h2>";
$functions = ['password_hash', 'password_verify', 'bin2hex', 'random_bytes'];
foreach ($functions as $func) {
    if (function_exists($func)) {
        echo "✅ $func disponible<br>";
    } else {
        echo "❌ $func NO disponible<br>";
    }
}

// 8. Variables superglobales
echo "<h2>8. Variables Globales</h2>";
echo "REQUEST_METHOD: " . $_SERVER['REQUEST_METHOD'] . "<br>";
echo "REQUEST_URI: " . $_SERVER['REQUEST_URI'] . "<br>";
echo "SCRIPT_NAME: " . $_SERVER['SCRIPT_NAME'] . "<br>";
echo "PATH_INFO: " . ($_SERVER['PATH_INFO'] ?? 'No disponible') . "<br>";

// 9. Prueba de escritura en BD
echo "<h2>9. Prueba Escritura en BD</h2>";
try {
    if ($pdo) {
        $pdo->exec("
            CREATE TABLE IF NOT EXISTS test_viso (
                id INT AUTO_INCREMENT PRIMARY KEY,
                mensaje VARCHAR(255),
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ");
        echo "✅ Tabla de prueba creada<br>";
        
        $stmt = $pdo->prepare("INSERT INTO test_viso (mensaje) VALUES (?)");
        $stmt->execute(['Test desde diagnostic.php']);
        echo "✅ Inserción de prueba exitosa<br>";
        
        // Limpiar
        $pdo->exec("DROP TABLE test_viso");
        echo "✅ Tabla de prueba eliminada<br>";
    }
} catch (Exception $e) {
    echo "❌ Error: " . $e->getMessage() . "<br>";
}

echo "<hr>";
echo "<h2>✅ Resumen</h2>";
echo "<p>Si todos los items están en verde ✅, el servidor está listo para usar login.php</p>";
echo "<p>Si hay errores ❌, contacta con soporte técnico.</p>";

?>
