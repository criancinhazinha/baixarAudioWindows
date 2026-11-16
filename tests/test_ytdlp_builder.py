from __future__ import annotations

from pathlib import Path

from src.core.ytdlp_builder import (
    build_download_command,
    build_ffprobe_command,
    build_inspect_command,
    build_remux_opus_command,
    build_topic_search_command,
)
from src.models.app_settings import AppSettings, CookieSource, ExistingFilePolicy
from src.models.audio_profile import AudioProfile


def _base_settings(tmp_path: Path) -> AppSettings:
    return AppSettings(
        output_dir=str(tmp_path),
        filename_template="%(uploader)s - %(title)s [%(format_id)s].%(ext)s",
        existing_file_policy=ExistingFilePolicy.RENAME,
    )


def test_raw_opus_profile_never_emits_reencoding_or_resampling(tmp_path: Path) -> None:
    settings = _base_settings(tmp_path)
    cmd = build_download_command(
        "bin/yt-dlp.exe",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        AudioProfile.RAW_OPUS_OR_BEST,
        settings,
    )
    forbidden = {"-x", "--extract-audio", "--audio-format", "-ar", "44100", "-ac", "-b:a", "--audio-quality"}
    assert not any(flag in cmd.args for flag in forbidden)
    assert "-f" in cmd.args
    assert cmd.format_selector == "bestaudio[acodec=opus]/bestaudio[ext=m4a]/bestaudio"


def test_raw_m4a_profile_never_emits_reencoding_and_uses_selected_format(tmp_path: Path) -> None:
    settings = _base_settings(tmp_path)
    cmd = build_download_command(
        "bin/yt-dlp.exe",
        "https://www.youtube.com/watch?v=abc123",
        AudioProfile.RAW_M4A,
        settings,
        selected_format_id="141",
    )
    assert "-x" not in cmd.args
    assert "--audio-format" not in cmd.args
    assert "141" in cmd.args


def test_wav_native_preserves_source_sample_rate_by_default(tmp_path: Path) -> None:
    settings = _base_settings(tmp_path)
    settings.force_wav_44100_16bit = False
    cmd = build_download_command(
        "bin/yt-dlp.exe",
        "https://www.youtube.com/watch?v=abc123",
        AudioProfile.WAV_NATIVE,
        settings,
    )
    assert "-x" in cmd.args
    assert "--audio-format" in cmd.args
    idx = cmd.args.index("--audio-format")
    assert cmd.args[idx + 1] == "wav"
    assert "--postprocessor-args" not in cmd.args
    assert not any("44100" in arg for arg in cmd.args)


def test_wav_native_with_forced_44100_adds_postprocessor_args(tmp_path: Path) -> None:
    settings = _base_settings(tmp_path)
    cmd = build_download_command(
        "bin/yt-dlp.exe",
        "https://www.youtube.com/watch?v=abc123",
        AudioProfile.WAV_NATIVE,
        settings,
        force_wav_44100_16bit=True,
    )
    assert "--postprocessor-args" in cmd.args
    idx = cmd.args.index("--postprocessor-args")
    assert "ffmpeg:-ar 44100 -sample_fmt s16" == cmd.args[idx + 1]


def test_cookies_browser_and_masked_file_preview(tmp_path: Path) -> None:
    settings = _base_settings(tmp_path)
    settings.cookie_source = CookieSource.BROWSER
    settings.cookie_browser = "edge"
    cmd_browser = build_inspect_command("yt-dlp.exe", "https://youtube.com/watch?v=1", settings)
    assert "--cookies-from-browser" in cmd_browser.args
    assert "edge" in cmd_browser.args

    settings.cookie_source = CookieSource.FILE
    settings.cookie_file_path = r"C:\Users\Secret\cookies.txt"
    cmd_file = build_download_command(
        "yt-dlp.exe",
        "https://youtube.com/watch?v=1",
        AudioProfile.RAW_OPUS_OR_BEST,
        settings,
    )
    assert r"C:\Users\Secret\cookies.txt" in cmd_file.args
    assert r"C:\Users\Secret\cookies.txt" not in cmd_file.masked_preview
    assert "<cookies.txt>" in cmd_file.masked_preview


def test_remux_and_ffprobe_and_topic_search_commands(tmp_path: Path) -> None:
    settings = _base_settings(tmp_path)
    remux = build_remux_opus_command("ffmpeg.exe", tmp_path / "in.webm", tmp_path / "out.opus")
    assert "-c:a" in remux and "copy" in remux

    probe = build_ffprobe_command("ffprobe.exe", tmp_path / "out.opus")
    assert "-print_format" in probe and "json" in probe

    search = build_topic_search_command("yt-dlp.exe", "Daft Punk Instant Crush", settings)
    assert "ytsearch5:Daft Punk Instant Crush topic" in search.args
