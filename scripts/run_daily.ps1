# Ejecuta el pipeline Murphy + portafolio una vez y guarda log.
# Uso manual: .\scripts\run_daily.ps1
# Uso con Task Scheduler: llamar a powershell.exe -ExecutionPolicy Bypass -File "C:\Users\boosa\Documents\ANALISIS INVIU\scripts\run_daily.ps1"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $ProjectDir "logs"
$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$LogFile = Join-Path $LogDir "daily_$Timestamp.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$env:PYTHONIOENCODING = "utf-8"
Set-Location $ProjectDir

"Inicio: $(Get-Date)" | Out-File -FilePath $LogFile -Encoding utf8

python run_all.py --max-cands 60 *>> $LogFile

"Fin: $(Get-Date)" | Out-File -FilePath $LogFile -Append -Encoding utf8
