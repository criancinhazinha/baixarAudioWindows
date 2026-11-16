from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PySide6.QtCore import QMimeData, QPoint, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QDrag
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.models.download_task import DownloadTask, TaskStatus
from src.services.download_manager import DownloadManager


class _QueueItemWidget(QFrame):
    """Card visual de cada tarefa na fila com progresso, estado e ações rápidas."""

    cancel_clicked = Signal(str)
    retry_clicked = Signal(str)
    play_clicked = Signal(str)
    explorer_clicked = Signal(str)
    copy_path_clicked = Signal(str)
    ffprobe_clicked = Signal(str)
    delete_clicked = Signal(str)

    def __init__(self, task: DownloadTask, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.task_id = task.task_id
        self.setObjectName("Card")
        self._build_ui()
        self.update_from_task(task, is_playing=False)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(8)

        self.lbl_title = QLabel("")
        self.lbl_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #F0F6FC;")

        self.lbl_drag_hint = QLabel("⇕ Arraste p/ UVR5")
        self.lbl_drag_hint.setObjectName("BadgeMaster")
        self.lbl_drag_hint.setVisible(False)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("BadgeStandard")

        top.addWidget(self.lbl_title, stretch=1)
        top.addWidget(self.lbl_drag_hint)
        top.addWidget(self.lbl_status)
        layout.addLayout(top)

        self.lbl_meta = QLabel("")
        self.lbl_meta.setObjectName("MutedLabel")
        layout.addWidget(self.lbl_meta)

        mid = QHBoxLayout()
        mid.setSpacing(10)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.lbl_stats = QLabel("0%  •  —  •  ETA —")
        self.lbl_stats.setObjectName("MutedLabel")
        mid.addWidget(self.progress, stretch=1)
        mid.addWidget(self.lbl_stats)
        layout.addLayout(mid)

        actions = QHBoxLayout()
        actions.setSpacing(6)

        self.btn_play = QPushButton("▶ Ouvir")
        self.btn_play.clicked.connect(lambda: self.play_clicked.emit(self.task_id))

        self.btn_explorer = QPushButton("Abrir no Explorer")
        self.btn_explorer.clicked.connect(lambda: self.explorer_clicked.emit(self.task_id))

        self.btn_copy = QPushButton("Copiar Caminho")
        self.btn_copy.clicked.connect(lambda: self.copy_path_clicked.emit(self.task_id))

        self.btn_ffprobe = QPushButton("ffprobe")
        self.btn_ffprobe.clicked.connect(lambda: self.ffprobe_clicked.emit(self.task_id))

        self.btn_delete = QPushButton("Excluir")
        self.btn_delete.setObjectName("DangerButton")
        self.btn_delete.clicked.connect(lambda: self.delete_clicked.emit(self.task_id))

        self.btn_retry = QPushButton("Tentar Novamente")
        self.btn_retry.clicked.connect(lambda: self.retry_clicked.emit(self.task_id))

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setObjectName("DangerButton")
        self.btn_cancel.clicked.connect(lambda: self.cancel_clicked.emit(self.task_id))

        actions.addWidget(self.btn_play)
        actions.addWidget(self.btn_explorer)
        actions.addWidget(self.btn_copy)
        actions.addWidget(self.btn_ffprobe)
        actions.addWidget(self.btn_delete)
        actions.addWidget(self.btn_retry)
        actions.addWidget(self.btn_cancel)
        actions.addStretch(1)
        layout.addLayout(actions)

    def update_from_task(self, task: DownloadTask, is_playing: bool) -> None:
        self.lbl_title.setText(task.title)
        fmt_txt = f"ID {task.active_format_id or task.selected_format_id or 'auto'}"
        self.lbl_meta.setText(f"{task.channel}  •  {task.profile.value}  •  {fmt_txt}")

        self.lbl_status.setText(task.status.value)
        if task.status == TaskStatus.COMPLETED:
            self.lbl_status.setStyleSheet(
                "background-color: #064E3B; color: #6EE7B7; border: 1px solid #10B981; "
                "border-radius: 6px; padding: 2px 8px; font-weight: 700; font-size: 11px;"
            )
        elif task.status == TaskStatus.ERROR:
            self.lbl_status.setStyleSheet(
                "background-color: #450A0A; color: #FCA5A5; border: 1px solid #EF4444; "
                "border-radius: 6px; padding: 2px 8px; font-weight: 700; font-size: 11px;"
            )
        elif task.status.is_active:
            self.lbl_status.setStyleSheet(
                "background-color: #0C4A6E; color: #7DD3FC; border: 1px solid #0EA5E9; "
                "border-radius: 6px; padding: 2px 8px; font-weight: 700; font-size: 11px;"
            )
        else:
            self.lbl_status.setStyleSheet("")

        self.progress.setValue(int(round(task.progress_percent)))
        if task.status == TaskStatus.ERROR and task.error_message:
            self.lbl_stats.setText(task.error_message[:90])
        else:
            self.lbl_stats.setText(
                f"{task.progress_percent:.1f}%  •  {task.speed_text}  •  "
                f"ETA {task.eta_text}  •  {task.total_text}"
            )

        completed_ok = task.status == TaskStatus.COMPLETED and bool(task.output_path) and Path(task.output_path).exists()
        self.lbl_drag_hint.setVisible(completed_ok)
        self.btn_play.setVisible(completed_ok)
        self.btn_play.setText("⏸ Pausar" if is_playing else "▶ Ouvir")
        self.btn_explorer.setVisible(completed_ok)
        self.btn_copy.setVisible(completed_ok)
        self.btn_ffprobe.setVisible(completed_ok)
        self.btn_delete.setVisible(completed_ok)

        self.btn_cancel.setVisible(not task.status.is_terminal)
        self.btn_retry.setVisible(task.status in {TaskStatus.ERROR, TaskStatus.CANCELLED})


class _DraggableQueueList(QListWidget):
    """QListWidget habilitado para Drag & Drop nativo de arquivos concluídos para o UVR5."""

    def __init__(self, manager: DownloadManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._manager = manager
        self._drag_start_pos: QPoint | None = None
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.setSpacing(6)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if not (event.buttons() & Qt.MouseButton.LeftButton) or self._drag_start_pos is None:
            super().mouseMoveEvent(event)
            return
        if (event.position().toPoint() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return

        item = self.itemAt(self._drag_start_pos)
        if not item:
            return
        task_id = item.data(Qt.ItemDataRole.UserRole)
        task = self._manager.get_task(task_id)
        if not task or task.status != TaskStatus.COMPLETED or not task.output_path:
            return
        path = Path(task.output_path)
        if not path.exists():
            return

        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(path))])
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)


