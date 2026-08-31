# Instala tarea Windows "IntermarketScanner" que corre al iniciar sesión y cada 30 min en horario US
# Requiere PowerShell elevado solo si se quiere crear en \ (opcional)
$ProjectDir = Split-Path -Parent $PSScriptRoot
if (-not $ProjectDir) { $ProjectDir = (Get-Location).Path }
$Py = "python"
$Script = Join-Path $ProjectDir "scanner\run_scanner.py"
$TaskName = "IntermarketScanner"

$Action = New-ScheduledTaskAction -Execute $Py -Argument "`"$Script`""
$TriggerLogon = New-ScheduledTaskTrigger -AtLogOn
$TriggerDaily = New-ScheduledTaskTrigger -Daily -At 13:30
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5)
# Principal: usuario actual, nivel más alto solo si hace falta
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Highest

try { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue } catch {}
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $TriggerLogon,$TriggerDaily -Settings $Settings -Principal $Principal -Description "Scanner intermarket -> Telegram @fpxbs777_bot cada 30 min"
Write-Host "Tarea $TaskName instalada. Probar: python scanner/run_scanner.py --once --force"
