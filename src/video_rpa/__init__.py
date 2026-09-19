"""Video RPA - 多平台影音自動化發佈與自癒系統套件."""

__version__ = "1.0.0"

from video_rpa.core.smart_driver import SmartDriver
from video_rpa.core.knowledge_store import KnowledgeStore
from video_rpa.core.trail_tracker import OperationTrailTracker

__all__ = [
    "SmartDriver",
    "KnowledgeStore",
    "OperationTrailTracker",
    "__version__",
]
