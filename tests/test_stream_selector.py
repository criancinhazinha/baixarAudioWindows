from __future__ import annotations

from src.core.stream_selector import (
    extract_audio_streams,
    is_topic_channel,
    parse_topic_search_results,
    parse_ytdlp_metadata,
    select_recommended_stream,
)
from src.models.audio_profile import AudioProfile


SAMPLE_FORMATS = [
    {"format_id": "137", "ext": "mp4", "vcodec": "avc1.640028", "acodec": "none", "tbr": 2000},
    {"format_id": "18", "ext": "mp4", "vcodec": "avc1.42001E", "acodec": "mp4a.40.2", "abr": 96},
    {"format_id": "249", "ext": "webm", "vcodec": "none", "acodec": "opus", "abr": 52, "asr": 48000, "filesize": 1200000},
    {"format_id": "140", "ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.2", "abr": 129, "asr": 44100, "filesize": 3200000},
    {"format_id": "251", "ext": "webm", "vcodec": "none", "acodec": "opus", "abr": 138, "asr": 48000, "filesize": 3400000},
]


def test_is_topic_channel_detection() -> None:
    assert is_topic_channel("Daft Punk - Topic") is True
    assert is_topic_channel("Legião Urbana - Topic") is True
    assert is_topic_channel("Daft Punk Official") is False


def test_extract_audio_streams_filters_video_and_muxed() -> None:
    streams = extract_audio_streams(SAMPLE_FORMATS)
    ids = [s.format_id for s in streams]
    assert "137" not in ids
    assert "18" not in ids
    assert ids == ["251", "140", "249"]


def test_select_recommended_stream_by_profile_and_premium_ids() -> None:
    streams = extract_audio_streams(SAMPLE_FORMATS)
    rec_opus = select_recommended_stream(streams, AudioProfile.RAW_OPUS_OR_BEST)
    assert rec_opus is not None and rec_opus.format_id == "251"

    rec_m4a = select_recommended_stream(streams, AudioProfile.RAW_M4A)
    assert rec_m4a is not None and rec_m4a.format_id == "140"

    premium_formats = SAMPLE_FORMATS + [
        {"format_id": "141", "ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.2", "abr": 256, "asr": 44100},
        {"format_id": "774", "ext": "webm", "vcodec": "none", "acodec": "opus", "abr": 256, "asr": 48000},
    ]
    p_streams = extract_audio_streams(premium_formats)
    assert select_recommended_stream(p_streams, AudioProfile.RAW_OPUS_OR_BEST).format_id == "774"
    assert select_recommended_stream(p_streams, AudioProfile.RAW_M4A).format_id == "141"


def test_parse_ytdlp_metadata_video_and_playlist() -> None:
    meta = parse_ytdlp_metadata(
        {
            "id": "xyz",
            "title": "Instant Crush",
            "channel": "Daft Punk - Topic",
            "duration": 337,
            "webpage_url": "https://www.youtube.com/watch?v=xyz",
            "formats": SAMPLE_FORMATS,
        }
    )
    assert meta.is_topic_master is True
    assert meta.duration_str == "05:37"
    assert meta.recommended_stream is not None
    assert meta.recommended_stream.format_id == "251"

    pl = parse_ytdlp_metadata(
        {
            "_type": "playlist",
            "id": "PL123",
            "title": "Álbum Teste",
            "entries": [
                {"id": "a1", "title": "Faixa 1", "channel": "Banda - Topic", "duration": 200},
                {"id": "a2", "title": "Faixa 2", "channel": "Canal Comum", "duration": 180},
            ],
        }
    )
    assert pl.is_playlist is True
    assert len(pl.entries) == 2
    assert pl.entries[0].is_topic_master is True
    assert pl.entries[1].is_topic_master is False


def test_parse_topic_search_prioritizes_topic_channels() -> None:
    results = parse_topic_search_results(
        [
            {"id": "1", "title": "Song (Live)", "channel": "Random Fan"},
            {"id": "2", "title": "Song", "channel": "Artist - Topic"},
        ]
    )
    assert results[0].id == "2"
    assert results[0].is_topic_master is True
