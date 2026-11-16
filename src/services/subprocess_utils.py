from __future__ import annotations

import os
import subprocess
from typing import Any


def windows_subprocess_kwargs() -> dict[str, Any]:
    """Retorna kwargs para evitar janelas de console (CMD) piscando no Windows."""
    kwargs: dict[str, Any] = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        kwargs["startupinfo"] = startupinfo
    return kwargs


def terminate_process_tree(proc: subprocess.Popen[Any] | None) -> None:
    """Encerra o processo e quaisquer subprocessos filhos (ex.: ffmpeg) no Windows."""
    if proc is None or proc.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                **windows_subprocess_kwargs(),
            )
            return
        except Exception:
            pass
    try:
        proc.terminate()
        proc.wait(timeout=3)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
