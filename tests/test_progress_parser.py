from __future__ import annotations

from src.core.progress_parser import parse_ytdlp_line


def test_parse_standard_progress_line() -> None:
    ev = parse_ytdlp_line("[download]  42.3% of   4.56MiB at    1.23MiB/s ETA 00:02")
    assert ev is not None
    assert ev.kind == "progress"
    assert ev.percent == 42.3
    assert ev.total_text == "4.56MiB"
    assert ev.speed_text == "1.23MiB/s"
    assert ev.eta_text == "00:02"


def test_parse_approx_progress_line_with_frag() -> None:
    ev = parse_ytdlp_line("[download]  88.5% of ~ 12.30MiB at  512.00KiB/s ETA 00:05 (frag 3/10)")
    assert ev is not None
    assert ev.kind == "progress"
    assert ev.percent == 88.5
    assert ev.total_text == "12.30MiB"
    assert ev.speed_text == "512.00KiB/s"
    assert ev.eta_text == "00:05"


def test_parse_complete_line() -> None:
    ev = parse_ytdlp_line("[download] 100% of   4.56MiB in 00:00:03 at 1.45MiB/s")
    assert ev is not None
    assert ev.kind == "progress"
    assert ev.percent == 100.0
    assert ev.eta_text == "00:00"
    assert ev.speed_text == "1.45MiB/s"


def test_parse_destination_extract_and_format_info() -> None:
    dest = parse_ytdlp_line(r"[download] Destination: C:\Music\song [251].webm")
    assert dest is not None and dest.kind == "destination"
    assert dest.path == r"C:\Music\song [251].webm"

    ext = parse_ytdlp_line(r"[ExtractAudio] Destination: C:\Music\song [251].wav")
    assert ext is not None and ext.kind == "extract_audio"
    assert ext.path == r"C:\Music\song [251].wav"

    fmt = parse_ytdlp_line("[info] dQw4w9WgXcQ: Downloading 1 format(s): 251")
    assert fmt is not None and fmt.kind == "format_id"
    assert fmt.format_id == "251"
