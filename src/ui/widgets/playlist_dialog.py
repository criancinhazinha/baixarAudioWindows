from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.models.video_metadata import PlaylistEntry, VideoMetadata


class PlaylistDialog(QDialog):
    """Modal para seleção de faixas antes de enfileirar playlist em lote."""

    def __init__(self, metadata: VideoMetadata, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Playlist — {metadata.playlist_title}")
        self.resize(680, 480)
        self._entries = metadata.entries
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        header = QLabel(
            f"Selecione as faixas para adicionar à fila ({len(self._entries)} encontradas):"
        )
        header.setStyleSheet("font-weight: 700; font-size: 14px;")
        root.addWidget(header)

        tools = QHBoxLayout()
        btn_all = QPushButton("Selecionar Todas")
        btn_all.clicked.connect(lambda: self._set_all_checked(True))
        btn_none = QPushButton("Desmarcar Todas")
        btn_none.clicked.connect(lambda: self._set_all_checked(False))
        self.lbl_count = QLabel("")
        self.lbl_count.setObjectName("MutedLabel")

        tools.addWidget(btn_all)
        tools.addWidget(btn_none)
        tools.addStretch(1)
        tools.addWidget(self.lbl_count)
        root.addLayout(tools)

        self.list_widget = QListWidget()
        for idx, entry in enumerate(self._entries, start=1):
            badge = " [Master - Topic]" if entry.is_topic_master else ""
            label = f"{idx:02d}. {entry.title}  —  {entry.channel or 'Canal'} ({entry.duration_str}){badge}"
            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self.list_widget.addItem(item)
        self.list_widget.itemChanged.connect(self._update_count)
        root.addWidget(self.list_widget, stretch=1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        self.btn_confirm = QPushButton("Enfileirar Selecionadas")
        self.btn_confirm.setObjectName("PrimaryButton")
        self.btn_confirm.clicked.connect(self.accept)
        bottom.addWidget(btn_cancel)
        bottom.addWidget(self.btn_confirm)
        root.addLayout(bottom)

        self._update_count()

    def _set_all_checked(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self.list_widget.blockSignals(True)
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(state)
        self.list_widget.blockSignals(False)
        self._update_count()

    def _update_count(self) -> None:
        count = len(self.selected_entries())
        self.lbl_count.setText(f"{count} selecionada(s)")
        self.btn_confirm.setEnabled(count > 0)
        self.btn_confirm.setText(f"Enfileirar Selecionadas ({count})")

    def selected_entries(self) -> list[PlaylistEntry]:
        selected: list[PlaylistEntry] = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.data(Qt.ItemDataRole.UserRole))
        return selected
