from __future__ import annotations

import os
import sys
from pathlib import Path

APP_FOLDER_NAME = "SonicFetchWindows"


def is_frozen() -> bool:
    """Retorna True quando empacotado com PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def app_root_dir() -> Path:
    """Diretório raiz da aplicação (projeto em dev ou pasta do .exe em produção)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def local_bin_dir() -> Path:
    """Pasta ./bin local ao projeto ou executável."""
    return app_root_dir() / "bin"


def appdata_dir() -> Path:
    """Diretório persistente de configurações e histórico em %APPDATA%."""
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / APP_FOLDER_NAME
    return Path.home() / "AppData" / "Roaming" / APP_FOLDER_NAME


def localappdata_bin_dir() -> Path:
    """Diretório alternativo para binários gerenciados em %LOCALAPPDATA%."""
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / APP_FOLDER_NAME / "bin"
    return Path.home() / "AppData" / "Local" / APP_FOLDER_NAME / "bin"


def preferred_bin_dir() -> Path:
    """Retorna a pasta bin gravável preferencial para instalar dependências."""
    local = local_bin_dir()
    if _is_dir_writable(local):
        return local
    fallback = localappdata_bin_dir()
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _is_dir_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def config_file_path() -> Path:
    d = appdata_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "config.json"


def history_file_path() -> Path:
    d = appdata_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "history.json"


def logs_dir() -> Path:
    d = appdata_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def default_output_dir() -> Path:
    return Path.home() / "Music" / "SonicFetch_UVR5"
