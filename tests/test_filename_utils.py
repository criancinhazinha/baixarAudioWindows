from __future__ import annotations

from pathlib import Path

from src.core.filename_utils import (
    clamp_output_path,
    clean_title_for_topic_search,
    resolve_unique_path,
    sanitize_windows_filename,
    sanitize_youtube_url,
)


def test_sanitize_windows_filename_removes_reserved_and_invalid_chars() -> None:
    assert sanitize_windows_filename('Track: "One" / <Best>?*') == "Track_ _One_ _ _Best___"
    assert sanitize_windows_filename("CON") == "_CON"
    assert sanitize_windows_filename("   ...  ") == "audio_uvr5"


def test_clamp_output_path_respects_max_length(tmp_path: Path) -> None:
    long_name = ("a" * 300) + ".webm"
    clamped = clamp_output_path(tmp_path, long_name, max_total_len=240)
    assert len(str(clamped)) <= 240
    assert clamped.suffix == ".webm"


def test_resolve_unique_path_increments_suffix(tmp_path: Path) -> None:
    first = tmp_path / "song.webm"
    first.write_bytes(b"1")
    second = resolve_unique_path(first)
    assert second.name == "song (2).webm"
    second.write_bytes(b"2")
    third = resolve_unique_path(first)
    assert third.name == "song (3).webm"


def test_sanitize_youtube_url_variants() -> None:
    res = sanitize_youtube_url("https://youtu.be/dQw4w9WgXcQ?si=tracker123&t=42")
    assert res.is_valid
    assert res.cleaned_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert res.video_id == "dQw4w9WgXcQ"

    music = sanitize_youtube_url("https://music.youtube.com/watch?v=abc123&si=foo")
    assert music.is_valid
    assert music.is_music_youtube is True
    assert music.cleaned_url == "https://music.youtube.com/watch?v=abc123"

    mixed_vid = sanitize_youtube_url(
        "https://www.youtube.com/watch?v=abc123&list=PL999&index=3",
        keep_playlist=False,
    )
    assert mixed_vid.is_mixed_video_and_playlist is True
    assert mixed_vid.is_playlist is False
    assert mixed_vid.cleaned_url == "https://www.youtube.com/watch?v=abc123"

    mixed_pl = sanitize_youtube_url(
        "https://www.youtube.com/watch?v=abc123&list=PL999&index=3",
        keep_playlist=True,
    )
    assert mixed_pl.is_playlist is True
    assert mixed_pl.cleaned_url == "https://www.youtube.com/playlist?list=PL999"

    search = sanitize_youtube_url("Pink Floyd Time")
    assert search.is_valid and search.is_search_query
    assert search.cleaned_url == "ytsearch5:Pink Floyd Time"

    bad = sanitize_youtube_url("https://example.com/video")
    assert bad.is_valid is False


def test_clean_title_for_topic_search() -> None:
    cleaned = clean_title_for_topic_search(
        "Bohemian Rhapsody (Official Video) [4K Remastered]",
        "Queen Official",
    )
    assert "Official Video" not in cleaned
    assert "Bohemian Rhapsody" in cleaned
