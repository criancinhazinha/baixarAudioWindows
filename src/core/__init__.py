"""Módulos puros de domínio e lógica core do SonicFetch Desktop."""

from src.core.filename_utils import (
    SanitizedUrlResult,
    clamp_output_path,
    clean_title_for_topic_search,
    resolve_unique_path,
    sanitize_windows_filename,
    sanitize_youtube_url,
)
from src.core.progress_parser import ProgressEvent, parse_ytdlp_line
from src.core.stream_selector import (
    extract_audio_streams,
    is_music_youtube_url,
    is_topic_channel,
    parse_ytdlp_metadata,
    select_recommended_stream,
)
from src.core.ytdlp_builder import (
    YtdlpCommand,
    build_download_command,
    build_ffprobe_command,
    build_inspect_command,
    build_remux_opus_command,
    build_topic_search_command,
)

__all__ = [
    "ProgressEvent",
    "SanitizedUrlResult",
    "YtdlpCommand",
    "build_download_command",
    "build_ffprobe_command",
    "build_inspect_command",
    "build_remux_opus_command",
    "build_topic_search_command",
    "clamp_output_path",
    "clean_title_for_topic_search",
    "extract_audio_streams",
    "is_music_youtube_url",
    "is_topic_channel",
    "parse_ytdlp_line",
    "parse_ytdlp_metadata",
    "resolve_unique_path",
    "sanitize_windows_filename",
    "sanitize_youtube_url",
    "select_recommended_stream",
]
