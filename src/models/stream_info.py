from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StreamInfo:
    """Representa um formato de áudio retornado pelo yt-dlp --dump-json."""

    format_id: str
    ext: str
    acodec: str
    vcodec: str = "none"
    abr: float | None = None
    asr: int | None = None
    filesize: int | None = None
    filesize_approx: int | None = None
    format_note: str = ""
    tbr: float | None = None
    audio_channels: int | None = None
    protocol: str = ""

    @property
    def is_audio_only(self) -> bool:
        v = (self.vcodec or "none").lower()
        a = (self.acodec or "none").lower()
        return v == "none" and a != "none"

    @property
    def is_opus(self) -> bool:
        return "opus" in (self.acodec or "").lower()

    @property
    def is_aac(self) -> bool:
        ac = (self.acodec or "").lower()
        return ac.startswith("mp4a") or "aac" in ac

    @property
    def is_premium_high_bitrate(self) -> bool:
        return self.format_id in {"141", "774"} or (self.abr is not None and self.abr >= 230)

    @property
    def effective_size_bytes(self) -> int | None:
        return self.filesize if self.filesize is not None else self.filesize_approx

    @property
    def size_mb_str(self) -> str:
        size = self.effective_size_bytes
        if size is None or size <= 0:
            return "—"
        return f"{size / (1024 * 1024):.2f} MB"

    @property
    def abr_str(self) -> str:
        if self.abr is None or self.abr <= 0:
            if self.tbr is not None and self.tbr > 0:
                return f"~{self.tbr:.0f} kbps"
            return "—"
        return f"{self.abr:.0f} kbps"

    @property
    def asr_str(self) -> str:
        if self.asr is None or self.asr <= 0:
            return "—"
        return f"{self.asr} Hz"

    @classmethod
    def from_ytdlp_dict(cls, raw: dict[str, Any]) -> StreamInfo:
        def _to_float(val: Any) -> float | None:
            if val is None:
                return None
            try:
                return float(val)
            except (TypeError, ValueError):
                return None

        def _to_int(val: Any) -> int | None:
            if val is None:
                return None
            try:
                return int(val)
            except (TypeError, ValueError):
                return None

        return cls(
            format_id=str(raw.get("format_id", "")),
            ext=str(raw.get("ext", "")),
            acodec=str(raw.get("acodec") or "none"),
            vcodec=str(raw.get("vcodec") or "none"),
            abr=_to_float(raw.get("abr")),
            asr=_to_int(raw.get("asr")),
            filesize=_to_int(raw.get("filesize")),
            filesize_approx=_to_int(raw.get("filesize_approx")),
            format_note=str(raw.get("format_note") or ""),
            tbr=_to_float(raw.get("tbr")),
            audio_channels=_to_int(raw.get("audio_channels")),
            protocol=str(raw.get("protocol") or ""),
        )