class DownloadQueueWidget(QFrame):
    """Painel completo da fila de downloads com ações de arquivo e integração UVR5."""

    ffprobe_requested = Signal(str)  # file_path
    status_message = Signal(str)

    def __init__(self, manager: DownloadManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self._manager = manager
        self._items_by_id: dict[str, QListWidgetItem] = {}
        self._widgets_by_id: dict[str, _QueueItemWidget] = {}
        self._playing_task_id: str | None = None

        self._audio_output = QAudioOutput(self)
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio_output)
        self._player.playbackStateChanged.connect(self._on_playback_changed)

        self._build_ui()
        self._manager.task_added.connect(self._on_task_added)
        self._manager.task_updated.connect(self._on_task_updated)
        self._manager.queue_changed.connect(self._rebuild_list)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)

        hdr = QHBoxLayout()
        title = QLabel("Fila de Downloads & Extração")
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #F0F6FC;")

        hint = QLabel("Arraste itens concluídos diretamente para o UVR5 ou Explorer")
        hint.setObjectName("MutedLabel")

        self.btn_cancel_all = QPushButton("Cancelar Todos")
        self.btn_cancel_all.clicked.connect(self._manager.cancel_all)

        self.btn_clear_done = QPushButton("Limpar Concluídos")
        self.btn_clear_done.clicked.connect(self._manager.remove_completed)

        hdr.addWidget(title)
        hdr.addSpacing(8)
        hdr.addWidget(hint, stretch=1)
        hdr.addWidget(self.btn_cancel_all)
        hdr.addWidget(self.btn_clear_done)
        root.addLayout(hdr)

        self.list_widget = _DraggableQueueList(self._manager)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._open_context_menu)
        self.list_widget.setMinimumHeight(180)
        root.addWidget(self.list_widget, stretch=1)

    def _on_task_added(self, task_id: str) -> None:
        self._rebuild_list()

    def _on_task_updated(self, task_id: str) -> None:
        task = self._manager.get_task(task_id)
        widget = self._widgets_by_id.get(task_id)
        item = self._items_by_id.get(task_id)
        if task and widget and item:
            widget.update_from_task(task, is_playing=(self._playing_task_id == task_id))
            item.setSizeHint(widget.sizeHint())
        else:
            self._rebuild_list()

    def _rebuild_list(self) -> None:
        self.list_widget.clear()
        self._items_by_id.clear()
        self._widgets_by_id.clear()

        for task in self._manager.tasks:
            item = QListWidgetItem(self.list_widget)
            item.setData(Qt.ItemDataRole.UserRole, task.task_id)
            widget = _QueueItemWidget(task)
            widget.cancel_clicked.connect(self._manager.cancel_task)
            widget.retry_clicked.connect(self._manager.retry_task)
            widget.play_clicked.connect(self._toggle_play)
            widget.explorer_clicked.connect(self._open_in_explorer)
            widget.copy_path_clicked.connect(self._copy_path)
            widget.ffprobe_clicked.connect(self._request_ffprobe)
            widget.delete_clicked.connect(self._delete_file)
            widget.update_from_task(task, is_playing=(self._playing_task_id == task.task_id))

            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
            self._items_by_id[task.task_id] = item
            self._widgets_by_id[task.task_id] = widget

    def _toggle_play(self, task_id: str) -> None:
        task = self._manager.get_task(task_id)
        if not task or not task.output_path:
            return
        if self._playing_task_id == task_id and self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.stop()
            self._playing_task_id = None
            self._on_task_updated(task_id)
            return

        prev = self._playing_task_id
        self._playing_task_id = task_id
        self._player.setSource(QUrl.fromLocalFile(task.output_path))
        self._audio_output.setVolume(0.9)
        self._player.play()
        if prev:
            self._on_task_updated(prev)
        self._on_task_updated(task_id)

    def _on_playback_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.StoppedState and self._playing_task_id:
            tid = self._playing_task_id
            self._playing_task_id = None
            self._on_task_updated(tid)

    def _open_in_explorer(self, task_id: str) -> None:
        task = self._manager.get_task(task_id)
        if not task or not task.output_path:
            return
        p = Path(task.output_path)
        if os.name == "nt" and p.exists():
            subprocess.Popen(["explorer", f"/select,{p}"])

    def _copy_path(self, task_id: str) -> None:
        task = self._manager.get_task(task_id)
        if task and task.output_path:
            QApplication.clipboard().setText(task.output_path)
            self.status_message.emit(f"Caminho copiado: {task.output_path}")

    def _request_ffprobe(self, task_id: str) -> None:
        task = self._manager.get_task(task_id)
        if task and task.output_path:
            self.ffprobe_requested.emit(task.output_path)

    def _delete_file(self, task_id: str) -> None:
        task = self._manager.get_task(task_id)
        if not task or not task.output_path:
            return
        p = Path(task.output_path)
        ans = QMessageBox.question(
            self,
            "Excluir Arquivo",
            f"Deseja excluir permanentemente o arquivo?\n\n{p.name}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            if self._playing_task_id == task_id:
                self._player.stop()
            p.unlink(missing_ok=True)
            self._manager.remove_task(task_id)
            self.status_message.emit(f"Arquivo excluído: {p.name}")

    def _open_context_menu(self, pos: QPoint) -> None:
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        task_id = item.data(Qt.ItemDataRole.UserRole)
        task = self._manager.get_task(task_id)
        if not task:
            return

        menu = QMenu(self)
        if task.status == TaskStatus.COMPLETED and task.output_path:
            act_probe = QAction("Verificar arquivo com ffprobe", self)
            act_probe.triggered.connect(lambda: self._request_ffprobe(task_id))
            act_exp = QAction("Abrir no Windows Explorer", self)
            act_exp.triggered.connect(lambda: self._open_in_explorer(task_id))
            act_copy = QAction("Copiar caminho completo", self)
            act_copy.triggered.connect(lambda: self._copy_path(task_id))
            menu.addAction(act_probe)
            menu.addAction(act_exp)
            menu.addAction(act_copy)
            menu.addSeparator()

        if not task.status.is_terminal:
            act_cancel = QAction("Cancelar download", self)
            act_cancel.triggered.connect(lambda: self._manager.cancel_task(task_id))
            menu.addAction(act_cancel)
        else:
            act_remove = QAction("Remover da lista", self)
            act_remove.triggered.connect(lambda: self._manager.remove_task(task_id))
            menu.addAction(act_remove)

        menu.exec(self.list_widget.mapToGlobal(pos))

    def stop_audio(self) -> None:
        self._player.stop()
