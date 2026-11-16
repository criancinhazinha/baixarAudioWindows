from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.models.audio_profile import AudioProfile


class TaskStatus(str, Enum):
    QUEUED = "Na fila"
    ANALYZING = "Analisando streams"
    DOWNLOADING = "Baixando fluxo bruto"
    CONVERTING_WAV = "Convertendo p/ WAV (FFmpeg)"
    REMUXING = "Remuxando contêiner"
    FINALIZING = "Finalizando"
    COMPLETED = "Concluído"
    CANCELLED = "Cancelado"
    ERROR = "Erro"

    @property
    def is_terminal(self) -> bool:
        return self in {TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.ERROR}

    @property
    def is_active(self) -> bool:
        return self in {
            TaskStatus.ANALYZING,
            TaskStatus.DOWNLOADING,
            TaskStatus.CONVERTING_WAV,
            TaskStatus.REMUXING,
            TaskStatus.FINALIZING,
        }


@dataclass
class DownloadTask:
    url: str
    title: str
    channel: str
    profile: AudioProfile
    selected_format_id: str | None = None
    remux_webm_to_opus: bool = False
    force_wav_44100_16bit: bool = False
    is_topic_master: bool = False
    playlist_index: int | None = None
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: TaskStatus = TaskStatus.QUEUED
    progress_percent: float = 0.0
    speed_text: str = "—"
    eta_text: str = "—"
    downloaded_text: str = "—"
    total_text: str = "—"
    active_format_id: str = ""
    active_codec: str = ""
    active_asr: str = ""
    output_path: str = ""
    command_preview: str = ""
    error_message: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
