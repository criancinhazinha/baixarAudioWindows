from __future__ import annotations

from src.models.audio_profile import AudioProfile
from src.models.download_task import DownloadTask, TaskStatus
from src.models.stream_info import StreamInfo
from src.models.video_metadata import PlaylistEntry, VideoMetadata
from src.ui.main_window import MainWindow
from src.ui.widgets.playlist_dialog import PlaylistDialog
from src.ui.widgets.profile_selector import ProfileSelector


def test_profile_selector_defaults_and_mp3_warning(qtbot) -> None:
    selector = ProfileSelector()
    qtbot.addWidget(selector)
    assert selector.current_profile() == AudioProfile.RAW_OPUS_OR_BEST
    assert selector.lbl_mp3_warning.isVisible() is False

    # Habilita MP3 legado e seleciona
    selector._radios[AudioProfile.MP3_LEGACY].setVisible(True)
    selector._radios[AudioProfile.MP3_LEGACY].setChecked(True)
    assert selector.current_profile() == AudioProfile.MP3_LEGACY
    assert selector.lbl_mp3_warning.isHidden() is False


def test_main_window_instantiates_and_populates_preview(qtbot, tmp_path) -> None:
    win = MainWindow()
    qtbot.addWidget(win)

    meta = VideoMetadata(
        id="abc123",
        title="Midnight City",
        url="https://www.youtube.com/watch?v=abc123",
        channel="M83 - Topic",
        duration=243,
        is_topic_master=True,
        streams=[
            StreamInfo(format_id="251", ext="webm", acodec="opus", abr=142.0, asr=48000, filesize=4_200_000),
            StreamInfo(format_id="140", ext="m4a", acodec="mp4a.40.2", abr=129.0, asr=44100, filesize=3_900_000),
        ],
    )
    win.preview_panel.set_metadata(meta, AudioProfile.RAW_OPUS_OR_BEST)
    assert win.preview_panel.streams_table.rowCount() == 2
    assert win.preview_panel.selected_format_id() == "251"
    assert win.preview_panel.badge_source.text() == "Master / - Topic"

    fake_audio = tmp_path / "M83 - Midnight City [251].webm"
    fake_audio.write_bytes(b"opus")
    task = DownloadTask(
        url=meta.url,
        title=meta.title,
        channel=meta.channel,
        profile=AudioProfile.RAW_OPUS_OR_BEST,
        status=TaskStatus.COMPLETED,
        progress_percent=100.0,
        output_path=str(fake_audio),
    )
    win._download_manager._tasks.insert(0, task)
    win._download_manager._tasks_by_id[task.task_id] = task
    win.queue_widget._rebuild_list()
    assert win.queue_widget.list_widget.count() == 1
    row_widget = win.queue_widget._widgets_by_id[task.task_id]
    assert row_widget.btn_explorer.isHidden() is False
    assert row_widget.lbl_drag_hint.isHidden() is False


def test_playlist_dialog_selection(qtbot) -> None:
    meta = VideoMetadata(
        id="PL1",
        title="Álbum Demo",
        url="https://www.youtube.com/playlist?list=PL1",
        is_playlist=True,
        playlist_title="Álbum Demo",
        entries=[
            PlaylistEntry(id="1", title="Track 1", url="https://youtube.com/watch?v=1", is_topic_master=True),
            PlaylistEntry(id="2", title="Track 2", url="https://youtube.com/watch?v=2", is_topic_master=False),
        ],
    )
    dlg = PlaylistDialog(meta)
    qtbot.addWidget(dlg)
    assert len(dlg.selected_entries()) == 2
    dlg._set_all_checked(False)
    assert len(dlg.selected_entries()) == 0
