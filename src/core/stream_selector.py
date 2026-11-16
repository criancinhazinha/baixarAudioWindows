from __future__ import annotations

from typing import Any

from src.models.audio_profile import AudioProfile
from src.models.stream_info import StreamInfo
from src.models.video_metadata import PlaylistEntry, TopicSearchResult, VideoMetadata


def is_topic_channel(channel: str | None, uploader: str | None = None) -> bool:
    """Identifica faixas oficiais geradas automaticamente ('Artista - Topic')."""
    for candidate in (channel, uploader):
        if candidate and candidate.strip().lower().endswith("- topic"):
            return True
    return False


def is_music_youtube_url(url: str | None) -> bool:
    return bool(url and "music.youtube.com" in url.lower())


def extract_audio_streams(raw_formats: list[dict[str, Any]]) -> list[StreamInfo]:
    """Extrai somente streams audio-only e ordena por prioridade UVR5."""
    streams: list[StreamInfo] = []
    for fmt in raw_formats or []:
        info = StreamInfo.from_ytdlp_dict(fmt)
        if not info.format_id:
            continue
        if info.is_audio_only:
            streams.append(info)

    def _sort_key(s: StreamInfo) -> tuple[int, float, int]:
        priority_ids = {"774": 5, "141": 4, "251": 3, "140": 2, "250": 1, "249": 0}
        id_rank = priority_ids.get(s.format_id, 1 if s.is_opus else 0)
        abr_val = s.abr if s.abr is not None else (s.tbr or 0.0)
        asr_val = s.asr or 0
        return (id_rank, abr_val, asr_val)

    streams.sort(key=_sort_key, reverse=True)
    return streams


def select_recommended_stream(
    streams: list[StreamInfo],
    profile: AudioProfile,
) -> StreamInfo | None:
    """Seleciona o stream mais adequado conforme o perfil UVR5 ativo."""
    if not streams:
        return None

    by_id = {s.format_id: s for s in streams}

    if profile == AudioProfile.RAW_M4A:
        for fid in ("141", "140"):
            if fid in by_id:
                return by_id[fid]
        aac_streams = [s for s in streams if s.ext.lower() == "m4a" or s.is_aac]
        if aac_streams:
            return max(aac_streams, key=lambda s: (s.abr or s.tbr or 0.0, s.asr or 0))
        return streams[0]

    # RAW_OPUS_OR_BEST, WAV_NATIVE, MP3_LEGACY: prioriza melhor fidelidade nativa
    # Se houver stream Premium 256 kbps (774 Opus ou 141 AAC), prioriza-o sobre 251/140 padrão.
    for fid in ("774", "141", "251", "140"):
        if fid in by_id:
            return by_id[fid]

    opus_streams = [s for s in streams if s.is_opus]
    if opus_streams:
        return max(opus_streams, key=lambda s: (s.abr or s.tbr or 0.0, s.asr or 0))
    return max(streams, key=lambda s: (s.abr or s.tbr or 0.0, s.asr or 0))


def parse_ytdlp_metadata(raw: dict[str, Any], original_url: str = "") -> VideoMetadata:
    """Converte o JSON retornado pelo yt-dlp --dump-json em VideoMetadata."""
    raw_type = str(raw.get("_type") or "")
    entries_raw = raw.get("entries")

    if raw_type == "playlist" or isinstance(entries_raw, list):
        parsed_entries: list[PlaylistEntry] = []
        for entry in entries_raw or []:
            if not isinstance(entry, dict):
                continue
            eid = str(entry.get("id") or "")
            eurl = str(entry.get("webpage_url") or entry.get("url") or "")
            if eurl and not eurl.startswith("http") and eid:
                eurl = f"https://www.youtube.com/watch?v={eid}"
            echannel = str(entry.get("channel") or entry.get("uploader") or "")
            parsed_entries.append(
                PlaylistEntry(
                    id=eid,
                    title=str(entry.get("title") or "Faixa sem título"),
                    url=eurl,
                    channel=echannel,
                    duration=entry.get("duration"),
                    is_topic_master=is_topic_channel(echannel),
                    thumbnail=str(entry.get("thumbnail") or ""),
                )
            )
        return VideoMetadata(
            id=str(raw.get("id") or ""),
            title=str(raw.get("title") or "Playlist"),
            url=original_url or str(raw.get("webpage_url") or ""),
            webpage_url=str(raw.get("webpage_url") or original_url),
            channel=str(raw.get("channel") or raw.get("uploader") or ""),
            uploader=str(raw.get("uploader") or ""),
            is_playlist=True,
            playlist_title=str(raw.get("title") or "Playlist"),
            entries=parsed_entries,
        )

    channel = str(raw.get("channel") or "")
    uploader = str(raw.get("uploader") or "")
    webpage_url = str(raw.get("webpage_url") or original_url)
    is_music = is_music_youtube_url(original_url) or is_music_youtube_url(webpage_url)
    topic_master = is_topic_channel(channel, uploader) or is_music

    streams = extract_audio_streams(raw.get("formats") or [])
    recommended = select_recommended_stream(streams, AudioProfile.RAW_OPUS_OR_BEST)

    thumbnail = str(raw.get("thumbnail") or "")
    if not thumbnail and isinstance(raw.get("thumbnails"), list) and raw["thumbnails"]:
        last_thumb = raw["thumbnails"][-1]
        if isinstance(last_thumb, dict):
            thumbnail = str(last_thumb.get("url") or "")

    return VideoMetadata(
        id=str(raw.get("id") or ""),
        title=str(raw.get("title") or "Faixa sem título"),
        url=webpage_url or original_url,
        webpage_url=webpage_url,
        channel=channel,
        uploader=uploader,
        duration=raw.get("duration"),
        thumbnail=thumbnail,
        is_topic_master=topic_master,
        is_music_url=is_music,
        streams=streams,
        recommended_stream=recommended,
        is_playlist=False,
    )


def parse_topic_search_results(raw_entries: list[dict[str, Any]]) -> list[TopicSearchResult]:
    """Converte entradas de ytsearch para lista de TopicSearchResult priorizando '- Topic'."""
    results: list[TopicSearchResult] = []
    for item in raw_entries:
        vid = str(item.get("id") or "")
        url = str(item.get("webpage_url") or item.get("url") or "")
        if url and not url.startswith("http") and vid:
            url = f"https://www.youtube.com/watch?v={vid}"
        channel = str(item.get("channel") or item.get("uploader") or "")
        results.append(
            TopicSearchResult(
                id=vid,
                title=str(item.get("title") or "Sem título"),
                url=url,
                channel=channel or "Canal desconhecido",
                duration=item.get("duration"),
                is_topic_master=is_topic_channel(channel),
                thumbnail=str(item.get("thumbnail") or ""),
            )
        )
    results.sort(key=lambda r: (not r.is_topic_master))
    return results[:5]
