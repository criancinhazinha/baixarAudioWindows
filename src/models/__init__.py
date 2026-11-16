"""Modelos de domínio do SonicFetch Desktop."""

from src.models.app_settings import AppSettings, CookieSource, ExistingFilePolicy
from src.models.audio_profile import AudioProfile, ProfileSpec, get_profile_spec
from src.models.download_task import DownloadTask, TaskStatus
from src.models.stream_info import StreamInfo
from src.models.video_metadata import PlaylistEntry, TopicSearchResult, VideoMetadata

__all__ = [
    "AppSettings",
    "AudioProfile",
    "CookieSource",
    "DownloadTask",
    "ExistingFilePolicy",
    "PlaylistEntry",
    "ProfileSpec",
    "StreamInfo",
    "TaskStatus",
    "TopicSearchResult",
    "VideoMetadata",
    "get_profile_spec",
]
