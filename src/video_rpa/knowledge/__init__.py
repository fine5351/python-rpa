"""Video RPA Knowledge - 各平台自動化知識庫資源與持久化操作軌跡."""

import os
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parent


def get_knowledge_path(platform: str) -> str:
    """取得特定平台的知識庫 JSON 檔案絕對路徑."""
    return str(KNOWLEDGE_DIR / f"{platform}_knowledge.json")


def get_trail_path() -> str:
    """取得操作軌跡 JSON 檔案絕對路徑."""
    return str(KNOWLEDGE_DIR / "operation_trail.json")
