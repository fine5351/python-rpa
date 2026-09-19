import json
import logging
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Ensure src directory is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(root_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from video_rpa.core.knowledge_store import KnowledgeStore
from video_rpa.core.trail_tracker import OperationTrailTracker, TrailRecord
from video_rpa.core.smart_driver import SmartDriver


class TestTrailTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = OperationTrailTracker.get_instance()
        self.tracker.clear()

    def tearDown(self):
        self.tracker.clear()

    def test_record_secondary_hit(self):
        self.tracker.record_secondary_hit(
            platform="rednote",
            step_id="publish_button",
            step_name="發佈按鈕",
            hit_index=6,
            total_candidates=6,
            original_primary="//button[@class='bg-red']",
            hit_locator="//xhs-publish-btn",
            by_type="xpath"
        )
        self.assertTrue(self.tracker.has_pending_consolidations())
        self.assertEqual(len(self.tracker.records), 1)
        r = self.tracker.records[0]
        self.assertEqual(r.platform, "rednote")
        self.assertEqual(r.step_id, "publish_button")
        self.assertEqual(r.hit_index, 6)
        self.assertEqual(r.hit_locator, "//xhs-publish-btn")
        self.assertEqual(r.original_primary, "//button[@class='bg-red']")

    def test_record_ai_action(self):
        self.tracker.record_ai_action(
            platform="youtube",
            step_id="modal_blocker",
            step_name="未知彈窗",
            action_type="AI_POPUP_DISMISS",
            suggested_xpath="//button[text()='確認']",
            original_primary=None,
            details="AI 偵測到畫面遮蔽彈窗"
        )
        self.assertEqual(len(self.tracker.records), 1)
        r = self.tracker.records[0]
        self.assertEqual(r.trigger_type, "AI_AGENT_POPUP")
        self.assertEqual(r.hit_locator, "//button[text()='確認']")

    def test_record_ai_agent_operation(self):
        self.tracker.record_ai_agent_operation(
            platform="tiktok",
            step_id="ai_caption_fill",
            step_name="AI 生成文案填入",
            operation_description="AI Agent 讀取頁面標籤後自動填寫最佳化文案",
            element_selector="//div[@contenteditable='true']",
            details="模型生成推薦標籤並送出"
        )
        self.assertEqual(len(self.tracker.records), 1)
        r = self.tracker.records[0]
        self.assertEqual(r.trigger_type, "AI_AGENT_OPERATION")
        self.assertIn("AI Agent", r.details)

    def test_consolidation_report_output(self):
        self.tracker.record_secondary_hit(
            platform="rednote",
            step_id="publish_button",
            step_name="發佈按鈕",
            hit_index=2,
            total_candidates=2,
            original_primary="//button[contains(text(), '舊版發布')]",
            hit_locator="//xhs-publish-btn",
            by_type="xpath"
        )
        report = self.tracker.build_consolidation_report()
        self.assertIn("🚨【RPA 固化提醒 / Script Consolidation Required】", report)
        self.assertIn("發佈按鈕", report)
        self.assertIn("//xhs-publish-btn", report)
        self.assertIn("src/video_rpa/knowledge/rednote_knowledge.json", report)

    def test_save_trail_to_file(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            temp_path = f.name
        try:
            self.tracker.record_secondary_hit(
                platform="tiktok",
                step_id="success_indicator",
                step_name="發佈成功指示標籤",
                hit_index=2,
                total_candidates=2,
                original_primary="//div[contains(text(), 'Manage your posts')]",
                hit_locator="//*[contains(text(), '已發布')]",
                by_type="xpath"
            )
            self.tracker.save_to_file(temp_path)
            with open(temp_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["hit_locator"], "//*[contains(text(), '已發布')]")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestKnowledgeStorePromotion(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        initial_data = {
            "version": "1.0.0",
            "platform": "rednote",
            "steps": {
                "publish_button": {
                    "name": "發佈按鈕",
                    "timeout": 15,
                    "locators": [
                        {"by": "xpath", "value": "//button[@class='primary']", "weight": 20},
                        {"by": "xpath", "value": "//button[@class='secondary']", "weight": 10},
                        {"by": "xpath", "value": "//xhs-publish-btn", "weight": 5}
                    ]
                }
            }
        }
        with open(self.temp_file.name, "w", encoding="utf-8") as f:
            json.dump(initial_data, f)
        self.store = KnowledgeStore(self.temp_file.name)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_promote_locator_to_primary(self):
        # Originally //button[@class='primary'] is primary (weight 20)
        locators_before = self.store.get_locators("publish_button")
        self.assertEqual(locators_before[0]["value"], "//button[@class='primary']")

        # Promote 3rd locator //xhs-publish-btn
        self.store.promote_locator_to_primary("publish_button", "//xhs-publish-btn")

        # Reload store to verify persistence
        new_store = KnowledgeStore(self.temp_file.name)
        locators_after = new_store.get_locators("publish_button")
        # Now //xhs-publish-btn must be 1st with weight > 20
        self.assertEqual(locators_after[0]["value"], "//xhs-publish-btn")
        self.assertGreater(locators_after[0]["weight"], 20)

    def test_record_success_with_secondary_promotes_immediately(self):
        self.store.record_success("publish_button", "//button[@class='secondary']", is_secondary=True)
        locators = self.store.get_locators("publish_button")
        self.assertEqual(locators[0]["value"], "//button[@class='secondary']")
        self.assertGreater(locators[0]["weight"], 20)


class TestSmartDriverSecondaryHit(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        initial_data = {
            "version": "1.0.0",
            "platform": "test_platform",
            "steps": {
                "test_step": {
                    "name": "測試步驟",
                    "timeout": 5,
                    "locators": [
                        {"by": "xpath", "value": "//button[@id='fail_btn']", "weight": 20},
                        {"by": "xpath", "value": "//button[@id='success_btn']", "weight": 10}
                    ]
                }
            }
        }
        with open(self.temp_file.name, "w", encoding="utf-8") as f:
            json.dump(initial_data, f)
        self.store = KnowledgeStore(self.temp_file.name)
        self.mock_driver = MagicMock()
        self.mock_vision = MagicMock()
        self.mock_vision.is_available.return_value = False
        self.smart_driver = SmartDriver(self.mock_driver, self.store, self.mock_vision)
        self.tracker = OperationTrailTracker.get_instance()
        self.tracker.clear()

    def tearDown(self):
        self.tracker.clear()
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    @patch("video_rpa.core.smart_driver.WebDriverWait")
    def test_secondary_hit_records_trail_and_promotes(self, mock_wait_cls):
        # Configure WebDriverWait: fail for first locator, succeed for second locator
        mock_wait_inst = MagicMock()
        mock_elem = MagicMock()

        def until_side_effect(condition):
            if mock_wait_inst.until.call_count == 1:
                raise Exception("First locator not found")
            return mock_elem

        mock_wait_inst.until.side_effect = until_side_effect
        mock_wait_cls.return_value = mock_wait_inst

        result = self.smart_driver.find_smart_element("test_step")
        self.assertEqual(result, mock_elem)

        # Verify trail record was captured
        self.assertEqual(len(self.tracker.records), 1)
        record = self.tracker.records[0]
        self.assertEqual(record.step_id, "test_step")
        self.assertEqual(record.hit_index, 2)
        self.assertEqual(record.original_primary, "//button[@id='fail_btn']")
        self.assertEqual(record.hit_locator, "//button[@id='success_btn']")

        # Verify KnowledgeStore was promoted so next time //button[@id='success_btn'] is first
        reloaded_store = KnowledgeStore(self.temp_file.name)
        reloaded_locators = reloaded_store.get_locators("test_step")
        self.assertEqual(reloaded_locators[0]["value"], "//button[@id='success_btn']")
        self.assertGreater(reloaded_locators[0]["weight"], 20)


if __name__ == "__main__":
    unittest.main()
