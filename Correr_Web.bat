@echo off
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
echo ==========================================
echo   GESTOR VENCIMIENTOS - WEB RESPONSIVE
echo ==========================================
echo.
echo Iniciando Servidor Web...
echo Abre tu navegador en: http://localhost:8000
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m uvicorn web_prototype.api_server:app --reload --port 8000
) else (
    echo ERROR: No se encuentra Python.
    pause
    exit /b
)
pause
