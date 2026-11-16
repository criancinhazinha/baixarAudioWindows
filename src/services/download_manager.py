from __future__ import annotations

import shutil
import subprocess
import threading
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from src.core.filename_utils import clamp_output_path, resolve_unique_path, sanitize_windows_filename
from src.core.progress_parser import parse_ytdlp_line
from src.core.ytdlp_builder import build_download_command, build_remux_opus_command
from src.models.app_settings import AppSettings, ExistingFilePolicy
from src.models.audio_profile import AudioProfile
from src.models.download_task import DownloadTask, TaskStatus
from src.services.binary_manager import BinaryStatus
from src.services.settings_store import SettingsStore
from src.services.subprocess_utils import terminate_process_tree, windows_subprocess_kwargs


class _DownloadSignals(QObject):
    progress = Signal(str)  # task_id
    log = Signal(str, str)  # task_id, line
    command = Signal(str, str)  # task_id, masked_cmd
    finished = Signal(str)  # task_id


class _DownloadWorker(QRunnable):
    def __init__(
        self,
        task: DownloadTask,
        settings: AppSettings,
        binaries: BinaryStatus,
        manager: DownloadManager,
    ) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self.task = task
        self.settings = settings
        self.binaries = binaries
        self.manager = manager
        self.signals = _DownloadSignals()
        self._cancel_event = threading.Event()
        self._proc: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    def cancel(self) -> None:
        self._cancel_event.set()
        with self._lock:
            terminate_process_tree(self._proc)

    def run(self) -> None:
        task = self.task
        staging_dir: Path | None = None
        try:
            if self._cancel_event.is_set():
                task.status = TaskStatus.CANCELLED
                return

            if not self.binaries.ytdlp_path:
                raise RuntimeError("yt-dlp.exe não encontrado. Baixe as dependências primeiro.")

            final_out_dir = Path(self.settings.output_dir)
            final_out_dir.mkdir(parents=True, exist_ok=True)

            use_staging = self.settings.existing_file_policy != ExistingFilePolicy.SKIP or (
                task.remux_webm_to_opus and task.profile == AudioProfile.RAW_OPUS_OR_BEST
            )
            if use_staging:
                staging_dir = final_out_dir / ".sonicfetch_tmp" / task.task_id
                staging_dir.mkdir(parents=True, exist_ok=True)
                work_dir = staging_dir
            else:
                work_dir = final_out_dir

            task.status = TaskStatus.ANALYZING
            self.signals.progress.emit(task.task_id)

            cmd = build_download_command(
                str(self.binaries.ytdlp_path),
                task.url,
                task.profile,
                self.settings,
                selected_format_id=task.selected_format_id,
                force_wav_44100_16bit=task.force_wav_44100_16bit,
                ffmpeg_location=self.binaries.ffmpeg_dir,
                output_dir_override=str(work_dir),
            )
            task.command_preview = cmd.masked_preview
            self.signals.command.emit(task.task_id, cmd.masked_preview)
            self.signals.log.emit(task.task_id, f"$ {cmd.masked_preview}")

            printed_filepath: str | None = None
            last_dest_path: str | None = None

            proc = subprocess.Popen(
                cmd.full_argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                **windows_subprocess_kwargs(),
            )
            with self._lock:
                self._proc = proc

            assert proc.stdout is not None
            error_tail: list[str] = []

            for raw_line in proc.stdout:
                if self._cancel_event.is_set():
                    break
                line = raw_line.rstrip("\r\n")
                if not line:
                    continue
                self.signals.log.emit(task.task_id, line)
                error_tail.append(line)
                if len(error_tail) > 12:
                    error_tail.pop(0)

                event = parse_ytdlp_line(line)
                if event is not None:
                    if event.kind == "format_id" and event.format_id:
                        task.active_format_id = event.format_id
                    elif event.kind == "destination" and event.path:
                        last_dest_path = event.path
                        if task.status == TaskStatus.ANALYZING:
                            task.status = TaskStatus.DOWNLOADING
                    elif event.kind == "extract_audio" and event.path:
                        last_dest_path = event.path
                        if task.profile == AudioProfile.WAV_NATIVE:
                            task.status = TaskStatus.CONVERTING_WAV
                        else:
                            task.status = TaskStatus.FINALIZING
                    elif event.kind == "postprocess":
                        if task.profile == AudioProfile.WAV_NATIVE:
                            task.status = TaskStatus.CONVERTING_WAV
                        else:
                            task.status = TaskStatus.FINALIZING
                    elif event.kind == "progress":
                        if task.status == TaskStatus.ANALYZING:
                            task.status = TaskStatus.DOWNLOADING
                        if event.percent is not None:
                            task.progress_percent = event.percent
                        if event.speed_text:
                            task.speed_text = event.speed_text
                        if event.eta_text:
                            task.eta_text = event.eta_text
                        if event.total_text:
                            task.total_text = event.total_text
                    elif event.kind == "already_downloaded" and event.path:
                        last_dest_path = event.path
                        task.progress_percent = 100.0
                    self.signals.progress.emit(task.task_id)
                else:
                    # --print after_move:filepath imprime o caminho final como linha simples
                    candidate = Path(line.strip())
                    if candidate.is_absolute() and candidate.exists():
                        printed_filepath = str(candidate)

            rc = proc.wait()
            with self._lock:
                self._proc = None

            if self._cancel_event.is_set():
                task.status = TaskStatus.CANCELLED
                self._cleanup_staging(staging_dir, last_dest_path)
                return

            if rc != 0:
                detail = next((l for l in reversed(error_tail) if "ERROR:" in l), "")
                raise RuntimeError(detail or f"yt-dlp encerrou com código {rc}.")

            produced_path_str = printed_filepath or last_dest_path
            if not produced_path_str:
                produced = self._find_produced_audio(work_dir)
                produced_path_str = str(produced) if produced else None

            if not produced_path_str or not Path(produced_path_str).exists():
                raise RuntimeError("Download concluído, mas o arquivo final não foi localizado.")

            produced_path = Path(produced_path_str)

            # Remux opcional sem perda (.webm -> .opus)
            if (
                task.remux_webm_to_opus
                and task.profile == AudioProfile.RAW_OPUS_OR_BEST
                and produced_path.suffix.lower() == ".webm"
                and self.binaries.ffmpeg_path
            ):
                task.status = TaskStatus.REMUXING
                self.signals.progress.emit(task.task_id)
                remuxed = produced_path.with_suffix(".opus")
                remux_cmd = build_remux_opus_command(
                    str(self.binaries.ffmpeg_path),
                    produced_path,
                    remuxed,
                )
                self.signals.log.emit(task.task_id, f"$ {' '.join(remux_cmd)}")
                rproc = subprocess.run(
                    remux_cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=120,
                    **windows_subprocess_kwargs(),
                )
                if rproc.returncode == 0 and remuxed.exists():
                    produced_path.unlink(missing_ok=True)
                    produced_path = remuxed
                else:
                    self.signals.log.emit(
                        task.task_id,
                        f"Aviso: remux para .opus falhou, mantendo {produced_path.name}",
                    )

            task.status = TaskStatus.FINALIZING
            self.signals.progress.emit(task.task_id)

            final_path = self._finalize_output(produced_path, final_out_dir, staging_dir)
            task.output_path = str(final_path)
            task.progress_percent = 100.0
            task.eta_text = "00:00"
            task.status = TaskStatus.COMPLETED
        except Exception as exc:
            if self._cancel_event.is_set():
                task.status = TaskStatus.CANCELLED
            else:
                task.status = TaskStatus.ERROR
                task.error_message = str(exc)
                self.signals.log.emit(task.task_id, f"ERRO: {exc}")
            self._cleanup_staging(staging_dir, None)
        finally:
            self._remove_empty_staging(staging_dir)
            self.signals.progress.emit(task.task_id)
            self.signals.finished.emit(task.task_id)

    def _find_produced_audio(self, directory: Path) -> Path | None:
        if not directory.exists():
            return None
        candidates = [
            p
            for p in directory.iterdir()
            if p.is_file() and not p.name.endswith((".part", ".ytdl", ".json", ".tmp"))
        ]
        return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None

    def _finalize_output(
        self,
        produced_path: Path,
        final_out_dir: Path,
        staging_dir: Path | None,
    ) -> Path:
        if staging_dir is None or produced_path.parent != staging_dir:
            return produced_path

        safe_name = sanitize_windows_filename(produced_path.stem) + produced_path.suffix
        target = clamp_output_path(final_out_dir, safe_name)

        policy = self.settings.existing_file_policy
        if target.exists():
            if policy == ExistingFilePolicy.RENAME:
                target = resolve_unique_path(target)
            elif policy == ExistingFilePolicy.OVERWRITE:
                target.unlink(missing_ok=True)
            elif policy == ExistingFilePolicy.SKIP:
                produced_path.unlink(missing_ok=True)
                return target

        shutil.move(str(produced_path), str(target))

        # Move eventuais arquivos sidecar .info.json para o destino final
        for sidecar in staging_dir.glob("*.info.json"):
            sidecar_target = target.with_suffix(".info.json")
            if sidecar_target.exists() and policy == ExistingFilePolicy.RENAME:
                sidecar_target = resolve_unique_path(sidecar_target)
            shutil.move(str(sidecar), str(sidecar_target))

        return target

    @staticmethod
    def _cleanup_staging(staging_dir: Path | None, last_dest: str | None) -> None:
        if staging_dir and staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
        if last_dest:
            p = Path(last_dest)
            for suffix in (".part", ".ytdl"):
                orphan = Path(str(p) + suffix)
                orphan.unlink(missing_ok=True)

    @staticmethod
    def _remove_empty_staging(staging_dir: Path | None) -> None:
        if staging_dir and staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
        if staging_dir and staging_dir.parent.name == ".sonicfetch_tmp":
            try:
                if not any(staging_dir.parent.iterdir()):
                    staging_dir.parent.rmdir()
            except OSError:
                pass


