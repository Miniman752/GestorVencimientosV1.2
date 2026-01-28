@echo off
:: Asegurar que estamos en el directorio del script
cd /d "%~dp0"

echo ==========================================
echo   GESTOR DE VENCIMIENTOS - MODO MOVIL
echo ==========================================
echo Directorio: %CD%
echo.

:: Verificar Python
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No se encuentra .venv\Scripts\python.exe
    echo Por favor verifica la instalacion.
    pause
    exit /b
)

echo 1. Iniciando Servidor (Backend)...
:: Lanzar uvicorn en una nueva ventana
start "API Server" ".venv\Scripts\python.exe" -m uvicorn mobile_prototype.api_server:app --reload --port 8000

echo Esperando 5 segundos para conectar...
timeout /t 5 >nul

echo 2. Iniciando App Movil (Frontend)...
:: Ejecutar la app en esta misma ventana (o lanzara su propia GUI)
".venv\Scripts\python.exe" mobile_prototype/mobile_app.py

echo.
echo ==========================================
echo   La App se ha cerrado.
echo ==========================================
pause