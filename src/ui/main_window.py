from __future__ import annotations

import traceback
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QEvent, QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from src.core.filename_utils import clean_title_for_topic_search, sanitize_youtube_url
from src.models.app_settings import AppSettings, CookieSource
from src.models.download_task import DownloadTask
from src.models.video_metadata import VideoMetadata
from src.services.binary_manager import BinaryManager, BinaryStatus, UpdateResult
from src.services.download_manager import DownloadManager
from src.services.inspector_service import FfprobeReport, InspectorService
from src.services.settings_store import SettingsStore
from src.services.topic_search_service import TopicSearchService
from src.ui.widgets.download_queue import DownloadQueueWidget
from src.ui.widgets.log_console import LogConsoleWidget
from src.ui.widgets.playlist_dialog import PlaylistDialog
from src.ui.widgets.preview_panel import PreviewPanel
from src.ui.widgets.profile_selector import ProfileSelector
from src.ui.widgets.settings_dialog import SettingsDialog
from src.ui.widgets.topic_search_dialog import TopicSearchDialog
from src.ui.widgets.url_input_bar import UrlInputBar


class _TaskSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(str, float)


class _SimpleRunnable(QRunnable):
    def __init__(self, fn: Callable[[Callable[[str, float], None]], Any]) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self._fn = fn
        self.signals = _TaskSignals()

    def run(self) -> None:
        try:
            result = self._fn(lambda msg, pct: self.signals.progress.emit(msg, pct))
            self.signals.finished.emit(result)
        except Exception as exc:
            self.signals.failed.emit(f"{exc}\n{traceback.format_exc(limit=2)}")


