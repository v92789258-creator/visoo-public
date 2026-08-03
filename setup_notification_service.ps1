# Script para programar el servicio de notificaciones VISO en Windows
# Ejecutar como Administrador

$python_path = "C:/Program Files/Python313/python.exe"
$script_path = "c:/Users/USUARIO.DESKTOP-NOO0BDB/Desktop/VISO VERSIONES/4.1/viso version 4.1.4/notification_service.py"
$task_name = "VISO_Notification_Service"

# Verificar si Python existe
if (-not (Test-Path $python_path)) {
    Write-Host "❌ Python no encontrado en $python_path"
    exit 1
}

# Verificar si el script existe
if (-not (Test-Path $script_path)) {
    Write-Host "❌ Script no encontrado en $script_path"
    exit 1
}

# Crear acción para ejecutar el servicio
$action = New-ScheduledTaskAction `
    -Execute $python_path `
    -Argument "`"$script_path`""

# Crear trigger para ejecutar al iniciar sesión
$trigger = New-ScheduledTaskTrigger -AtLogOn

# Crear principal para ejecutar como usuario actual
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive

# Configuración de la tarea
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

try {
    # Eliminar tarea anterior si existe
    if (Get-ScheduledTask -TaskName $task_name -ErrorAction SilentlyContinue) {
        Write-Host "🔄 Eliminando tarea anterior..."
        Unregister-ScheduledTask -TaskName $task_name -Confirm:$false
    }
    
    # Registrar nueva tarea
    Register-ScheduledTask `
        -TaskName $task_name `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings `
        -Description "Servicio de notificaciones VISO que verifica nuevas notificaciones cada 5 minutos" `
        -Force | Out-Null
    
    Write-Host "✅ Servicio de notificaciones programado exitosamente"
    Write-Host "📋 Nombre de tarea: $task_name"
    Write-Host "🚀 Se ejecutará al iniciar sesión y verificará notificaciones cada 5 minutos"
    Write-Host ""
    Write-Host "Para eliminar la tarea más adelante, ejecuta:"
    Write-Host "Unregister-ScheduledTask -TaskName '$task_name' -Confirm:`$false"
}
catch {
    Write-Host "❌ Error registrando tarea: $_"
    exit 1
}
