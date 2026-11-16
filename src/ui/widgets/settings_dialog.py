from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.models.app_settings import (
    SUPPORTED_BROWSERS,
    TEMPLATE_PRESETS,
    AppSettings,
    CookieSource,
    ExistingFilePolicy,
)
from src.services.binary_manager import BinaryStatus


class SettingsDialog(QDialog):
    """Diálogo de configurações: pasta, templates, cookies, concorrência e updater yt-dlp."""

    download_deps_requested = Signal()
    update_ytdlp_requested = Signal()

    def __init__(
        self,
        settings: AppSettings,
        binaries: BinaryStatus,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configurações — SonicFetch Desktop")
        self.resize(650, 620)
        self._settings = settings
        self._binaries = binaries
        self._build_ui()
        self._load_values(settings)
        self.refresh_binary_status(binaries)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        # Saída e Organização
        grp_out = QGroupBox("Saída, Nomeação e Fila")
        form_out = QFormLayout(grp_out)

        dir_row = QHBoxLayout()
        self.edit_output_dir = QLineEdit()
        btn_browse_dir = QPushButton("Procurar...")
        btn_browse_dir.clicked.connect(self._browse_output_dir)
        btn_open_dir = QPushButton("Abrir Pasta")
        btn_open_dir.clicked.connect(self._open_output_dir)
        dir_row.addWidget(self.edit_output_dir, stretch=1)
        dir_row.addWidget(btn_browse_dir)
        dir_row.addWidget(btn_open_dir)
        form_out.addRow("Pasta de saída:", dir_row)

        self.combo_template_preset = QComboBox()
        for label, tpl in TEMPLATE_PRESETS:
            self.combo_template_preset.addItem(label, tpl)
        self.combo_template_preset.addItem("Personalizado", "")
        self.combo_template_preset.currentIndexChanged.connect(self._on_preset_changed)
        form_out.addRow("Preset de nome:", self.combo_template_preset)

        self.edit_template = QLineEdit()
        form_out.addRow("Template yt-dlp:", self.edit_template)

        self.combo_existing = QComboBox()
        self.combo_existing.addItem("Renomear automaticamente (2), (3)...", ExistingFilePolicy.RENAME)
        self.combo_existing.addItem("Pular se já existir", ExistingFilePolicy.SKIP)
        self.combo_existing.addItem("Sobrescrever existente", ExistingFilePolicy.OVERWRITE)
        form_out.addRow("Arquivo existente:", self.combo_existing)

        self.spin_concurrency = QSpinBox()
        self.spin_concurrency.setRange(1, 4)
        form_out.addRow("Downloads simultâneos:", self.spin_concurrency)

        self.combo_mixed = QComboBox()
        self.combo_mixed.addItem("Perguntar sempre", "ask")
        self.combo_mixed.addItem("Baixar apenas o vídeo", "video")
        self.combo_mixed.addItem("Abrir playlist inteira", "playlist")
        form_out.addRow("URL mista (vídeo+playlist):", self.combo_mixed)

        root.addWidget(grp_out)

        # Cookies & Autenticação
        grp_cookies = QGroupBox("Autenticação & Cookies (YouTube Music Premium / Anti-Bot)")
        form_ck = QFormLayout(grp_cookies)

        self.combo_cookie_src = QComboBox()
        self.combo_cookie_src.addItem("Desativado (Padrão)", CookieSource.NONE)
        self.combo_cookie_src.addItem("Importar do Navegador (--cookies-from-browser)", CookieSource.BROWSER)
        self.combo_cookie_src.addItem("Arquivo manual cookies.txt", CookieSource.FILE)
        self.combo_cookie_src.currentIndexChanged.connect(self._update_cookie_fields)
        form_ck.addRow("Fonte de cookies:", self.combo_cookie_src)

        self.combo_browser = QComboBox()
        for br in SUPPORTED_BROWSERS:
            self.combo_browser.addItem(br.capitalize(), br)
        form_ck.addRow("Navegador:", self.combo_browser)

        ck_file_row = QHBoxLayout()
        self.edit_cookie_file = QLineEdit()
        self.btn_browse_cookie = QPushButton("Selecionar cookies.txt...")
        self.btn_browse_cookie.clicked.connect(self._browse_cookie_file)
        ck_file_row.addWidget(self.edit_cookie_file, stretch=1)
        ck_file_row.addWidget(self.btn_browse_cookie)
        form_ck.addRow("Arquivo cookies.txt:", ck_file_row)

        root.addWidget(grp_cookies)

        # Opções avançadas
        grp_adv = QGroupBox("Comportamento e Auditoria UVR5")
        adv_layout = QVBoxLayout(grp_adv)
        self.chk_clipboard = QCheckBox("Monitorar área de transferência ao focar a janela")
        self.chk_metadata = QCheckBox("Incorporar metadados sem perda (--embed-metadata)")
        self.chk_info_json = QCheckBox("Salvar arquivo .info.json sidecar para auditoria técnica")
        self.chk_legacy_mp3 = QCheckBox(
            "Habilitar perfil legado MP3 na interface (não recomendado para UVR5)"
        )
        adv_layout.addWidget(self.chk_clipboard)
        adv_layout.addWidget(self.chk_metadata)
        adv_layout.addWidget(self.chk_info_json)
        adv_layout.addWidget(self.chk_legacy_mp3)
        root.addWidget(grp_adv)

        # Binários gerenciados
        grp_bin = QGroupBox("Gerenciador de Binários (yt-dlp.exe & ffmpeg.exe)")
        bin_layout = QVBoxLayout(grp_bin)
        self.lbl_bin_status = QLabel("")
        self.lbl_bin_status.setWordWrap(True)
        bin_layout.addWidget(self.lbl_bin_status)

        bin_btns = QHBoxLayout()
        self.btn_download_deps = QPushButton("Baixar / Reparar Dependências")
        self.btn_download_deps.clicked.connect(self.download_deps_requested.emit)
        self.btn_update_ytdlp = QPushButton("Atualizar yt-dlp agora")
        self.btn_update_ytdlp.setObjectName("PrimaryButton")
        self.btn_update_ytdlp.clicked.connect(self.update_ytdlp_requested.emit)
        bin_btns.addWidget(self.btn_download_deps)
        bin_btns.addWidget(self.btn_update_ytdlp)
        bin_btns.addStretch(1)
        bin_layout.addLayout(bin_btns)
        root.addWidget(grp_bin)

        # Botões Salvar / Cancelar
        btns = QHBoxLayout()
        btns.addStretch(1)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Salvar Configurações")
        btn_save.setObjectName("PrimaryButton")
        btn_save.clicked.connect(self.accept)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        root.addLayout(btns)

    def _load_values(self, s: AppSettings) -> None:
        self.edit_output_dir.setText(s.output_dir)
        self.edit_template.setText(s.filename_template)
        matched_idx = self.combo_template_preset.findData(s.filename_template)
        if matched_idx >= 0:
            self.combo_template_preset.setCurrentIndex(matched_idx)
        else:
            self.combo_template_preset.setCurrentIndex(self.combo_template_preset.count() - 1)

        idx_ex = self.combo_existing.findData(s.existing_file_policy)
        if idx_ex >= 0:
            self.combo_existing.setCurrentIndex(idx_ex)
        self.spin_concurrency.setValue(s.normalized_concurrency())

        idx_mix = self.combo_mixed.findData(s.preferred_mixed_url_mode)
        if idx_mix >= 0:
            self.combo_mixed.setCurrentIndex(idx_mix)

        idx_ck = self.combo_cookie_src.findData(s.cookie_source)
        if idx_ck >= 0:
            self.combo_cookie_src.setCurrentIndex(idx_ck)
        idx_br = self.combo_browser.findData(s.cookie_browser)
        if idx_br >= 0:
            self.combo_browser.setCurrentIndex(idx_br)
        self.edit_cookie_file.setText(s.cookie_file_path)

        self.chk_clipboard.setChecked(s.clipboard_monitor)
        self.chk_metadata.setChecked(s.embed_metadata)
        self.chk_info_json.setChecked(s.write_info_json)
        self.chk_legacy_mp3.setChecked(s.allow_legacy_mp3)
        self._update_cookie_fields()

    def refresh_binary_status(self, b: BinaryStatus) -> None:
        self._binaries = b
        yt_txt = f"{b.ytdlp_path} (v{b.ytdlp_version or '?'})" if b.ytdlp_path else "Ausente"
        ff_txt = f"{b.ffmpeg_path} (v{b.ffmpeg_version or '?'})" if b.ffmpeg_path else "Ausente"
        fp_txt = f"{b.ffprobe_path}" if b.ffprobe_path else "Ausente"
        self.lbl_bin_status.setText(
            f"yt-dlp: {yt_txt}\nffmpeg: {ff_txt}\nffprobe: {fp_txt}"
        )
        self.btn_update_ytdlp.setEnabled(b.ytdlp_ready)

    def build_updated_settings(self) -> AppSettings:
        return AppSettings(
            output_dir=self.edit_output_dir.text().strip() or self._settings.output_dir,
            filename_template=self.edit_template.text().strip()
            or "%(uploader)s - %(title)s [%(format_id)s].%(ext)s",
            default_profile=self._settings.default_profile,
            remux_webm_to_opus=self._settings.remux_webm_to_opus,
            force_wav_44100_16bit=self._settings.force_wav_44100_16bit,
            allow_legacy_mp3=self.chk_legacy_mp3.isChecked(),
            embed_metadata=self.chk_metadata.isChecked(),
            write_info_json=self.chk_info_json.isChecked(),
            existing_file_policy=self.combo_existing.currentData(),
            max_concurrent_downloads=self.spin_concurrency.value(),
            cookie_source=self.combo_cookie_src.currentData(),
            cookie_browser=self.combo_browser.currentData(),
            cookie_file_path=self.edit_cookie_file.text().strip(),
            clipboard_monitor=self.chk_clipboard.isChecked(),
            preferred_mixed_url_mode=self.combo_mixed.currentData(),
        )

    def _on_preset_changed(self) -> None:
        tpl = self.combo_template_preset.currentData()
        if tpl:
            self.edit_template.setText(tpl)

    def _update_cookie_fields(self) -> None:
        src = self.combo_cookie_src.currentData()
        self.combo_browser.setEnabled(src == CookieSource.BROWSER)
        is_file = src == CookieSource.FILE
        self.edit_cookie_file.setEnabled(is_file)
        self.btn_browse_cookie.setEnabled(is_file)

    def _browse_output_dir(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self, "Escolher Pasta de Saída", self.edit_output_dir.text()
        )
        if chosen:
            self.edit_output_dir.setText(chosen)

    def _open_output_dir(self) -> None:
        path = Path(self.edit_output_dir.text().strip())
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(path))

    def _browse_cookie_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar cookies.txt", "", "Cookies (*.txt);;Todos (*.*)"
        )
        if path:
            self.edit_cookie_file.setText(path)
