"""Video RPA 操作軌跡追蹤與固化管理器."""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TrailRecord:
    """Represents a single operation trail event that deviated from the primary selector
    or required AI/HITL intervention."""

    def __init__(self, platform: str, step_id: str, step_name: str, trigger_type: str,
                 original_primary: Optional[str], hit_locator: str, hit_index: int = 1,
                 total_candidates: int = 1, by_type: str = "xpath", details: str = "",
                 suggested_target: str = ""):
        self.platform = platform
        self.step_id = step_id
        self.step_name = step_name
        self.trigger_type = trigger_type  # SECONDARY_LOCATOR, AI_AGENT_LOCATOR, AI_AGENT_POPUP, HITL_INTERVENTION, AI_AGENT_OPERATION
        self.original_primary = original_primary
        self.hit_locator = hit_locator
        self.hit_index = hit_index
        self.total_candidates = total_candidates
        self.by_type = by_type
        self.details = details
        self.suggested_target = suggested_target or f"src/video_rpa/knowledge/{platform}_knowledge.json"
        self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "step_id": self.step_id,
            "step_name": self.step_name,
            "trigger_type": self.trigger_type,
            "hit_index": self.hit_index,
            "total_candidates": self.total_candidates,
            "original_primary": self.original_primary,
            "hit_locator": self.hit_locator,
            "by_type": self.by_type,
            "details": self.details,
            "suggested_target": self.suggested_target,
            "timestamp": self.timestamp
        }


