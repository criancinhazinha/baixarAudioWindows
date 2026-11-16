from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.models.video_metadata import TopicSearchResult


class TopicSearchDialog(QDialog):
    """Exibe resultados da busca por versões oficiais '- Topic' no YouTube Music."""

    def __init__(self, results: list[TopicSearchResult], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Buscar Versão Master (- Topic)")
        self.resize(640, 380)
        self._results = results
        self._selected_url: str | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        lbl = QLabel(
            "Selecione uma versão oficial '- Topic' para substituir o vídeo atual por uma master limpa:"
        )
        lbl.setWordWrap(True)
        root.addWidget(lbl)

        self.list_widget = QListWidget()
        for res in self._results:
            tag = "★ MASTER (- Topic)" if res.is_topic_master else "Vídeo"
            text = f"[{tag}]  {res.title}\n    Canal: {res.channel}  •  Duração: {res.duration_str}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, res.url)
            self.list_widget.addItem(item)
        if self._results:
            self.list_widget.setCurrentRow(0)
        self.list_widget.itemDoubleClicked.connect(lambda _: self._confirm())
        root.addWidget(self.list_widget, stretch=1)

        row = QHBoxLayout()
        row.addStretch(1)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        self.btn_select = QPushButton("Carregar Versão Selecionada")
        self.btn_select.setObjectName("MasterButton")
        self.btn_select.setEnabled(bool(self._results))
        self.btn_select.clicked.connect(self._confirm)
        row.addWidget(btn_cancel)
        row.addWidget(self.btn_select)
        root.addLayout(row)

    def _confirm(self) -> None:
        item = self.list_widget.currentItem()
        if item:
            self._selected_url = item.data(Qt.ItemDataRole.UserRole)
            self.accept()

    @property
    def selected_url(self) -> str | None:
        return self._selected_url
