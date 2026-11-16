from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.stream_selector import select_recommended_stream
from src.models.audio_profile import AudioProfile
from src.models.stream_info import StreamInfo
from src.models.video_metadata import VideoMetadata


class PreviewPanel(QFrame):
    """Exibe metadados do vídeo/faixa, badge '- Topic' e tabela de streams audio-only."""

    search_topic_requested = Signal()
    enqueue_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self._metadata: VideoMetadata | None = None
        self._current_profile: AudioProfile = AudioProfile.RAW_OPUS_OR_BEST
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # Barra de progresso para análise assíncrona
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0)
        self.loading_bar.setMaximumHeight(6)
        self.loading_bar.setTextVisible(False)
        self.loading_bar.setVisible(False)
        root.addWidget(self.loading_bar)

        # Cabeçalho: thumbnail + informações + badges
        header = QHBoxLayout()
        header.setSpacing(14)

        self.thumb_label = QLabel("Sem capa")
        self.thumb_label.setFixedSize(160, 90)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setStyleSheet(
            "background-color: #0D1117; border: 1px solid #262E3B; border-radius: 8px; color: #6E7681;"
        )
        header.addWidget(self.thumb_label)

        info_col = QVBoxLayout()
        info_col.setSpacing(6)

        self.title_label = QLabel("Cole uma URL do YouTube ou YouTube Music para inspecionar os streams")
        self.title_label.setObjectName("TitleLabel")
        self.title_label.setWordWrap(True)

        self.artist_label = QLabel("Nenhum item analisado")
        self.artist_label.setObjectName("MutedLabel")

        badges_row = QHBoxLayout()
        badges_row.setSpacing(8)

        self.badge_source = QLabel("Aguardando")
        self.badge_source.setObjectName("BadgeStandard")
        self.badge_source.setVisible(False)

        self.badge_premium = QLabel("Premium 256 kbps")
        self.badge_premium.setObjectName("BadgePremium")
        self.badge_premium.setVisible(False)

        self.btn_find_topic = QPushButton("Buscar versão - Topic (Master)")
        self.btn_find_topic.setObjectName("MasterButton")
        self.btn_find_topic.setVisible(False)
        self.btn_find_topic.clicked.connect(self.search_topic_requested.emit)

        badges_row.addWidget(self.badge_source)
        badges_row.addWidget(self.badge_premium)
        badges_row.addWidget(self.btn_find_topic)
        badges_row.addStretch(1)

        info_col.addWidget(self.title_label)
        info_col.addWidget(self.artist_label)
        info_col.addLayout(badges_row)
        header.addLayout(info_col, stretch=1)
        root.addLayout(header)

        # Controle da tabela de streams
        stream_bar = QHBoxLayout()
        stream_bar.setSpacing(10)

        lbl_streams = QLabel("Streams de Áudio Disponíveis (Somente Áudio)")
        lbl_streams.setStyleSheet("font-weight: 600; color: #C9D1D9;")

        self.chk_auto_stream = QCheckBox("Seleção automática pelo perfil UVR5")
        self.chk_auto_stream.setChecked(True)
        self.chk_auto_stream.toggled.connect(self._on_auto_toggled)

        self.lbl_selected_stream = QLabel("Stream: Automático")
        self.lbl_selected_stream.setObjectName("MutedLabel")

        stream_bar.addWidget(lbl_streams)
        stream_bar.addStretch(1)
        stream_bar.addWidget(self.chk_auto_stream)
        stream_bar.addWidget(self.lbl_selected_stream)
        root.addLayout(stream_bar)

        self.streams_table = QTableWidget(0, 7)
        self.streams_table.setHorizontalHeaderLabels(
            ["Format ID", "Codec", "Contêiner", "Bitrate (abr)", "Sample Rate", "Tamanho", "Notas"]
        )
        self.streams_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.streams_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.streams_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.streams_table.setAlternatingRowColors(True)
        self.streams_table.verticalHeader().setVisible(False)
        self.streams_table.setMinimumHeight(140)
        self.streams_table.setMaximumHeight(200)
        hdr = self.streams_table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.streams_table.itemSelectionChanged.connect(self._on_table_selection_changed)
        root.addWidget(self.streams_table)

        # Rodapé com botão de download
        action_row = QHBoxLayout()
        action_row.addStretch(1)
        self.btn_enqueue = QPushButton("Adicionar à Fila de Extração")
        self.btn_enqueue.setObjectName("PrimaryButton")
        self.btn_enqueue.setMinimumHeight(36)
        self.btn_enqueue.setMinimumWidth(220)
        self.btn_enqueue.setEnabled(False)
        self.btn_enqueue.clicked.connect(self.enqueue_requested.emit)
        action_row.addWidget(self.btn_enqueue)
        root.addLayout(action_row)

    def set_loading(self, loading: bool) -> None:
        self.loading_bar.setVisible(loading)
        if loading:
            self.btn_enqueue.setEnabled(False)

    def set_thumbnail_bytes(self, data: bytes | None) -> None:
        if not data:
            self.thumb_label.setPixmap(QPixmap())
            self.thumb_label.setText("Sem capa")
            return
        pix = QPixmap()
        if pix.loadFromData(data):
            scaled = pix.scaled(
                self.thumb_label.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.thumb_label.setPixmap(scaled)
            self.thumb_label.setText("")

    def set_metadata(self, meta: VideoMetadata | None, profile: AudioProfile) -> None:
        self._metadata = meta
        self._current_profile = profile
        if meta is None:
            self.title_label.setText("Cole uma URL do YouTube ou YouTube Music para inspecionar os streams")
            self.artist_label.setText("Nenhum item analisado")
            self.badge_source.setVisible(False)
            self.badge_premium.setVisible(False)
            self.btn_find_topic.setVisible(False)
            self.streams_table.setRowCount(0)
            self.btn_enqueue.setEnabled(False)
            self.set_thumbnail_bytes(None)
            return

        self.title_label.setText(meta.title)
        self.artist_label.setText(f"{meta.display_artist}  •  Duração: {meta.duration_str}")

        self.badge_source.setVisible(True)
        if meta.is_topic_master:
            self.badge_source.setText("Master / - Topic")
            self.badge_source.setObjectName("BadgeMaster")
            self.btn_find_topic.setVisible(False)
        else:
            self.badge_source.setText("Vídeo Padrão")
            self.badge_source.setObjectName("BadgeStandard")
            self.btn_find_topic.setVisible(True)
        self.badge_source.style().unpolish(self.badge_source)
        self.badge_source.style().polish(self.badge_source)

        self.badge_premium.setVisible(meta.has_premium_stream)

        self._populate_streams_table(meta.streams)
        self.apply_profile_selection(profile)
        self.btn_enqueue.setEnabled(bool(meta.streams))

    def apply_profile_selection(self, profile: AudioProfile) -> None:
        self._current_profile = profile
        if not self._metadata or not self._metadata.streams:
            return
        if self.chk_auto_stream.isChecked():
            rec = select_recommended_stream(self._metadata.streams, profile)
            if rec:
                self._select_row_by_format_id(rec.format_id)
                self.lbl_selected_stream.setText(
                    f"Auto: ID {rec.format_id} ({rec.acodec}, {rec.abr_str}, {rec.asr_str})"
                )

    def selected_format_id(self) -> str | None:
        if self.chk_auto_stream.isChecked():
            if self._metadata:
                rec = select_recommended_stream(self._metadata.streams, self._current_profile)
                return rec.format_id if rec else None
            return None
        row = self.streams_table.currentRow()
        if row >= 0:
            item = self.streams_table.item(row, 0)
            if item:
                return item.data(Qt.ItemDataRole.UserRole)
        return None

    def selected_stream(self) -> StreamInfo | None:
        fid = self.selected_format_id()
        if not fid or not self._metadata:
            return None
        return next((s for s in self._metadata.streams if s.format_id == fid), None)

    def _populate_streams_table(self, streams: list[StreamInfo]) -> None:
        self.streams_table.blockSignals(True)
        self.streams_table.setRowCount(len(streams))
        for row_idx, s in enumerate(streams):
            note = s.format_note
            if s.is_premium_high_bitrate:
                note = f"{note} [Premium 256k]".strip()
            values = [
                s.format_id,
                s.acodec,
                s.ext,
                s.abr_str,
                s.asr_str,
                s.size_mb_str,
                note or "—",
            ]
            for col_idx, val in enumerate(values):
                cell = QTableWidgetItem(val)
                if col_idx == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, s.format_id)
                if col_idx in (0, 3, 4, 5):
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.streams_table.setItem(row_idx, col_idx, cell)
        self.streams_table.blockSignals(False)

    def _select_row_by_format_id(self, format_id: str) -> None:
        self.streams_table.blockSignals(True)
        for row in range(self.streams_table.rowCount()):
            item = self.streams_table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == format_id:
                self.streams_table.selectRow(row)
                break
        self.streams_table.blockSignals(False)

    def _on_auto_toggled(self, checked: bool) -> None:
        if checked:
            self.apply_profile_selection(self._current_profile)
        else:
            self._on_table_selection_changed()

    def _on_table_selection_changed(self) -> None:
        row = self.streams_table.currentRow()
        if row < 0 or not self._metadata:
            return
        item = self.streams_table.item(row, 0)
        if not item:
            return
        fid = item.data(Qt.ItemDataRole.UserRole)
        stream = next((s for s in self._metadata.streams if s.format_id == fid), None)
        if stream:
            # Se usuário clicou manualmente em outra linha, desativa auto apenas se diferente do recomendado
            rec = select_recommended_stream(self._metadata.streams, self._current_profile)
            if rec and rec.format_id != stream.format_id and self.chk_auto_stream.isChecked():
                self.chk_auto_stream.blockSignals(True)
                self.chk_auto_stream.setChecked(False)
                self.chk_auto_stream.blockSignals(False)
            prefix = "Auto" if self.chk_auto_stream.isChecked() else "Manual"
            self.lbl_selected_stream.setText(
                f"{prefix}: ID {stream.format_id} ({stream.acodec}, {stream.abr_str}, {stream.asr_str})"
            )
