from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from src.core.stream_selector import parse_ytdlp_metadata
from src.core.ytdlp_builder import build_ffprobe_command, build_inspect_command
from src.models.app_settings import AppSettings
from src.models.video_metadata import VideoMetadata
from src.services.subprocess_utils import windows_subprocess_kwargs


@dataclass(frozen=True)
class FfprobeReport:
    file_path: str
    format_name: str
    codec_name: str
    sample_rate: str
    channels: str
    bit_rate_kbps: str
    duration_sec: str
    size_mb: str
    raw_summary: str


class InspectorService:
    """Executa --dump-single-json e ffprobe sem bloquear a UI."""

    def inspect_url(
        self,
        ytdlp_exe: Path,
        url: str,
        settings: AppSettings,
        *,
        flat_playlist: bool = True,
    ) -> tuple[VideoMetadata, str]:
        cmd = build_inspect_command(
            str(ytdlp_exe),
            url,
            settings,
            flat_playlist=flat_playlist,
        )
        proc = subprocess.run(
            cmd.full_argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
            **windows_subprocess_kwargs(),
        )
        if proc.returncode != 0:
            err_msg = (proc.stderr or proc.stdout or "Falha ao analisar URL.").strip()
            raise RuntimeError(err_msg)

        stdout = (proc.stdout or "").strip()
        if not stdout:
            raise RuntimeError("O yt-dlp não retornou metadados para esta URL.")

        raw_json = json.loads(stdout)
        metadata = parse_ytdlp_metadata(raw_json, original_url=url)
        return metadata, cmd.masked_preview

    def inspect_file_ffprobe(self, ffprobe_exe: Path, file_path: Path) -> FfprobeReport:
        if not file_path.is_file():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        argv = build_ffprobe_command(str(ffprobe_exe), file_path)
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            **windows_subprocess_kwargs(),
        )
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or "Falha ao executar ffprobe.").strip())

        data: dict[str, Any] = json.loads(proc.stdout or "{}")
        streams = data.get("streams") or []
        audio_stream = next(
            (s for s in streams if s.get("codec_type") == "audio"),
            streams[0] if streams else {},
        )
        fmt = data.get("format") or {}

        codec_name = str(audio_stream.get("codec_name") or "desconhecido")
        sample_rate = str(audio_stream.get("sample_rate") or "—")
        if sample_rate != "—":
            sample_rate = f"{sample_rate} Hz"
        channels = str(audio_stream.get("channels") or "—")

        raw_br = audio_stream.get("bit_rate") or fmt.get("bit_rate")
        try:
            bit_rate_kbps = f"{int(raw_br) / 1000:.1f} kbps" if raw_br else "—"
        except (TypeError, ValueError):
            bit_rate_kbps = "—"

        try:
            dur = float(fmt.get("duration") or audio_stream.get("duration") or 0)
            dur_str = f"{dur:.2f} s" if dur > 0 else "—"
        except (TypeError, ValueError):
            dur_str = "—"

        try:
            size_bytes = int(fmt.get("size") or file_path.stat().st_size)
            size_mb = f"{size_bytes / (1024 * 1024):.2f} MB"
        except Exception:
            size_mb = "—"

        format_name = str(fmt.get("format_name") or file_path.suffix.lstrip("."))
        pretty = json.dumps(
            {
                "file": str(file_path),
                "format": format_name,
                "codec": codec_name,
                "sample_rate": sample_rate,
                "channels": channels,
                "bit_rate": bit_rate_kbps,
                "duration": dur_str,
                "size": size_mb,
            },
            indent=2,
            ensure_ascii=False,
        )
        return FfprobeReport(
            file_path=str(file_path),
            format_name=format_name,
            codec_name=codec_name,
            sample_rate=sample_rate,
            channels=channels,
            bit_rate_kbps=bit_rate_kbps,
            duration_sec=dur_str,
            size_mb=size_mb,
            raw_summary=pretty,
        )

    def fetch_thumbnail_bytes(self, url: str) -> bytes | None:
        if not url:
            return None
        try:
            with httpx.Client(follow_redirects=True, timeout=15.0) as client:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.content
        except Exception:
            return None