class MainWindow(QMainWindow):
    """Janela principal do SonicFetch Desktop (Extrator UVR5 para Windows)."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SonicFetch Desktop — Extrator de Áudio UVR5 (Bit-Exact)")
        self.setMinimumSize(960, 640)
        self.resize(1160, 840)

        self._pool = QThreadPool(self)
        self._store = SettingsStore()
        self._settings: AppSettings = self._store.load_settings()
        self._binary_manager = BinaryManager()
        self._inspector = InspectorService()
        self._topic_search = TopicSearchService()
        self._download_manager = DownloadManager(self._store, self)

        self._binaries: BinaryStatus = BinaryStatus(None, None, None)
        self._current_metadata: VideoMetadata | None = None
        self._last_clipboard_seen: str = ""
        self._active_settings_dialog: SettingsDialog | None = None
        self._keep_workers: list[QObject] = []

        self._build_ui()
        self._connect_signals()
        self.profile_selector.apply_settings(self._settings)
        self._refresh_binaries(include_versions=True)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(14, 12, 14, 10)
        root.setSpacing(10)

        # Cabeçalho compacto com status dos binários e cookies
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        app_title = QLabel("SonicFetch Desktop")
        app_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #F0F6FC;")
        app_sub = QLabel("Extração bit-exact (Opus 251/774 • AAC 140/141 • WAV nativo) para Ultimate Vocal Remover 5")
        app_sub.setObjectName("MutedLabel")
        title_box.addWidget(app_title)
        title_box.addWidget(app_sub)

        self.lbl_bin_pill = QLabel("Verificando binários...")
        self.lbl_bin_pill.setObjectName("BadgeStandard")
        self.lbl_cookie_pill = QLabel("Cookies: Desativado")
        self.lbl_cookie_pill.setObjectName("BadgeStandard")

        header.addLayout(title_box, stretch=1)
        header.addWidget(self.lbl_cookie_pill)
        header.addWidget(self.lbl_bin_pill)
        root.addLayout(header)

        # Banner de dependências ausentes (FR-09)
        self.deps_banner = QFrame()
        self.deps_banner.setObjectName("BannerWarning")
        self.deps_banner.setVisible(False)
        banner_lay = QHBoxLayout(self.deps_banner)
        banner_lay.setContentsMargins(12, 10, 12, 10)
        banner_lay.setSpacing(12)

        self.lbl_deps_msg = QLabel(
            "yt-dlp.exe ou ffmpeg.exe/ffprobe.exe não foram encontrados. "
            "Clique ao lado para baixar automaticamente para a pasta local ./bin/."
        )
        self.lbl_deps_msg.setWordWrap(True)
        self.deps_progress = QProgressBar()
        self.deps_progress.setRange(0, 100)
        self.deps_progress.setMaximumWidth(180)
        self.deps_progress.setVisible(False)

        self.btn_download_deps = QPushButton("Baixar Dependências Automaticamente")
        self.btn_download_deps.setObjectName("PrimaryButton")
        self.btn_download_deps.clicked.connect(self._start_download_dependencies)

        banner_lay.addWidget(self.lbl_deps_msg, stretch=1)
        banner_lay.addWidget(self.deps_progress)
        banner_lay.addWidget(self.btn_download_deps)
        root.addWidget(self.deps_banner)

        # Barra de URL
        self.url_bar = UrlInputBar()
        root.addWidget(self.url_bar)

        # Área central dividida verticalmente: Preview + Perfis | Fila | Console
        splitter = QSplitter(Qt.Orientation.Vertical)

        top_area = QWidget()
        top_layout = QHBoxLayout(top_area)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)

        self.preview_panel = PreviewPanel()
        self.profile_selector = ProfileSelector()
        self.profile_selector.setMinimumWidth(330)
        self.profile_selector.setMaximumWidth(400)

        top_layout.addWidget(self.preview_panel, stretch=3)
        top_layout.addWidget(self.profile_selector, stretch=1)

        self.queue_widget = DownloadQueueWidget(self._download_manager)
        self.log_console = LogConsoleWidget()

        splitter.addWidget(top_area)
        splitter.addWidget(self.queue_widget)
        splitter.addWidget(self.log_console)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 1)
        root.addWidget(splitter, stretch=1)

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Pronto.")

    def _connect_signals(self) -> None:
        self.url_bar.analyze_requested.connect(self._on_analyze_requested)
        self.url_bar.settings_requested.connect(self._open_settings)
        self.profile_selector.profile_changed.connect(self._on_profile_changed)
        self.preview_panel.search_topic_requested.connect(self._on_search_topic_requested)
        self.preview_panel.enqueue_requested.connect(self._on_enqueue_current)
        self.queue_widget.ffprobe_requested.connect(self._run_ffprobe)
        self.queue_widget.status_message.connect(lambda m: self._status_bar.showMessage(m, 5000))
        self.log_console.ffprobe_file_requested.connect(self._run_ffprobe)

        self._download_manager.log_received.connect(
            lambda tid, line: self.log_console.append_line(f"[{tid[:6]}] {line}")
        )
        self._download_manager.command_started.connect(
            lambda _tid, cmd: self.log_console.set_last_command(cmd)
        )

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.WindowActivate and self._settings.clipboard_monitor:
            clip = QApplication.clipboard().text().strip()
            if clip and clip != self._last_clipboard_seen and clip.startswith("http"):
                res = sanitize_youtube_url(clip)
                if res.is_valid and not res.is_search_query:
                    self._last_clipboard_seen = clip
                    self.url_bar.set_url(clip)
                    self.url_bar.set_hint("URL detectada da área de transferência.")
        super().changeEvent(event)

    def closeEvent(self, event) -> None:
        active = any(t.status.is_active for t in self._download_manager.tasks)
        if active:
            ans = QMessageBox.question(
                self,
                "Downloads em andamento",
                "Existem downloads ativos. Deseja cancelar todos e sair?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._download_manager.cancel_all()
        self.queue_widget.stop_audio()
        super().closeEvent(event)

    def _refresh_binaries(self, include_versions: bool = True) -> None:
        self._binaries = self._binary_manager.inspect_status(include_versions=include_versions)
        self._download_manager.update_context(self._settings, self._binaries)

        if self._binaries.all_ready:
            self.deps_banner.setVisible(False)
            yt_v = self._binaries.ytdlp_version or "ok"
            ff_v = self._binaries.ffmpeg_version or "ok"
            self.lbl_bin_pill.setText(f"yt-dlp {yt_v}  •  ffmpeg {ff_v}")
            self.lbl_bin_pill.setObjectName("BadgeMaster")
        else:
            missing = []
            if not self._binaries.ytdlp_path:
                missing.append("yt-dlp.exe")
            if not self._binaries.ffmpeg_path:
                missing.append("ffmpeg.exe")
            if not self._binaries.ffprobe_path:
                missing.append("ffprobe.exe")
            self.lbl_deps_msg.setText(
                f"Dependências ausentes ({', '.join(missing)}). "
                "Clique ao lado para baixar automaticamente sem precisar configurar PATH."
            )
            self.deps_banner.setVisible(True)
            self.lbl_bin_pill.setText(f"Faltando: {', '.join(missing)}")
            self.lbl_bin_pill.setObjectName("BadgePremium")

        self.lbl_bin_pill.style().unpolish(self.lbl_bin_pill)
        self.lbl_bin_pill.style().polish(self.lbl_bin_pill)
        self._update_cookie_badge()

        if self._active_settings_dialog is not None:
            self._active_settings_dialog.refresh_binary_status(self._binaries)

    def _update_cookie_badge(self) -> None:
        if self._settings.cookie_source == CookieSource.BROWSER:
            self.lbl_cookie_pill.setText(f"Cookies: {self._settings.cookie_browser.capitalize()}")
            self.lbl_cookie_pill.setObjectName("BadgeMaster")
        elif self._settings.cookie_source == CookieSource.FILE and self._settings.cookie_file_path:
            self.lbl_cookie_pill.setText("Cookies: cookies.txt")
            self.lbl_cookie_pill.setObjectName("BadgeMaster")
        else:
            self.lbl_cookie_pill.setText("Cookies: Desativado")
            self.lbl_cookie_pill.setObjectName("BadgeStandard")
        self.lbl_cookie_pill.style().unpolish(self.lbl_cookie_pill)
        self.lbl_cookie_pill.style().polish(self.lbl_cookie_pill)

    def _run_bg(
        self,
        fn: Callable[[Callable[[str, float], None]], Any],
        on_done: Callable[[Any], None],
        on_err: Callable[[str], None],
        on_progress: Callable[[str, float], None] | None = None,
    ) -> None:
        runnable = _SimpleRunnable(fn)
        signals = runnable.signals
        self._keep_workers.append(signals)

        def _cleanup() -> None:
            if signals in self._keep_workers:
                self._keep_workers.remove(signals)

        signals.finished.connect(lambda res: (_cleanup(), on_done(res)))
        signals.failed.connect(lambda err: (_cleanup(), on_err(err)))
        if on_progress:
            signals.progress.connect(on_progress)
        self._pool.start(runnable)

    def _start_download_dependencies(self) -> None:
        self.btn_download_deps.setEnabled(False)
        self.deps_progress.setVisible(True)
        self.deps_progress.setValue(0)
        self.log_console.append_line("[Dependências] Iniciando download automático de yt-dlp.exe e FFmpeg...")

        def _job(progress_cb: Callable[[str, float], None]) -> BinaryStatus:
            return self._binary_manager.download_dependencies(progress_cb=progress_cb)

        def _on_prog(msg: str, pct: float) -> None:
            self.lbl_deps_msg.setText(msg)
            self.deps_progress.setValue(int(pct))
            self._status_bar.showMessage(msg)

        def _on_done(_status: BinaryStatus) -> None:
            self.btn_download_deps.setEnabled(True)
            self.deps_progress.setVisible(False)
            self._refresh_binaries(include_versions=True)
            self.log_console.append_line("[Dependências] Binários instalados com sucesso.")
            self._status_bar.showMessage("Dependências instaladas e prontas!", 6000)

        def _on_err(err: str) -> None:
            self.btn_download_deps.setEnabled(True)
            self.deps_progress.setVisible(False)
            self.lbl_deps_msg.setText("Erro ao baixar dependências. Verifique sua conexão.")
            self.log_console.append_line(f"[Dependências] ERRO: {err}")
            QMessageBox.critical(self, "Erro ao Baixar Dependências", err.splitlines()[0])

        self._run_bg(_job, _on_done, _on_err, _on_prog)

    def _on_analyze_requested(self, raw_input: str) -> None:
        if not self._binaries.ytdlp_path:
            QMessageBox.warning(
                self,
                "yt-dlp.exe não encontrado",
                "Baixe as dependências primeiro clicando em 'Baixar Dependências Automaticamente'.",
            )
            return

        pref = self._settings.preferred_mixed_url_mode
        keep_pl: bool | None = None
        if pref == "playlist":
            keep_pl = True
        elif pref == "video":
            keep_pl = False

        sanitized = sanitize_youtube_url(raw_input, keep_playlist=keep_pl)
        if not sanitized.is_valid:
            QMessageBox.warning(self, "URL Inválida", sanitized.error or "URL inválida.")
            return

        if sanitized.is_mixed_video_and_playlist and pref == "ask":
            box = QMessageBox(self)
            box.setWindowTitle("URL Mista Detectada")
            box.setText("Este link aponta para um vídeo dentro de uma playlist.")
            box.setInformativeText("Como deseja analisar este link?")
            btn_vid = box.addButton("Apenas este vídeo", QMessageBox.ButtonRole.AcceptRole)
            btn_pl = box.addButton("Playlist inteira", QMessageBox.ButtonRole.ActionRole)
            box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            clicked = box.clickedButton()
            if clicked == btn_pl:
                sanitized = sanitize_youtube_url(raw_input, keep_playlist=True)
            elif clicked == btn_vid:
                sanitized = sanitize_youtube_url(raw_input, keep_playlist=False)
            else:
                return

        self.url_bar.set_hint(f"URL limpa: {sanitized.cleaned_url}")
        self._analyze_cleaned_url(sanitized.cleaned_url)

    def _analyze_cleaned_url(self, cleaned_url: str) -> None:
        assert self._binaries.ytdlp_path is not None
        ytdlp_path = self._binaries.ytdlp_path
        settings_copy = AppSettings.from_dict(self._settings.to_dict())

        self.url_bar.set_busy(True)
        self.preview_panel.set_loading(True)
        self._status_bar.showMessage("Consultando metadados e streams disponíveis...")

        def _job(_progress: Callable[[str, float], None]) -> tuple[VideoMetadata, str, bytes | None]:
            meta, masked_cmd = self._inspector.inspect_url(ytdlp_path, cleaned_url, settings_copy)
            thumb_bytes = (
                self._inspector.fetch_thumbnail_bytes(meta.thumbnail)
                if (not meta.is_playlist and meta.thumbnail)
                else None
            )
            return meta, masked_cmd, thumb_bytes

        def _on_done(payload: tuple[VideoMetadata, str, bytes | None]) -> None:
            meta, masked_cmd, thumb_bytes = payload
            self.url_bar.set_busy(False)
            self.preview_panel.set_loading(False)
            self.log_console.set_last_command(masked_cmd)
            self.log_console.append_line(f"$ {masked_cmd}")

            if meta.is_playlist:
                self._status_bar.showMessage(
                    f"Playlist carregada: {meta.playlist_title} ({len(meta.entries)} itens).", 6000
                )
                dlg = PlaylistDialog(meta, self)
                if dlg.exec() == PlaylistDialog.DialogCode.Accepted:
                    self._enqueue_playlist_entries(dlg.selected_entries())
                return

            self._current_metadata = meta
            self.preview_panel.set_metadata(meta, self.profile_selector.current_profile())
            self.preview_panel.set_thumbnail_bytes(thumb_bytes)
            self._status_bar.showMessage(
                f"Inspeção concluída: {len(meta.streams)} streams de áudio encontrados.", 6000
            )

        def _on_err(err: str) -> None:
            self.url_bar.set_busy(False)
            self.preview_panel.set_loading(False)
            self.log_console.append_line(f"[Análise] ERRO: {err}")
            self._status_bar.showMessage("Erro ao analisar URL.", 6000)
            QMessageBox.critical(self, "Erro na Inspeção", err.splitlines()[0])

        self._run_bg(_job, _on_done, _on_err)

    def _on_profile_changed(self) -> None:
        profile = self.profile_selector.current_profile()
        self._settings.default_profile = profile
        self._settings.remux_webm_to_opus = self.profile_selector.chk_remux_opus.isChecked()
        self._settings.force_wav_44100_16bit = self.profile_selector.chk_force_44100.isChecked()
        self._store.save_settings(self._settings)
        self.preview_panel.apply_profile_selection(profile)

    def _on_enqueue_current(self) -> None:
        if not self._current_metadata:
            return
        if not self._binaries.ytdlp_path:
            QMessageBox.warning(self, "Dependências ausentes", "Baixe o yt-dlp.exe primeiro.")
            return

        profile = self.profile_selector.current_profile()
        sel_id = self.preview_panel.selected_format_id()
        sel_stream = self.preview_panel.selected_stream()

        task = DownloadTask(
            url=self._current_metadata.url,
            title=self._current_metadata.title,
            channel=self._current_metadata.display_artist,
            profile=profile,
            selected_format_id=sel_id,
            remux_webm_to_opus=self.profile_selector.remux_opus_enabled(),
            force_wav_44100_16bit=self.profile_selector.force_44100_enabled(),
            is_topic_master=self._current_metadata.is_topic_master,
            active_format_id=sel_id or "",
            active_codec=sel_stream.acodec if sel_stream else "",
            active_asr=sel_stream.asr_str if sel_stream else "",
        )
        self._download_manager.enqueue(task)
        self._status_bar.showMessage(f"Adicionado à fila: {task.title}", 5000)

    def _enqueue_playlist_entries(self, entries) -> None:
        profile = self.profile_selector.current_profile()
        remux = self.profile_selector.remux_opus_enabled()
        force_44 = self.profile_selector.force_44100_enabled()
        for idx, entry in enumerate(entries, start=1):
            if not entry.url:
                continue
            task = DownloadTask(
                url=entry.url,
                title=entry.title,
                channel=entry.channel or "YouTube",
                profile=profile,
                selected_format_id=None,
                remux_webm_to_opus=remux,
                force_wav_44100_16bit=force_44,
                is_topic_master=entry.is_topic_master,
                playlist_index=idx,
            )
            self._download_manager.enqueue(task)
        self._status_bar.showMessage(f"{len(entries)} faixa(s) adicionada(s) à fila.", 5000)

    def _on_search_topic_requested(self) -> None:
        if not self._current_metadata or not self._binaries.ytdlp_path:
            return
        ytdlp_path = self._binaries.ytdlp_path
        settings_copy = AppSettings.from_dict(self._settings.to_dict())
        query = clean_title_for_topic_search(
            self._current_metadata.title,
            self._current_metadata.display_artist,
        )
        self._status_bar.showMessage(f"Buscando versões '- Topic' para: {query}...")
        self.preview_panel.btn_find_topic.setEnabled(False)

        def _job(_progress: Callable[[str, float], None]):
            return self._topic_search.search_topic_versions(ytdlp_path, query, settings_copy)

        def _on_done(payload) -> None:
            results, masked_cmd = payload
            self.preview_panel.btn_find_topic.setEnabled(True)
            self.log_console.set_last_command(masked_cmd)
            self.log_console.append_line(f"$ {masked_cmd}")
            if not results:
                QMessageBox.information(
                    self,
                    "Busca - Topic",
                    "Nenhuma alternativa '- Topic' encontrada para esta faixa.",
                )
                return
            dlg = TopicSearchDialog(results, self)
            if dlg.exec() == TopicSearchDialog.DialogCode.Accepted and dlg.selected_url:
                self.url_bar.set_url(dlg.selected_url)
                self._analyze_cleaned_url(dlg.selected_url)

        def _on_err(err: str) -> None:
            self.preview_panel.btn_find_topic.setEnabled(True)
            self.log_console.append_line(f"[Busca Topic] ERRO: {err}")
            QMessageBox.critical(self, "Erro na Busca - Topic", err.splitlines()[0])

        self._run_bg(_job, _on_done, _on_err)

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self._settings, self._binaries, self)
        self._active_settings_dialog = dlg
        dlg.download_deps_requested.connect(self._start_download_dependencies)
        dlg.update_ytdlp_requested.connect(self._update_ytdlp_now)

        if dlg.exec() == SettingsDialog.DialogCode.Accepted:
            self._settings = dlg.build_updated_settings()
            self._store.save_settings(self._settings)
            self.profile_selector.apply_settings(self._settings)
            self._download_manager.update_context(self._settings, self._binaries)
            self._update_cookie_badge()
            self._status_bar.showMessage("Configurações salvas.", 4000)

        self._active_settings_dialog = None

    def _update_ytdlp_now(self) -> None:
        self._status_bar.showMessage("Atualizando yt-dlp.exe (-U)...")
        self.log_console.append_line("[Updater] Executando yt-dlp.exe -U...")

        def _job(_progress: Callable[[str, float], None]) -> UpdateResult:
            return self._binary_manager.update_ytdlp()

        def _on_done(res: UpdateResult) -> None:
            self._refresh_binaries(include_versions=True)
            self.log_console.append_line(f"[Updater] {res.output}")
            QMessageBox.information(
                self,
                "Atualização do yt-dlp",
                f"Versão anterior: {res.previous_version or '?'}\n"
                f"Versão atual: {res.current_version or '?'}\n\n{res.output}",
            )

        def _on_err(err: str) -> None:
            self.log_console.append_line(f"[Updater] ERRO: {err}")
            QMessageBox.critical(self, "Erro ao Atualizar yt-dlp", err.splitlines()[0])

        self._run_bg(_job, _on_done, _on_err)

    def _run_ffprobe(self, file_path_str: str) -> None:
        if not self._binaries.ffprobe_path:
            QMessageBox.warning(
                self,
                "ffprobe.exe ausente",
                "Baixe as dependências para usar a auditoria ffprobe.",
            )
            return
        ffprobe_exe = self._binaries.ffprobe_path
        target = Path(file_path_str)
        self.log_console.set_expanded(True)
        self.log_console.append_line(f"[ffprobe] Auditando: {target}")

        def _job(_progress: Callable[[str, float], None]) -> FfprobeReport:
            return self._inspector.inspect_file_ffprobe(ffprobe_exe, target)

        def _on_done(report: FfprobeReport) -> None:
            self.log_console.append_line(report.raw_summary)
            QMessageBox.information(
                self,
                "Auditoria Técnica (ffprobe)",
                f"Arquivo: {Path(report.file_path).name}\n"
                f"Contêiner: {report.format_name}\n"
                f"Codec de Áudio: {report.codec_name}\n"
                f"Sample Rate: {report.sample_rate}\n"
                f"Canais: {report.channels}\n"
                f"Bitrate: {report.bit_rate_kbps}\n"
                f"Duração: {report.duration_sec}\n"
                f"Tamanho: {report.size_mb}",
            )

        def _on_err(err: str) -> None:
            self.log_console.append_line(f"[ffprobe] ERRO: {err}")
            QMessageBox.critical(self, "Erro no ffprobe", err.splitlines()[0])

        self._run_bg(_job, _on_done, _on_err)
