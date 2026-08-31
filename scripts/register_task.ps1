# Registra una tarea diaria en el Programador de Tareas de Windows para ejecutar el pipeline.
# Requiere PowerShell como Administrador.
# Uso: powershell.exe -ExecutionPolicy Bypass -File "C:\Users\boosa\Documents\ANALISIS INVIU\scripts\register_task.ps1" [-Time "08:00"]

param(
    [string]$Time = "08:00"
)

$ProjectDir = "C:\Users\boosa\Documents\ANALISIS INVIU"
$ScriptPath = Join-Path $ProjectDir "scripts\run_daily.ps1"
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$ScriptPath`""
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive

Register-ScheduledTask -TaskName "MurphyPortafolioDaily" -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force
Write-Host "Tarea 'MurphyPortafolioDaily' registrada para ejecutarse diariamente a las $Time"
Write-Host "Para eliminarla: Unregister-ScheduledTask -TaskName MurphyPortafolioDaily -Confirm:`$false"
