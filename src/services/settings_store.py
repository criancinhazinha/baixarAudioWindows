from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.app_paths import config_file_path, history_file_path
from src.models.app_settings import AppSettings
from src.models.download_task import DownloadTask


class SettingsStore:
    """Persistência de configurações e histórico recente em %APPDATA%\\SonicFetchWindows."""

    def __init__(
        self,
        config_path: Path | None = None,
        history_path: Path | None = None,
    ) -> None:
        self._config_path = config_path or config_file_path()
        self._history_path = history_path or history_file_path()

    def load_settings(self) -> AppSettings:
        if not self._config_path.exists():
            return AppSettings()
        try:
            raw = json.loads(self._config_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                return AppSettings.from_dict(raw)
        except Exception:
            pass
        return AppSettings()

    def save_settings(self, settings: AppSettings) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(settings.to_dict(), indent=2, ensure_ascii=False)
        self._config_path.write_text(payload, encoding="utf-8")

    def load_history(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self._history_path.exists():
            return []
        try:
            raw = json.loads(self._history_path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                return [item for item in raw if isinstance(item, dict)][:limit]
        except Exception:
            pass
        return []

    def append_history(self, task: DownloadTask, limit: int = 100) -> None:
        items = self.load_history(limit=limit)
        entry = asdict(task)
        entry["profile"] = task.profile.value
        entry["status"] = task.status.value
        items = [i for i in items if i.get("task_id") != task.task_id]
        items.insert(0, entry)
        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        self._history_path.write_text(
            json.dumps(items[:limit], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