class DownloadManager(QObject):
    """Gerencia a fila assíncrona de downloads com limite configurável de concorrência."""

    task_added = Signal(str)
    task_updated = Signal(str)
    log_received = Signal(str, str)
    command_started = Signal(str, str)
    queue_changed = Signal()

    def __init__(self, settings_store: SettingsStore | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._store = settings_store or SettingsStore()
        self._pool = QThreadPool(self)
        self._tasks: list[DownloadTask] = []
        self._tasks_by_id: dict[str, DownloadTask] = {}
        self._active_workers: dict[str, _DownloadWorker] = {}
        self._settings = self._store.load_settings()
        self._binaries = BinaryStatus(None, None, None)

    @property
    def tasks(self) -> list[DownloadTask]:
        return list(self._tasks)

    def get_task(self, task_id: str) -> DownloadTask | None:
        return self._tasks_by_id.get(task_id)

    def update_context(self, settings: AppSettings, binaries: BinaryStatus) -> None:
        self._settings = settings
        self._binaries = binaries
        self._dispatch_pending()

    def enqueue(self, task: DownloadTask) -> DownloadTask:
        self._tasks.insert(0, task)
        self._tasks_by_id[task.task_id] = task
        self.task_added.emit(task.task_id)
        self.queue_changed.emit()
        self._dispatch_pending()
        return task

    def retry_task(self, task_id: str) -> None:
        task = self._tasks_by_id.get(task_id)
        if not task or task.status.is_active:
            return
        task.status = TaskStatus.QUEUED
        task.progress_percent = 0.0
        task.speed_text = "—"
        task.eta_text = "—"
        task.error_message = ""
        self.task_updated.emit(task_id)
        self.queue_changed.emit()
        self._dispatch_pending()

    def cancel_task(self, task_id: str) -> None:
        task = self._tasks_by_id.get(task_id)
        if not task:
            return
        worker = self._active_workers.get(task_id)
        if worker:
            worker.cancel()
        elif task.status == TaskStatus.QUEUED:
            task.status = TaskStatus.CANCELLED
            self.task_updated.emit(task_id)
            self.queue_changed.emit()

    def cancel_all(self) -> None:
        for task in list(self._tasks):
            if not task.status.is_terminal:
                self.cancel_task(task.task_id)

    def remove_completed(self) -> None:
        to_remove = [t.task_id for t in self._tasks if t.status.is_terminal]
        if not to_remove:
            return
        self._tasks = [t for t in self._tasks if t.task_id not in to_remove]
        for tid in to_remove:
            self._tasks_by_id.pop(tid, None)
        self.queue_changed.emit()

    def remove_task(self, task_id: str) -> None:
        task = self._tasks_by_id.get(task_id)
        if not task:
            return
        if task.status.is_active:
            self.cancel_task(task_id)
        self._tasks = [t for t in self._tasks if t.task_id != task_id]
        self._tasks_by_id.pop(task_id, None)
        self.queue_changed.emit()

    def _dispatch_pending(self) -> None:
        max_conc = self._settings.normalized_concurrency()
        queued = [t for t in reversed(self._tasks) if t.status == TaskStatus.QUEUED]
        for task in queued:
            if len(self._active_workers) >= max_conc:
                break
            worker = _DownloadWorker(task, self._settings, self._binaries, self)
            worker.signals.progress.connect(self._on_worker_progress)
            worker.signals.log.connect(self.log_received)
            worker.signals.command.connect(self.command_started)
            worker.signals.finished.connect(self._on_worker_finished)
            self._active_workers[task.task_id] = worker
            self._pool.start(worker)

    def _on_worker_progress(self, task_id: str) -> None:
        self.task_updated.emit(task_id)

    def _on_worker_finished(self, task_id: str) -> None:
        self._active_workers.pop(task_id, None)
        task = self._tasks_by_id.get(task_id)
        if task and task.status == TaskStatus.COMPLETED:
            self._store.append_history(task)
        self.task_updated.emit(task_id)
        self.queue_changed.emit()
        self._dispatch_pending()
