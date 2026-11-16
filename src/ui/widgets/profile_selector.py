from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QGroupBox,
    QLabel,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from src.models.app_settings import AppSettings
from src.models.audio_profile import AudioProfile, get_profile_spec


class ProfileSelector(QGroupBox):
    """Seletor dos perfis de extração calibrados para UVR5."""

    profile_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Perfil de Extração (Calibrado para UVR5)", parent)
        self._allow_legacy_mp3 = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self._group = QButtonGroup(self)
        self._radios: dict[AudioProfile, QRadioButton] = {}

        for profile in (
            AudioProfile.RAW_OPUS_OR_BEST,
            AudioProfile.RAW_M4A,
            AudioProfile.WAV_NATIVE,
            AudioProfile.MP3_LEGACY,
        ):
            spec = get_profile_spec(profile)
            rb = QRadioButton(spec.title)
            rb.setToolTip(spec.description)
            self._group.addButton(rb)
            self._radios[profile] = rb
            layout.addWidget(rb)

            if profile == AudioProfile.RAW_OPUS_OR_BEST:
                self.chk_remux_opus = QCheckBox(
                    "Extrair contêiner sem recodificar (.webm → .opus via ffmpeg -c:a copy)"
                )
                self.chk_remux_opus.setStyleSheet("margin-left: 22px; color: #9CA3AF;")
                self.chk_remux_opus.toggled.connect(lambda _: self.profile_changed.emit())
                layout.addWidget(self.chk_remux_opus)

            if profile == AudioProfile.WAV_NATIVE:
                self.chk_force_44100 = QCheckBox(
                    "Forçar 44.1 kHz / 16-bit (CD / Teclados / DAWs legadas)"
                )
                self.chk_force_44100.setStyleSheet("margin-left: 22px; color: #9CA3AF;")
                self.chk_force_44100.toggled.connect(lambda _: self.profile_changed.emit())
                layout.addWidget(self.chk_force_44100)

        self.lbl_desc = QLabel("")
        self.lbl_desc.setObjectName("MutedLabel")
        self.lbl_desc.setWordWrap(True)
        layout.addWidget(self.lbl_desc)

        self.lbl_mp3_warning = QLabel(
            "⚠ Atenção: MP3 aplica dupla compressão com perda e reduz a qualidade da separação no UVR5."
        )
        self.lbl_mp3_warning.setWordWrap(True)
        self.lbl_mp3_warning.setStyleSheet(
            "background-color: #3B2809; color: #FCD34D; border: 1px solid #D97706; "
            "border-radius: 6px; padding: 6px 10px; font-weight: 600;"
        )
        self.lbl_mp3_warning.setVisible(False)
        layout.addWidget(self.lbl_mp3_warning)

        self._group.buttonToggled.connect(self._on_selection_changed)
        self._radios[AudioProfile.RAW_OPUS_OR_BEST].setChecked(True)
        self._update_visibility_and_hints()

    def apply_settings(self, settings: AppSettings) -> None:
        self._allow_legacy_mp3 = settings.allow_legacy_mp3
        self._radios[AudioProfile.MP3_LEGACY].setVisible(self._allow_legacy_mp3)

        target = settings.default_profile
        if target == AudioProfile.MP3_LEGACY and not self._allow_legacy_mp3:
            target = AudioProfile.RAW_OPUS_OR_BEST
        self._radios[target].setChecked(True)
        self.chk_remux_opus.setChecked(settings.remux_webm_to_opus)
        self.chk_force_44100.setChecked(settings.force_wav_44100_16bit)
        self._update_visibility_and_hints()

    def current_profile(self) -> AudioProfile:
        for profile, rb in self._radios.items():
            if rb.isChecked():
                return profile
        return AudioProfile.RAW_OPUS_OR_BEST

    def remux_opus_enabled(self) -> bool:
        return self.current_profile() == AudioProfile.RAW_OPUS_OR_BEST and self.chk_remux_opus.isChecked()

    def force_44100_enabled(self) -> bool:
        return self.current_profile() == AudioProfile.WAV_NATIVE and self.chk_force_44100.isChecked()

    def _on_selection_changed(self) -> None:
        self._update_visibility_and_hints()
        self.profile_changed.emit()

    def _update_visibility_and_hints(self) -> None:
        profile = self.current_profile()
        spec = get_profile_spec(profile)
        self.lbl_desc.setText(spec.description)
        self.chk_remux_opus.setEnabled(profile == AudioProfile.RAW_OPUS_OR_BEST)
        self.chk_force_44100.setEnabled(profile == AudioProfile.WAV_NATIVE)
        self.lbl_mp3_warning.setVisible(profile == AudioProfile.MP3_LEGACY)
