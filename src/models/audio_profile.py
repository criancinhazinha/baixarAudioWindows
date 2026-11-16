from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AudioProfile(str, Enum):
    """Perfis de extração calibrados para fluxo de trabalho com UVR5."""

    RAW_OPUS_OR_BEST = "raw_opus_or_best"
    RAW_M4A = "raw_m4a"
    WAV_NATIVE = "wav_native"
    MP3_LEGACY = "mp3_legacy"


@dataclass(frozen=True)
class ProfileSpec:
    profile: AudioProfile
    title: str
    short_label: str
    description: str
    is_lossless_generation: bool
    warning: str | None = None


PROFILE_SPECS: dict[AudioProfile, ProfileSpec] = {
    AudioProfile.RAW_OPUS_OR_BEST: ProfileSpec(
        profile=AudioProfile.RAW_OPUS_OR_BEST,
        title="Original Bruto — UVR5 Recomendado (Bit-Exact)",
        short_label="Original Bruto (UVR5)",
        description=(
            "Baixa o stream nativo (Opus 251/774 ou AAC 140/141) bit a bit, "
            "sem transcodificação nem alteração de sample rate."
        ),
        is_lossless_generation=True,
    ),
    AudioProfile.RAW_M4A: ProfileSpec(
        profile=AudioProfile.RAW_M4A,
        title="M4A / AAC Nativo Puro",
        short_label="M4A Nativo",
        description=(
            "Prioriza fluxo nativo M4A/AAC (ID 141 Premium 256 kbps ou ID 140) "
            "sem re-encoding."
        ),
        is_lossless_generation=True,
    ),
    AudioProfile.WAV_NATIVE: ProfileSpec(
        profile=AudioProfile.WAV_NATIVE,
        title="WAV (PCM Sem Perdas de Geração)",
        short_label="WAV Nativo",
        description=(
            "Decodifica diretamente o melhor stream nativo para WAV preservando "
            "o sample rate original da fonte (48 kHz no Opus ou 44.1 kHz no AAC)."
        ),
        is_lossless_generation=True,
    ),
    AudioProfile.MP3_LEGACY: ProfileSpec(
        profile=AudioProfile.MP3_LEGACY,
        title="MP3 (Modo Legado — Não Recomendado p/ UVR5)",
        short_label="MP3 Legado",
        description="Converte o áudio para MP3 CBR 320 kbps.",
        is_lossless_generation=False,
        warning=(
            "Atenção: MP3 aplica dupla compressão com perda e reduz a qualidade "
            "da separação no UVR5."
        ),
    ),
}


def get_profile_spec(profile: AudioProfile) -> ProfileSpec:
    return PROFILE_SPECS[profile]
