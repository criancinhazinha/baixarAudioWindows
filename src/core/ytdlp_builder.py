from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.models.app_settings import AppSettings, CookieSource, ExistingFilePolicy
from src.models.audio_profile import AudioProfile


@dataclass(frozen=True)
class YtdlpCommand:
    executable: str
    args: list[str]
    format_selector: str
    masked_preview: str

    @property
    def full_argv(self) -> list[str]:
        return [self.executable, *self.args]


def _cookie_args(settings: AppSettings) -> tuple[list[str], list[str]]:
    """Retorna (args_reais, args_mascarados) para autenticação por cookies."""
    if settings.cookie_source == CookieSource.BROWSER and settings.cookie_browser:
        return (
            ["--cookies-from-browser", settings.cookie_browser],
            ["--cookies-from-browser", settings.cookie_browser],
        )
    if settings.cookie_source == CookieSource.FILE and settings.cookie_file_path:
        return (
            ["--cookies", settings.cookie_file_path],
            ["--cookies", "<cookies.txt>"],
        )
    return [], []


def _format_selector_for_profile(
    profile: AudioProfile,
    selected_format_id: str | None,
) -> str:
    if selected_format_id:
        return selected_format_id.strip()
    if profile == AudioProfile.RAW_M4A:
        return "bestaudio[ext=m4a]/bestaudio[acodec^=mp4a]/bestaudio"
    return "bestaudio[acodec=opus]/bestaudio[ext=m4a]/bestaudio"


def _mask_command_for_log(executable: str, args: list[str], cookie_file: str) -> str:
    masked: list[str] = [Path(executable).name]
    skip_mask_next = False
    for arg in args:
        if skip_mask_next:
            masked.append('"<cookies.txt>"')
            skip_mask_next = False
            continue
        if arg == "--cookies" and cookie_file:
            masked.append(arg)
            skip_mask_next = True
            continue
        if " " in arg or "\\" in arg:
            masked.append(f'"{arg}"')
        else:
            masked.append(arg)
    return " ".join(masked)


def build_download_command(
    ytdlp_exe: str,
    url: str,
    profile: AudioProfile,
    settings: AppSettings,
    *,
    selected_format_id: str | None = None,
    force_wav_44100_16bit: bool | None = None,
    ffmpeg_location: str | None = None,
    output_dir_override: str | None = None,
    template_override: str | None = None,
) -> YtdlpCommand:
    """Constrói os argumentos CLI do yt-dlp respeitando estritamente os perfis UVR5.

    Regra crítica do PRD (FR-03):
    - Perfis Brutos (RAW_OPUS_OR_BEST, RAW_M4A) NUNCA emitem `-x`, `--audio-format`,
      `-ar`, `-ac` ou `-b:a`.
    - Perfil WAV_NATIVE NUNCA injeta `-ar 44100` por padrão.
    """
    fmt_selector = _format_selector_for_profile(profile, selected_format_id)
    out_dir = Path(output_dir_override or settings.output_dir)
    template = template_override or settings.filename_template or "%(uploader)s - %(title)s [%(format_id)s].%(ext)s"
    output_pattern = str(out_dir / template)

    args: list[str] = [
        "--newline",
        "--progress",
        "--no-color",
        "--no-playlist",
        "--windows-filenames",
        "--encoding",
        "utf-8",
        "-f",
        fmt_selector,
    ]

    if ffmpeg_location:
        args.extend(["--ffmpeg-location", ffmpeg_location])

    cookie_real, _ = _cookie_args(settings)
    args.extend(cookie_real)

    # Política de arquivo existente
    if settings.existing_file_policy == ExistingFilePolicy.SKIP:
        args.append("--no-overwrites")
    elif settings.existing_file_policy == ExistingFilePolicy.OVERWRITE:
        args.append("--force-overwrites")
    else:
        # RENAME é garantido antes/pelo caminho único ou --no-overwrites + renomeação segura
        args.append("--no-overwrites")

    # Regras por perfil
    if profile in (AudioProfile.RAW_OPUS_OR_BEST, AudioProfile.RAW_M4A):
        # Zero transcodificação: não emite -x nem filtros de áudio.
        if settings.embed_metadata:
            args.append("--embed-metadata")
    elif profile == AudioProfile.WAV_NATIVE:
        args.extend(["-x", "--audio-format", "wav"])
        use_44100 = (
            force_wav_44100_16bit
            if force_wav_44100_16bit is not None
            else settings.force_wav_44100_16bit
        )
        if use_44100:
            args.extend(["--postprocessor-args", "ffmpeg:-ar 44100 -sample_fmt s16"])
        if settings.embed_metadata:
            args.append("--embed-metadata")
    elif profile == AudioProfile.MP3_LEGACY:
        args.extend(["-x", "--audio-format", "mp3", "--audio-quality", "320K"])
        if settings.embed_metadata:
            args.append("--embed-metadata")

    if settings.write_info_json:
        args.append("--write-info-json")

    args.extend(["-o", output_pattern, "--print", "after_move:filepath", url])

    preview = _mask_command_for_log(ytdlp_exe, args, settings.cookie_file_path)
    return YtdlpCommand(
        executable=ytdlp_exe,
        args=args,
        format_selector=fmt_selector,
        masked_preview=preview,
    )


def build_inspect_command(
    ytdlp_exe: str,
    url: str,
    settings: AppSettings,
    *,
    flat_playlist: bool = True,
) -> YtdlpCommand:
    """Constrói comando --dump-single-json para inspecionar streams sem baixar."""
    args: list[str] = [
        "--dump-single-json",
        "--no-warnings",
        "--no-color",
        "--encoding",
        "utf-8",
    ]
    if flat_playlist:
        args.append("--flat-playlist")
    cookie_real, _ = _cookie_args(settings)
    args.extend(cookie_real)
    args.append(url)
    preview = _mask_command_for_log(ytdlp_exe, args, settings.cookie_file_path)
    return YtdlpCommand(
        executable=ytdlp_exe,
        args=args,
        format_selector="",
        masked_preview=preview,
    )


def build_topic_search_command(
    ytdlp_exe: str,
    query: str,
    settings: AppSettings,
    *,
    limit: int = 5,
) -> YtdlpCommand:
    """Constrói comando de busca rápida de versões '- Topic'."""
    search_expr = f"ytsearch{limit}:{query} topic"
    args: list[str] = [
        "--dump-json",
        "--flat-playlist",
        "--no-warnings",
        "--no-color",
        "--encoding",
        "utf-8",
    ]
    cookie_real, _ = _cookie_args(settings)
    args.extend(cookie_real)
    args.append(search_expr)
    preview = _mask_command_for_log(ytdlp_exe, args, settings.cookie_file_path)
    return YtdlpCommand(
        executable=ytdlp_exe,
        args=args,
        format_selector="",
        masked_preview=preview,
    )


def build_remux_opus_command(
    ffmpeg_exe: str,
    input_path: Path,
    output_path: Path,
) -> list[str]:
    """Remuxa .webm (Opus) -> .opus sem recodificar (-c:a copy)."""
    return [
        ffmpeg_exe,
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-c:a",
        "copy",
        str(output_path),
    ]


def build_ffprobe_command(ffprobe_exe: str, file_path: Path) -> list[str]:
    """Inspeciona codec, sample rate, canais e bitrate reais do arquivo salvo."""
    return [
        ffprobe_exe,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]
