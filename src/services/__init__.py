"""Camada de serviços do SonicFetch Desktop."""

from src.services.binary_manager import BinaryManager, BinaryStatus, UpdateResult
from src.services.download_manager import DownloadManager
from src.services.inspector_service import FfprobeReport, InspectorService
from src.services.settings_store import SettingsStore
from src.services.topic_search_service import TopicSearchService

__all__ = [
    "BinaryManager",
    "BinaryStatus",
    "DownloadManager",
    "FfprobeReport",
    "InspectorService",
    "SettingsStore",
    "TopicSearchService",
    "UpdateResult",
]
