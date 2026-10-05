# packaging/windows/install-desktop.ps1
# Instala el icono y el atajo de Eco'clock en el Menú Inicio (y opcionalmente Escritorio)

$ErrorActionPreference = "Stop"

$IconSrc = Join-Path $PSScriptRoot "ecoclock.ico"
if (-not (Test-Path $IconSrc)) {
    Write-Error "No se encontró ecoclock.ico en $PSScriptRoot"
}

# Buscar ecoclock-gui.exe
$gui = Get-Command ecoclock-gui -ErrorAction SilentlyContinue
if (-not $gui) {
    Write-Host "Aviso: 'ecoclock-gui' no está en el PATH." -ForegroundColor Yellow
    Write-Host "¿Instalaste con:  python -m pip install --user -e `".[gui]`"  ?"
    # Intentamos ubicaciones comunes de pip --user
    $possible = @(
        "$env:APPDATA\Python\Python*\Scripts\ecoclock-gui.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python*\Scripts\ecoclock-gui.exe"
    )
    $found = Get-Item $possible -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) {
        $Target = $found.FullName
    } else {
        Write-Error "No se encontró ecoclock-gui.exe. Instálalo primero."
    }
} else {
    $Target = $gui.Source
}

Write-Host "Usando: $Target"

# Carpeta del Menú Inicio del usuario
$StartMenu = [Environment]::GetFolderPath("Programs")
$ShortcutPath = Join-Path $StartMenu "Eco'clock.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $Target
$Shortcut.WorkingDirectory = Split-Path $Target
$Shortcut.IconLocation = $IconSrc
$Shortcut.Description = "Eco'clock — Dona tiempo de cómputo para verificar datos climáticos"
$Shortcut.Save()

Write-Host "Listo: 'Eco'clock' añadido al Menú Inicio." -ForegroundColor Green
Write-Host "Ruta del atajo: $ShortcutPath"
