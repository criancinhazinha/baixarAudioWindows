from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class UrlInputBar(QWidget):
    """Barra principal de entrada de URLs do YouTube / YT Music ou busca."""

    analyze_requested = Signal(str)
    settings_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(8)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText(
            "Cole a URL do YouTube, YouTube Music (music.youtube.com), Playlist ou digite uma busca..."
        )
        self.url_edit.setClearButtonEnabled(True)
        self.url_edit.returnPressed.connect(self._emit_analyze)

        self.btn_paste = QPushButton("Colar")
        self.btn_paste.setToolTip("Colar da área de transferência e analisar")
        self.btn_paste.clicked.connect(self._paste_from_clipboard)

        self.btn_clear = QPushButton("Limpar")
        self.btn_clear.clicked.connect(self.url_edit.clear)

        self.btn_analyze = QPushButton("Analisar")
        self.btn_analyze.setObjectName("PrimaryButton")
        self.btn_analyze.setMinimumWidth(110)
        self.btn_analyze.clicked.connect(self._emit_analyze)

        self.btn_settings = QPushButton("Configurações")
        self.btn_settings.clicked.connect(self.settings_requested.emit)

        row.addWidget(self.url_edit, stretch=1)
        row.addWidget(self.btn_paste)
        row.addWidget(self.btn_clear)
        row.addWidget(self.btn_analyze)
        row.addWidget(self.btn_settings)

        self.status_hint = QLabel("")
        self.status_hint.setObjectName("MutedLabel")
        self.status_hint.setVisible(False)

        root.addLayout(row)
        root.addWidget(self.status_hint)

    def set_url(self, url: str) -> None:
        self.url_edit.setText(url)

    def current_text(self) -> str:
        return self.url_edit.text().strip()

    def set_busy(self, busy: bool) -> None:
        self.btn_analyze.setEnabled(not busy)
        self.btn_paste.setEnabled(not busy)
        self.btn_analyze.setText("Analisando..." if busy else "Analisar")

    def set_hint(self, text: str) -> None:
        self.status_hint.setText(text)
        self.status_hint.setVisible(bool(text))

    def _paste_from_clipboard(self) -> None:
        clip = QApplication.clipboard().text().strip()
        if clip:
            self.url_edit.setText(clip)
            self._emit_analyze()

    def _emit_analyze(self) -> None:
        text = self.url_edit.text().strip()
        if text:
            self.analyze_requested.emit(text)