class OperationTrailTracker:
    """Tracks non-primary selector hits, AI Agent web operations, and HITL actions.
    Provides structured summaries and triggers consolidation logs at task completion."""

    _instance: Optional["OperationTrailTracker"] = None

    def __init__(self):
        self.records: List[TrailRecord] = []

    @classmethod
    def get_instance(cls) -> "OperationTrailTracker":
        if cls._instance is None:
            cls._instance = OperationTrailTracker()
        return cls._instance

    def clear(self) -> None:
        """Clears all in-memory trail records."""
        self.records.clear()

    def has_pending_consolidations(self) -> bool:
        return len(self.records) > 0

    def record_secondary_hit(self, platform: str, step_id: str, step_name: str,
                             hit_index: int, total_candidates: int,
                             original_primary: Optional[str], hit_locator: str,
                             by_type: str = "xpath") -> None:
        """Records when an element was matched by the 2nd or later candidate selector."""
        record = TrailRecord(
            platform=platform,
            step_id=step_id,
            step_name=step_name,
            trigger_type="SECONDARY_LOCATOR",
            original_primary=original_primary,
            hit_locator=hit_locator,
            hit_index=hit_index,
            total_candidates=total_candidates,
            by_type=by_type,
            details=f"原首選選擇器失效，命中第 {hit_index}/{total_candidates} 個候選選擇器",
            suggested_target=f"src/video_rpa/knowledge/{platform}_knowledge.json"
        )
        self.records.append(record)
        logger.warning(
            f"📝 [操作軌跡記錄] 步驟 [{step_name}] 未命中首選選擇器，命中第 {hit_index} 個候選選擇器: {hit_locator}"
        )

    def record_ai_action(self, platform: str, step_id: str, step_name: str,
                         action_type: str, suggested_xpath: str,
                         original_primary: Optional[str] = None, details: str = "") -> None:
        """Records when an AI Agent (Vision or DOM analyzer) resolves an obstacle or locates an element."""
        trigger_type = "AI_AGENT_POPUP" if "POPUP" in action_type else "AI_AGENT_LOCATOR"
        record = TrailRecord(
            platform=platform,
            step_id=step_id,
            step_name=step_name,
            trigger_type=trigger_type,
            original_primary=original_primary,
            hit_locator=suggested_xpath,
            hit_index=0,
            total_candidates=0,
            by_type="xpath",
            details=details or f"AI Agent 自動分析網頁推論操作: {action_type}",
            suggested_target=f"src/video_rpa/knowledge/{platform}_knowledge.json"
        )
        self.records.append(record)
        logger.warning(
            f"🤖 [操作軌跡記錄] 步驟 [{step_name}] 觸發 AI Agent 介入操作: {suggested_xpath} ({details})"
        )

    def record_ai_agent_operation(self, platform: str, step_id: str, step_name: str,
                                  operation_description: str, element_selector: Optional[str] = None,
                                  details: str = "") -> None:
        """Records generic AI agent web reading or interaction operations."""
        record = TrailRecord(
            platform=platform,
            step_id=step_id,
            step_name=step_name,
            trigger_type="AI_AGENT_OPERATION",
            original_primary=None,
            hit_locator=element_selector or operation_description,
            hit_index=0,
            total_candidates=0,
            by_type="ai_agent",
            details=f"{operation_description} | {details}" if details else operation_description,
            suggested_target=f"src/video_rpa/knowledge/{platform}_knowledge.json"
        )
        self.records.append(record)
        logger.warning(
            f"🤖 [操作軌跡記錄] 步驟 [{step_name}] 引入 AI Agent 讀取網頁資料並操作: {operation_description}"
        )

    def record_hitl_action(self, platform: str, step_id: str, step_name: str,
                           new_xpath: str, original_primary: Optional[str] = None,
                           is_new_step: bool = False) -> None:
        """Records when human intervention resolves a stuck step or adds a new step."""
        record = TrailRecord(
            platform=platform,
            step_id=step_id,
            step_name=step_name,
            trigger_type="HITL_INTERVENTION",
            original_primary=original_primary,
            hit_locator=new_xpath,
            hit_index=0,
            total_candidates=0,
            by_type="xpath",
            details="使用者透過人機協同拾取器或終端機指定之新選擇器" if not is_new_step else "人機協同新增之中介步驟",
            suggested_target=f"src/video_rpa/knowledge/{platform}_knowledge.json"
        )
        self.records.append(record)
        logger.warning(
            f"🧑‍💻 [操作軌跡記錄] 步驟 [{step_name}] 透過人機協同介入完成: {new_xpath}"
        )

    def save_to_file(self, target_file: Optional[str] = None) -> None:
        """Persists trail records to a JSON file for future consolidation or audits."""
        if not self.records:
            return

        if target_file is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            target_file = os.path.normpath(os.path.join(current_dir, "..", "knowledge", "operation_trail.json"))

        try:
            folder = os.path.dirname(target_file)
            if folder and not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)

            existing_data: List[Dict[str, Any]] = []
            if os.path.exists(target_file):
                try:
                    with open(target_file, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                except Exception:
                    existing_data = []

            new_entries = [r.to_dict() for r in self.records]
            existing_data.extend(new_entries)

            temp_path = f"{target_file}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, target_file)
            logger.info(f"Persisted {len(new_entries)} operation trail record(s) to {target_file}")
        except Exception as e:
            logger.error(f"Failed to persist operation trail to {target_file}: {e}")

    def build_consolidation_report(self) -> str:
        """Builds a formatted multiline string detailing pending consolidations."""
        if not self.records:
            return "✨【RPA 固化檢查】本次任務所有步驟均於首選選擇器第 1 次命中，無需回寫 script 進行固化。"

        lines = [
            "=" * 80,
            "🚨【RPA 固化提醒 / Script Consolidation Required】",
            f"本次執行中偵測到 {len(self.records)} 項步驟偏離原定首選選擇器或引入了 AI/人機介入。",
            "系統已在執行期間自動調整知識庫優先級，為使後續執行能「第 1 次就命中」，請將以下操作回寫至 script 固化：",
            "-" * 80
        ]

        for idx, r in enumerate(self.records, start=1):
            trigger_title = {
                "SECONDARY_LOCATOR": f"備選選擇器命中 (第 {r.hit_index}/{r.total_candidates} 個)",
                "AI_AGENT_LOCATOR": "AI Agent 視覺推論定位",
                "AI_AGENT_POPUP": "AI Agent 彈窗排除介入",
                "HITL_INTERVENTION": "人機協同標註介入",
                "AI_AGENT_OPERATION": "AI Agent 網頁讀取與操作"
            }.get(r.trigger_type, r.trigger_type)

            lines.append(f"[{idx}] 平台: {r.platform} | 步驟: {r.step_name} (ID: {r.step_id})")
            lines.append(f"    - 觸發機制: {trigger_title}")
            if r.original_primary:
                lines.append(f"    - 原首選 (已失效): {r.original_primary}")
            lines.append(f"    - 實際生效 (新首選): {r.hit_locator}")
            lines.append(f"    - 詳細說明: {r.details}")
            lines.append(f"    - 建議回寫目標: {r.suggested_target}")
            lines.append(f"    - 固化建議: 請確認將此選擇器設為第一順位，讓未來直接命中，避免等待超時。")
            lines.append("-" * 80)

        lines.append("=" * 80)
        return "\n".join(lines)

    def print_consolidation_log(self, target_logger: Optional[logging.Logger] = None) -> None:
        """Outputs the consolidation report to the specified logger or module logger."""
        report = self.build_consolidation_report()
        log_func = (target_logger or logger).warning if self.has_pending_consolidations() else (target_logger or logger).info
        for line in report.split("\n"):
            log_func(line)
        if self.has_pending_consolidations():
            self.save_to_file()
