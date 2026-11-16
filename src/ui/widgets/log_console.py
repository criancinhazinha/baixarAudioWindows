from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class LogConsoleWidget(QFrame):
    """Painel colapsável com comando exato executado, stdout/stderr e auditoria ffprobe."""

    ffprobe_file_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self._expanded = False
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(6)

        bar = QHBoxLayout()
        self.btn_toggle = QPushButton("▶ Console Técnico & Diagnóstico")
        self.btn_toggle.clicked.connect(self.toggle_expanded)

        self.lbl_last_cmd = QLabel("Pronto")
        self.lbl_last_cmd.setObjectName("MutedLabel")

        self.btn_ffprobe = QPushButton("Verificar arquivo com ffprobe...")
        self.btn_ffprobe.clicked.connect(self._pick_file_for_ffprobe)

        self.btn_copy = QPushButton("Copiar Log")
        self.btn_copy.clicked.connect(self._copy_log)

        self.btn_clear = QPushButton("Limpar")
        self.btn_clear.clicked.connect(self.clear)

        bar.addWidget(self.btn_toggle)
        bar.addWidget(self.lbl_last_cmd, stretch=1)
        bar.addWidget(self.btn_ffprobe)
        bar.addWidget(self.btn_copy)
        bar.addWidget(self.btn_clear)
        root.addLayout(bar)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setObjectName("LogView")
        self.text_edit.setReadOnly(True)
        self.text_edit.setMaximumBlockCount(3000)
        self.text_edit.setMinimumHeight(150)
        self.text_edit.setVisible(False)
        root.addWidget(self.text_edit)

    def toggle_expanded(self) -> None:
        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self.text_edit.setVisible(expanded)
        self.btn_toggle.setText(
            "▼ Console Técnico & Diagnóstico" if expanded else "▶ Console Técnico & Diagnóstico"
        )

    def append_line(self, line: str) -> None:
        self.text_edit.appendPlainText(line)

    def set_last_command(self, cmd: str) -> None:
        preview = cmd if len(cmd) <= 110 else cmd[:107] + "..."
        self.lbl_last_cmd.setText(preview)
        self.lbl_last_cmd.setToolTip(cmd)

    def clear(self) -> None:
        self.text_edit.clear()

    def _copy_log(self) -> None:
        QApplication.clipboard().setText(self.text_edit.toPlainText())

    def _pick_file_for_ffprobe(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar arquivo de áudio para auditoria ffprobe",
            "",
            "Áudio (*.webm *.opus *.m4a *.wav *.mp3 *.flac);;Todos (*.*)",
        )
        if path:
            self.set_expanded(True)
            self.ffprobe_file_requested.emit(path)
