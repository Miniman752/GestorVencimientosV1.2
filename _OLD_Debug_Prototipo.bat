@echo off
cd /d "%~dp0"
echo ==========================================
echo   DEBUG MODE - GESTOR DE VENCIMIENTOS
echo ==========================================
echo.
echo Directorio Actual: %CD%
echo.

echo Buscando Python...
if exist ".venv\Scripts\python.exe" (
    echo [OK] Python encontrado en .venv\Scripts\python.exe
    set PY=".venv\Scripts\python.exe"
) else (
    echo [ERROR] NO SE ENCUENTRA .venv\Scripts\python.exe
    echo Buscando globalmente...
    where python
    pause
    exit /b
)

echo.
echo 1. Lanzando Servidor API (Ventana Nueva)...
echo    Si esta ventana se cierra, hay un error en el servidor.
start "DEBUG API SERVER" cmd /k "%PY% -m uvicorn mobile_prototype.api_server:app --reload --port 8000"

echo.
echo Esperando 5 segundos...
timeout /t 5 >nul

echo.
echo 2. Lanzando App Movil...
echo    Cualquier error aparecera aqui abajo.
%PY% mobile_prototype/mobile_app.py

echo.
echo ==========================================
echo   FIN DE EJECUCION
echo ==========================================
pause
