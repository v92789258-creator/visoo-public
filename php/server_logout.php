<?php
session_start();
session_unset();   // Borra variables de sesión
session_destroy(); // Destruye la sesión por completo

header("Location: login.php");
exit;
