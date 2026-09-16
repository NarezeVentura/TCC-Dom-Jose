@echo off
setlocal

set "PROJECT_DIR=%~dp0.."
set "VENV_PYTHON=%PROJECT_DIR%\.venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    where py >nul 2>&1
    if not errorlevel 1 (
        py -3 -m venv "%PROJECT_DIR%\.venv"
    ) else (
        where python >nul 2>&1
        if errorlevel 1 (
            echo Python 3 nao foi encontrado. Instale Python 3 e tente novamente.
            pause
            exit /b 1
        )
        python -m venv "%PROJECT_DIR%\.venv"
    )
    if errorlevel 1 (
        echo Nao foi possivel criar o ambiente virtual.
        pause
        exit /b 1
    )
)

"%VENV_PYTHON%" -m pip install -r "%PROJECT_DIR%\requirements.txt"
if errorlevel 1 (
    echo Nao foi possivel instalar as dependencias.
    pause
    exit /b 1
)

start "Sistema de Vendas" "%VENV_PYTHON%" "%PROJECT_DIR%\app.py"
start "" "http://127.0.0.1:5000"
exit /b 0
