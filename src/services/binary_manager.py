from __future__ import annotations

import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx

from src.app_paths import local_bin_dir, localappdata_bin_dir, preferred_bin_dir
from src.services.subprocess_utils import windows_subprocess_kwargs

YTDLP_RELEASE_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_MIRROR_URLS: tuple[str, ...] = (
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
)


@dataclass(frozen=True)
class BinaryStatus:
    ytdlp_path: Path | None
    ffmpeg_path: Path | None
    ffprobe_path: Path | None
    ytdlp_version: str = ""
    ffmpeg_version: str = ""
    ytdlp_origin: str = "missing"  # "local", "appdata", "system", "missing"
    ffmpeg_origin: str = "missing"

    @property
    def all_ready(self) -> bool:
        return bool(self.ytdlp_path and self.ffmpeg_path and self.ffprobe_path)

    @property
    def ytdlp_ready(self) -> bool:
        return self.ytdlp_path is not None

    @property
    def ffmpeg_dir(self) -> str | None:
        if self.ffmpeg_path:
            return str(self.ffmpeg_path.parent)
        return None


@dataclass(frozen=True)
class UpdateResult:
    success: bool
    previous_version: str
    current_version: str
    output: str


class BinaryManager:
    """Detecta, baixa e atualiza yt-dlp.exe, ffmpeg.exe e ffprobe.exe sem terminal."""

    def _find_binary(self, filename: str) -> tuple[Path | None, str]:
        local_candidate = local_bin_dir() / filename
        if local_candidate.is_file():
            return local_candidate, "local"

        appdata_candidate = localappdata_bin_dir() / filename
        if appdata_candidate.is_file():
            return appdata_candidate, "appdata"

        which_hit = shutil.which(filename) or shutil.which(Path(filename).stem)
        if which_hit:
            return Path(which_hit), "system"

        return None, "missing"

    def probe_version(self, exe_path: Path | None, flag: str = "--version") -> str:
        if not exe_path or not exe_path.is_file():
            return ""
        try:
            proc = subprocess.run(
                [str(exe_path), flag],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                **windows_subprocess_kwargs(),
            )
            first_line = (proc.stdout or proc.stderr or "").strip().splitlines()
            return first_line[0].strip() if first_line else ""
        except Exception:
            return ""

    def inspect_status(self, include_versions: bool = True) -> BinaryStatus:
        ytdlp_path, ytdlp_origin = self._find_binary("yt-dlp.exe")
        ffmpeg_path, ffmpeg_origin = self._find_binary("ffmpeg.exe")
        ffprobe_path, _ = self._find_binary("ffprobe.exe")

        yt_ver = self.probe_version(ytdlp_path, "--version") if include_versions else ""
        ff_ver = self.probe_version(ffmpeg_path, "-version") if include_versions else ""
        if ff_ver.startswith("ffmpeg version "):
            ff_ver = ff_ver.replace("ffmpeg version ", "", 1).split(" ")[0]

        return BinaryStatus(
            ytdlp_path=ytdlp_path,
            ffmpeg_path=ffmpeg_path,
            ffprobe_path=ffprobe_path,
            ytdlp_version=yt_ver,
            ffmpeg_version=ff_ver,
            ytdlp_origin=ytdlp_origin,
            ffmpeg_origin=ffmpeg_origin,
        )

    def download_dependencies(
        self,
        progress_cb: Callable[[str, float], None] | None = None,
    ) -> BinaryStatus:
        """Baixa yt-dlp.exe e extrai ffmpeg.exe + ffprobe.exe para bin/."""
        target_dir = preferred_bin_dir()
        target_dir.mkdir(parents=True, exist_ok=True)

        status = self.inspect_status(include_versions=False)

        if not status.ytdlp_path:
            if progress_cb:
                progress_cb("Baixando yt-dlp.exe oficial...", 5.0)
            ytdlp_dest = target_dir / "yt-dlp.exe"
            self._download_file(
                YTDLP_RELEASE_URL,
                ytdlp_dest,
                min_bytes=1_000_000,
                progress_cb=lambda p: progress_cb(
                    f"Baixando yt-dlp.exe ({p:.0f}%)...", 5.0 + p * 0.30
                )
                if progress_cb
                else None,
            )

        if not status.ffmpeg_path or not status.ffprobe_path:
            if progress_cb:
                progress_cb("Baixando pacote FFmpeg Windows x64...", 38.0)
            self._download_and_extract_ffmpeg(target_dir, progress_cb)

        if progress_cb:
            progress_cb("Validando binários instalados...", 96.0)
        final_status = self.inspect_status(include_versions=True)
        if progress_cb:
            progress_cb("Dependências prontas.", 100.0)
        return final_status

    def _download_file(
        self,
        url: str,
        dest: Path,
        *,
        min_bytes: int = 100_000,
        progress_cb: Callable[[float], None] | None = None,
    ) -> None:
        tmp_dest = dest.with_suffix(dest.suffix + ".tmp")
        with httpx.Client(follow_redirects=True, timeout=120.0) as client:
            with client.stream("GET", url) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("Content-Length") or 0)
                downloaded = 0
                with tmp_dest.open("wb") as fh:
                    for chunk in resp.iter_bytes(chunk_size=65536):
                        if not chunk:
                            continue
                        fh.write(chunk)
                        downloaded += len(chunk)
                        if progress_cb and total > 0:
                            progress_cb(min(100.0, downloaded * 100.0 / total))

        if tmp_dest.stat().st_size < min_bytes:
            tmp_dest.unlink(missing_ok=True)
            raise RuntimeError(f"Arquivo baixado de {url} está incompleto ou corrompido.")
        tmp_dest.replace(dest)

    def _download_and_extract_ffmpeg(
        self,
        target_dir: Path,
        progress_cb: Callable[[str, float], None] | None = None,
    ) -> None:
        last_err: Exception | None = None
        with tempfile.TemporaryDirectory(prefix="sonicfetch_ffmpeg_") as tmp_dir_str:
            zip_path = Path(tmp_dir_str) / "ffmpeg.zip"
            downloaded_ok = False
            for url in FFMPEG_MIRROR_URLS:
                try:
                    self._download_file(
                        url,
                        zip_path,
                        min_bytes=10_000_000,
                        progress_cb=lambda p: progress_cb(
                            f"Baixando FFmpeg ({p:.0f}%)...", 38.0 + p * 0.45
                        )
                        if progress_cb
                        else None,
                    )
                    downloaded_ok = True
                    break
                except Exception as exc:
                    last_err = exc
                    continue

            if not downloaded_ok:
                raise RuntimeError(f"Falha ao baixar FFmpeg: {last_err}")

            if progress_cb:
                progress_cb("Extraindo ffmpeg.exe e ffprobe.exe...", 86.0)

            extracted_names: set[str] = set()
            with zipfile.ZipFile(zip_path, "r") as zf:
                for member in zf.infolist():
                    lower = member.filename.lower()
                    if lower.endswith("/ffmpeg.exe") or lower == "ffmpeg.exe":
                        self._extract_member(zf, member, target_dir / "ffmpeg.exe")
                        extracted_names.add("ffmpeg.exe")
                    elif lower.endswith("/ffprobe.exe") or lower == "ffprobe.exe":
                        self._extract_member(zf, member, target_dir / "ffprobe.exe")
                        extracted_names.add("ffprobe.exe")

            if "ffmpeg.exe" not in extracted_names or "ffprobe.exe" not in extracted_names:
                raise RuntimeError("O arquivo ZIP do FFmpeg não continha ffmpeg.exe e ffprobe.exe.")

    @staticmethod
    def _extract_member(zf: zipfile.ZipFile, member: zipfile.ZipInfo, dest: Path) -> None:
        tmp = dest.with_suffix(".tmp")
        with zf.open(member, "r") as src, tmp.open("wb") as out:
            shutil.copyfileobj(src, out)
        tmp.replace(dest)

    def update_ytdlp(self) -> UpdateResult:
        status = self.inspect_status(include_versions=True)
        if not status.ytdlp_path:
            return UpdateResult(
                success=False,
                previous_version="",
                current_version="",
                output="yt-dlp.exe não encontrado.",
            )
        prev_ver = status.ytdlp_version
        proc = subprocess.run(
            [str(status.ytdlp_path), "-U"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            **windows_subprocess_kwargs(),
        )
        out = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
        new_ver = self.probe_version(status.ytdlp_path, "--version")
        return UpdateResult(
            success=proc.returncode == 0,
            previous_version=prev_ver,
            current_version=new_ver,
            output=out,
        )
