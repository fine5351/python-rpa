"""Pytest 與單元測試環境設定，確保 src 目錄自動加入 sys.path."""

import os
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(root_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
