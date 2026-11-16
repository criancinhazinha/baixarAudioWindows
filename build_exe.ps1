# Script de empacotamento standalone Windows (.exe) via PyInstaller
$ErrorActionPreference = "Stop"

$PythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    throw "Ambiente virtual .venv não encontrado. Crie com: uv venv .venv --python 3.11"
}

& $PythonExe -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name "SonicFetchDesktop" `
    --paths $PSScriptRoot `
    (Join-Path $PSScriptRoot "src\main.py")

Write-Host ""
Write-Host "Build concluído em: dist\SonicFetchDesktop\SonicFetchDesktop.exe"
