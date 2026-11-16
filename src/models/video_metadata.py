from __future__ import annotations

from dataclasses import dataclass, field

from src.models.stream_info import StreamInfo


def format_duration(seconds: int | float | None) -> str:
    """Formata duração em MM:SS ou HH:MM:SS."""
    if seconds is None or seconds < 0:
        return "--:--"
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


@dataclass(frozen=True)
class PlaylistEntry:
    id: str
    title: str
    url: str
    channel: str = ""
    duration: int | float | None = None
    is_topic_master: bool = False
    thumbnail: str = ""

    @property
    def duration_str(self) -> str:
        return format_duration(self.duration)


@dataclass(frozen=True)
class TopicSearchResult:
    id: str
    title: str
    url: str
    channel: str
    duration: int | float | None = None
    is_topic_master: bool = False
    thumbnail: str = ""

    @property
    def duration_str(self) -> str:
        return format_duration(self.duration)


@dataclass
class VideoMetadata:
    id: str
    title: str
    url: str
    webpage_url: str = ""
    channel: str = ""
    uploader: str = ""
    duration: int | float | None = None
    thumbnail: str = ""
    is_topic_master: bool = False
    is_music_url: bool = False
    streams: list[StreamInfo] = field(default_factory=list)
    recommended_stream: StreamInfo | None = None
    is_playlist: bool = False
    playlist_title: str = ""
    entries: list[PlaylistEntry] = field(default_factory=list)

    @property
    def display_artist(self) -> str:
        return self.channel or self.uploader or "Canal desconhecido"

    @property
    def duration_str(self) -> str:
        return format_duration(self.duration)

    @property
    def has_premium_stream(self) -> bool:
        return any(s.is_premium_high_bitrate for s in self.streams)
