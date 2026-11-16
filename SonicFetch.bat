@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo [SonicFetch Desktop] Ambiente virtual .venv nao encontrado.
    echo Execute primeiro:
    echo   uv venv .venv --python 3.11
    echo   uv pip install -r requirements.txt
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" -m src.main
