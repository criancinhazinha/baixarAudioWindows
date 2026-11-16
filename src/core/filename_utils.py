from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

_INVALID_WIN_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE_RE = re.compile(r"\s+")
_RESERVED_WINDOWS_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

_TRACKING_PARAMS = {
    "si",
    "pp",
    "t",
    "feature",
    "ab_channel",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "kw",
    "index",
}

_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}

_TITLE_NOISE_RE = re.compile(
    r"[\(\[]\s*(?:official\s*(?:music\s*)?video|official\s*audio|lyric\s*video|lyrics|"
    r"videoclipe\s*oficial|clipe\s*oficial|audio\s*oficial|áudio\s*oficial|"
    r"hd|4k|remastered(?:\s*\d{4})?|ao\s*vivo|live)\s*[\)\]]",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SanitizedUrlResult:
    cleaned_url: str
    is_valid: bool
    is_search_query: bool = False
    is_playlist: bool = False
    is_mixed_video_and_playlist: bool = False
    is_music_youtube: bool = False
    video_id: str | None = None
    playlist_id: str | None = None
    error: str | None = None


def sanitize_windows_filename(name: str, max_length: int = 180) -> str:
    """Remove caracteres inválidos no Windows e evita nomes reservados."""
    cleaned = _INVALID_WIN_CHARS_RE.sub("_", name or "")
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip().rstrip(". ")
    if not cleaned:
        cleaned = "audio_uvr5"
    stem_upper = cleaned.split(".")[0].upper()
    if stem_upper in _RESERVED_WINDOWS_NAMES:
        cleaned = f"_{cleaned}"
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip(". ")
    return cleaned or "audio_uvr5"


def clamp_output_path(output_dir: Path, filename: str, max_total_len: int = 250) -> Path:
    """Garante que o caminho completo não ultrapasse o limite clássico do Windows."""
    candidate = output_dir / filename
    if len(str(candidate)) <= max_total_len:
        return candidate

    p = Path(filename)
    ext = p.suffix
    stem = p.stem
    dir_len = len(str(output_dir)) + 1
    available = max(16, max_total_len - dir_len - len(ext))
    trimmed_stem = stem[:available].rstrip(". ")
    return output_dir / f"{trimmed_stem}{ext}"


def resolve_unique_path(path: Path) -> Path:
    """Retorna um caminho único incrementando (2), (3), ... caso já exista."""
    if not path.exists():
        return path
    parent = path.parent
    stem = path.stem
    ext = path.suffix
    counter = 2
    while True:
        candidate = parent / f"{stem} ({counter}){ext}"
        if not candidate.exists():
            return candidate
        counter += 1


def clean_title_for_topic_search(title: str, artist: str = "") -> str:
    """Limpa sufixos de videoclipe para melhorar buscas '- Topic' no YouTube Music."""
    cleaned = _TITLE_NOISE_RE.sub("", title or "")
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip(" -|")
    if artist and artist.lower().endswith(" - topic"):
        artist_clean = artist[:-8].strip()
    else:
        artist_clean = artist.strip()
    if artist_clean and artist_clean.lower() not in cleaned.lower():
        return f"{artist_clean} {cleaned}".strip()
    return cleaned or (title or "").strip()


def sanitize_youtube_url(
    raw_input: str,
    keep_playlist: bool | None = None,
) -> SanitizedUrlResult:
    """Sanitiza URLs do YouTube/YT Music removendo tracking e tratando links mistos."""
    text = (raw_input or "").strip()
    if not text:
        return SanitizedUrlResult(
            cleaned_url="",
            is_valid=False,
            error="Informe uma URL do YouTube, YouTube Music ou termo de busca.",
        )

    # Termo de busca direta (sem esquema nem domínio YouTube)
    if "://" not in text and not any(host in text.lower() for host in _YOUTUBE_HOSTS):
        return SanitizedUrlResult(
            cleaned_url=f"ytsearch5:{text}",
            is_valid=True,
            is_search_query=True,
        )

    normalized_input = text if "://" in text else f"https://{text}"
    parsed = urlparse(normalized_input)
    host = parsed.netloc.lower().split(":")[0]

    if host not in _YOUTUBE_HOSTS:
        return SanitizedUrlResult(
            cleaned_url="",
            is_valid=False,
            error=f"Domínio não suportado: {host or text}. Use youtube.com, youtu.be ou music.youtube.com.",
        )

    is_music = host == "music.youtube.com"
    query = parse_qs(parsed.query, keep_blank_values=False)

    # Remove tracking parameters
    for param in list(query.keys()):
        if param.lower() in _TRACKING_PARAMS:
            query.pop(param, None)

    video_id: str | None = None
    playlist_id: str | None = query.get("list", [None])[0]

    if host in {"youtu.be", "www.youtu.be"}:
        seg = parsed.path.strip("/").split("/")[0]
        if seg:
            video_id = seg
    elif parsed.path.startswith("/shorts/") or parsed.path.startswith("/live/"):
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2:
            video_id = parts[1]
    else:
        video_id = query.get("v", [None])[0]

    is_playlist_only_page = parsed.path.rstrip("/") == "/playlist" and bool(playlist_id)
    is_mixed = bool(video_id and playlist_id and not is_playlist_only_page)

    base_host = "music.youtube.com" if is_music else "www.youtube.com"

    if is_playlist_only_page:
        qs = urlencode({"list": playlist_id})
        cleaned = urlunparse(("https", base_host, "/playlist", "", qs, ""))
        return SanitizedUrlResult(
            cleaned_url=cleaned,
            is_valid=True,
            is_playlist=True,
            is_music_youtube=is_music,
            playlist_id=playlist_id,
        )

    if is_mixed:
        if keep_playlist is True:
            qs = urlencode({"list": playlist_id})
            cleaned = urlunparse(("https", base_host, "/playlist", "", qs, ""))
            return SanitizedUrlResult(
                cleaned_url=cleaned,
                is_valid=True,
                is_playlist=True,
                is_mixed_video_and_playlist=True,
                is_music_youtube=is_music,
                video_id=video_id,
                playlist_id=playlist_id,
            )
        # Se keep_playlist é False ou None (padrão video, mas sinaliza mixed para a UI)
        qs = urlencode({"v": video_id})
        cleaned = urlunparse(("https", base_host, "/watch", "", qs, ""))
        return SanitizedUrlResult(
            cleaned_url=cleaned,
            is_valid=True,
            is_playlist=False,
            is_mixed_video_and_playlist=True,
            is_music_youtube=is_music,
            video_id=video_id,
            playlist_id=playlist_id,
        )

    if video_id:
        qs = urlencode({"v": video_id})
        cleaned = urlunparse(("https", base_host, "/watch", "", qs, ""))
        return SanitizedUrlResult(
            cleaned_url=cleaned,
            is_valid=True,
            is_music_youtube=is_music,
            video_id=video_id,
        )

    return SanitizedUrlResult(
        cleaned_url="",
        is_valid=False,
        error="Não foi possível identificar o ID do vídeo ou playlist na URL.",
    )
