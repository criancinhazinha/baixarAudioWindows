from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from src.app_paths import default_output_dir
from src.models.audio_profile import AudioProfile


class CookieSource(str, Enum):
    NONE = "none"
    BROWSER = "browser"
    FILE = "file"


class ExistingFilePolicy(str, Enum):
    SKIP = "skip"
    OVERWRITE = "overwrite"
    RENAME = "rename"


SUPPORTED_BROWSERS: tuple[str, ...] = ("edge", "chrome", "firefox", "brave", "opera")

TEMPLATE_PRESETS: list[tuple[str, str]] = [
    (
        "Artista - Título [Format ID] (Recomendado UVR5)",
        "%(uploader)s - %(title)s [%(format_id)s].%(ext)s",
    ),
    ("Apenas Título", "%(title)s.%(ext)s"),
    ("Playlist Numerada", "%(playlist_index)02d - %(title)s.%(ext)s"),
]


@dataclass
class AppSettings:
    output_dir: str = field(default_factory=lambda: str(default_output_dir()))
    filename_template: str = "%(uploader)s - %(title)s [%(format_id)s].%(ext)s"
    default_profile: AudioProfile = AudioProfile.RAW_OPUS_OR_BEST
    remux_webm_to_opus: bool = False
    force_wav_44100_16bit: bool = False
    allow_legacy_mp3: bool = False
    embed_metadata: bool = True
    write_info_json: bool = False
    existing_file_policy: ExistingFilePolicy = ExistingFilePolicy.RENAME
    max_concurrent_downloads: int = 2
    cookie_source: CookieSource = CookieSource.NONE
    cookie_browser: str = "edge"
    cookie_file_path: str = ""
    clipboard_monitor: bool = False
    preferred_mixed_url_mode: str = "ask"  # "ask", "video", "playlist"

    def normalized_concurrency(self) -> int:
        return max(1, min(4, int(self.max_concurrent_downloads)))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["default_profile"] = self.default_profile.value
        data["existing_file_policy"] = self.existing_file_policy.value
        data["cookie_source"] = self.cookie_source.value
        data["max_concurrent_downloads"] = self.normalized_concurrency()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppSettings:
        defaults = cls()

        def _enum_val(enum_cls: type[Enum], raw: Any, fallback: Any) -> Any:
            try:
                return enum_cls(raw)
            except Exception:
                return fallback

        raw_concurrency = data.get("max_concurrent_downloads", defaults.max_concurrent_downloads)
        try:
            concurrency = max(1, min(4, int(raw_concurrency)))
        except (TypeError, ValueError):
            concurrency = defaults.max_concurrent_downloads

        browser = str(data.get("cookie_browser", defaults.cookie_browser)).lower()
        if browser not in SUPPORTED_BROWSERS:
            browser = defaults.cookie_browser

        mixed_mode = str(data.get("preferred_mixed_url_mode", defaults.preferred_mixed_url_mode))
        if mixed_mode not in {"ask", "video", "playlist"}:
            mixed_mode = "ask"

        return cls(
            output_dir=str(data.get("output_dir") or defaults.output_dir),
            filename_template=str(data.get("filename_template") or defaults.filename_template),
            default_profile=_enum_val(
                AudioProfile, data.get("default_profile"), defaults.default_profile
            ),
            remux_webm_to_opus=bool(data.get("remux_webm_to_opus", defaults.remux_webm_to_opus)),
            force_wav_44100_16bit=bool(
                data.get("force_wav_44100_16bit", defaults.force_wav_44100_16bit)
            ),
            allow_legacy_mp3=bool(data.get("allow_legacy_mp3", defaults.allow_legacy_mp3)),
            embed_metadata=bool(data.get("embed_metadata", defaults.embed_metadata)),
            write_info_json=bool(data.get("write_info_json", defaults.write_info_json)),
            existing_file_policy=_enum_val(
                ExistingFilePolicy,
                data.get("existing_file_policy"),
                defaults.existing_file_policy,
            ),
            max_concurrent_downloads=concurrency,
            cookie_source=_enum_val(
                CookieSource, data.get("cookie_source"), defaults.cookie_source
            ),
            cookie_browser=browser,
            cookie_file_path=str(data.get("cookie_file_path") or ""),
            clipboard_monitor=bool(data.get("clipboard_monitor", defaults.clipboard_monitor)),
            preferred_mixed_url_mode=mixed_mode,
        )
