from __future__ import annotations

from pathlib import Path

from src.models.app_settings import AppSettings, CookieSource, ExistingFilePolicy
from src.models.audio_profile import AudioProfile
from src.models.download_task import DownloadTask, TaskStatus
from src.services.settings_store import SettingsStore


def test_settings_store_roundtrip(tmp_path: Path) -> None:
    store = SettingsStore(
        config_path=tmp_path / "config.json",
        history_path=tmp_path / "history.json",
    )
    settings = AppSettings(
        output_dir=str(tmp_path / "Out"),
        default_profile=AudioProfile.WAV_NATIVE,
        force_wav_44100_16bit=False,
        max_concurrent_downloads=3,
        cookie_source=CookieSource.BROWSER,
        cookie_browser="chrome",
        existing_file_policy=ExistingFilePolicy.OVERWRITE,
    )
    store.save_settings(settings)
    loaded = store.load_settings()
    assert loaded.output_dir == settings.output_dir
    assert loaded.default_profile == AudioProfile.WAV_NATIVE
    assert loaded.max_concurrent_downloads == 3
    assert loaded.cookie_source == CookieSource.BROWSER
    assert loaded.cookie_browser == "chrome"
    assert loaded.existing_file_policy == ExistingFilePolicy.OVERWRITE

    task = DownloadTask(
        url="https://www.youtube.com/watch?v=123",
        title="Test Track",
        channel="Artist - Topic",
        profile=AudioProfile.RAW_OPUS_OR_BEST,
        status=TaskStatus.COMPLETED,
        output_path=str(tmp_path / "test.webm"),
    )
    store.append_history(task)
    history = store.load_history()
    assert len(history) == 1
    assert history[0]["title"] == "Test Track"
