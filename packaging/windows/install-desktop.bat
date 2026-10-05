@echo off
setlocal EnableDelayedExpansion

echo.
echo  Eco'clock - Instalador de icono (Windows)
echo  ========================================
echo.

:: Ruta del icono (misma carpeta que este .bat)
set "ICON=%~dp0ecoclock.ico"
if not exist "%ICON%" (
    echo ERROR: No se encuentra ecoclock.ico en esta carpeta.
    pause
    exit /b 1
)

:: Buscar ecoclock-gui.exe en el PATH
where ecoclock-gui >nul 2>&1
if %errorlevel% equ 0 (
    for /f "delims=" %%i in ('where ecoclock-gui') do set "TARGET=%%i"
    goto :found
)

:: Buscar en ubicaciones típicas de pip --user
for /d %%d in ("%APPDATA%\Python\Python*") do (
    if exist "%%d\Scripts\ecoclock-gui.exe" (
        set "TARGET=%%d\Scripts\ecoclock-gui.exe"
        goto :found
    )
)
for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%d\Scripts\ecoclock-gui.exe" (
        set "TARGET=%%d\Scripts\ecoclock-gui.exe"
        goto :found
    )
)

echo ERROR: No se encontro ecoclock-gui.exe
echo.
echo Instala primero la GUI con:
echo   python -m pip install --user -e ".[gui]"
echo.
pause
exit /b 1

:found
echo Usando: %TARGET%
echo.

:: Crear atajo en el Menu Inicio del usuario
set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
set "SHORTCUT=%STARTMENU%\Eco'clock.lnk"

:: Usamos PowerShell solo para crear el .lnk (es lo mas fiable)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT%'); ^
   $s.TargetPath = '%TARGET%'; ^
   $s.WorkingDirectory = (Split-Path '%TARGET%'); ^
   $s.IconLocation = '%ICON%'; ^
   $s.Description = 'Eco''clock — Dona tiempo de computo para verificar datos climaticos'; ^
   $s.Save()"

if exist "%SHORTCUT%" (
    echo Listo: "Eco'clock" anadido al Menu Inicio.
    echo Ruta: %SHORTCUT%
) else (
    echo ERROR: No se pudo crear el atajo.
)

echo.
pause
