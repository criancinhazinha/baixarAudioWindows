from __future__ import annotations

import re
from dataclasses import dataclass

# Exemplos suportados:
# [download]  42.3% of   4.56MiB at    1.23MiB/s ETA 00:02
# [download]  42.3% of ~  4.56MiB at  512.00KiB/s ETA 00:05 (frag 3/10)
# [download] 100% of   4.56MiB in 00:00:03 at 1.45MiB/s
_PROGRESS_RE = re.compile(
    r"\[download\]\s+(?P<percent>\d+(?:\.\d+)?)%\s+of\s+~?\s*(?P<total>[0-9.]+\s*\S+)"
    r"(?:\s+at\s+(?P<speed>\S+/s))?(?:\s+ETA\s+(?P<eta>\S+))?",
    re.IGNORECASE,
)
_COMPLETE_RE = re.compile(
    r"\[download\]\s+100(?:\.0)?%\s+of\s+~?\s*(?P<total>[0-9.]+\s*\S+)\s+in\s+\S+(?:\s+at\s+(?P<speed>\S+/s))?",
    re.IGNORECASE,
)
_DEST_RE = re.compile(r"^\[download\]\s+Destination:\s+(?P<path>.+)$")
_ALREADY_RE = re.compile(r"^\[download\]\s+(?P<path>.+?)\s+has already been downloaded$")
_EXTRACT_AUDIO_RE = re.compile(r"^\[ExtractAudio\]\s+Destination:\s+(?P<path>.+)$")
_FORMAT_INFO_RE = re.compile(r"\[info\]\s+\S+:\s+Downloading\s+\d+\s+format\(s\):\s+(?P<fid>\S+)")


@dataclass(frozen=True)
class ProgressEvent:
    kind: str  # "progress", "destination", "extract_audio", "format_id", "already_downloaded", "postprocess"
    percent: float | None = None
    total_text: str | None = None
    speed_text: str | None = None
    eta_text: str | None = None
    path: str | None = None
    format_id: str | None = None


def parse_ytdlp_line(line: str) -> ProgressEvent | None:
    """Interpreta uma linha de stdout/stderr do yt-dlp e retorna ProgressEvent se relevante."""
    text = (line or "").strip()
    if not text:
        return None

    if m := _COMPLETE_RE.search(text):
        return ProgressEvent(
            kind="progress",
            percent=100.0,
            total_text=m.group("total").strip(),
            speed_text=(m.group("speed") or "—").strip(),
            eta_text="00:00",
        )

    if m := _PROGRESS_RE.search(text):
        pct = float(m.group("percent"))
        return ProgressEvent(
            kind="progress",
            percent=max(0.0, min(100.0, pct)),
            total_text=m.group("total").strip(),
            speed_text=(m.group("speed") or "—").strip(),
            eta_text=(m.group("eta") or "—").strip(),
        )

    if m := _DEST_RE.match(text):
        return ProgressEvent(kind="destination", path=m.group("path").strip())

    if m := _ALREADY_RE.match(text):
        return ProgressEvent(kind="already_downloaded", path=m.group("path").strip(), percent=100.0)

    if m := _EXTRACT_AUDIO_RE.match(text):
        return ProgressEvent(kind="extract_audio", path=m.group("path").strip())

    if m := _FORMAT_INFO_RE.search(text):
        return ProgressEvent(kind="format_id", format_id=m.group("fid").strip())

    if text.startswith(("[ExtractAudio]", "[Metadata]", "[Fixup")):
        return ProgressEvent(kind="postprocess")

    return None
