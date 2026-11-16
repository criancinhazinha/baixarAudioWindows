from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from src.core.stream_selector import parse_topic_search_results
from src.core.ytdlp_builder import build_topic_search_command
from src.models.app_settings import AppSettings
from src.models.video_metadata import TopicSearchResult
from src.services.subprocess_utils import windows_subprocess_kwargs


class TopicSearchService:
    """Busca versões oficiais '- Topic' no YouTube / YouTube Music."""

    def search_topic_versions(
        self,
        ytdlp_exe: Path,
        query: str,
        settings: AppSettings,
        *,
        limit: int = 5,
    ) -> tuple[list[TopicSearchResult], str]:
        cmd = build_topic_search_command(str(ytdlp_exe), query, settings, limit=limit)
        proc = subprocess.run(
            cmd.full_argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            **windows_subprocess_kwargs(),
        )
        if proc.returncode != 0 and not (proc.stdout or "").strip():
            raise RuntimeError((proc.stderr or "Erro ao buscar versões - Topic.").strip())

        entries: list[dict[str, Any]] = []
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    entries.append(obj)
            except json.JSONDecodeError:
                continue

        return parse_topic_search_results(entries), cmd.masked_preview
