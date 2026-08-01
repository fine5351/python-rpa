import os
import sys
import unittest
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.window_grabber import WindowGrabber
from utils.ocr_engine import OCREngine
from utils.config_loader import ConfigLoader
from utils.game_controller import GameController

class TestFullPipelineFlow(unittest.TestCase):
    def setUp(self):
        self.grabber = WindowGrabber()
        self.ocr = OCREngine()
        self.config_loader = ConfigLoader("config.yml")
        self.controller = GameController(self.grabber)

    def test_grid_coordinates_progression(self):
        """
        驗證 4 行 x 9 列 (共 36 格) 座標推算非重疊且呈現單調遞增
        """
        prev_x = -1
        prev_y = -1
        cell_count = 0

        coords = []
        for row in range(4):
            row_y = None
            for col in range(6):
                cx, cy = self.grabber.get_grid_cell_center(row, col)
                coords.append((row, col, cx, cy))
                cell_count += 1

                # 同行的 Y 座標應相同，X 座標應向右遞增
                if row_y is None:
                    row_y = cy
                else:
                    self.assertEqual(cy, row_y, f"Row {row} Col {col} Y 座標未對齊: {cy} != {row_y}")
                
                if col > 0:
                    prev_col_x = coords[-2][2]
                    self.assertGreater(cx, prev_col_x, f"Col {col} X 座標未能向右遞增: {cx} <= {prev_col_x}")

        self.assertEqual(cell_count, 24, "絕區零驅動倉庫一頁應剛好為 24 格 (4行 x 6列)")

    def test_complete_decision_and_action_flow(self):
        """
        驗證「取得數值 -> 分析 -> 棄置/鎖定/強化 -> 下一個」之完整狀態機運轉
        """
        mock_drives = [
            # 1. Lv15 神裝 -> 應標記鎖定 🔒
            {
                'name': '拂曉行紀', 'slot': 1, 'level': 15, 'main_stat': '生命值',
                'substat_details': [
                    {'std_name': '暴擊率', 'full_text': '暴擊率 +2 7.2%', 'plus_count': 2, 'total_rolls': 3},
                    {'std_name': '攻擊力', 'full_text': '攻擊力 +1 6%', 'plus_count': 1, 'total_rolls': 2}
                ],
                'expected_action': 'LOCK'
            },
            # 2. Lv15 垃圾裝 -> 應標記棄置 🗑️
            {
                'name': '啄木鳥電音', 'slot': 2, 'level': 15, 'main_stat': '攻擊力',
                'substat_details': [
                    {'std_name': '防禦力', 'full_text': '防禦力 +3 45', 'plus_count': 3, 'total_rolls': 4},
                    {'std_name': '生命值', 'full_text': '生命值 112', 'plus_count': 0, 'total_rolls': 1}
                ],
                'expected_action': 'TRASH'
            },
            # 3. Lv1 可強化裝 -> 應觸發強化 ⚡
            {
                'name': '震星迪斯科', 'slot': 4, 'level': 1, 'main_stat': '衝擊力',
                'substat_details': [
                    {'std_name': '暴擊率', 'full_text': '暴擊率 2.4%', 'plus_count': 0, 'total_rolls': 1},
                    {'std_name': '暴擊傷害', 'full_text': '暴擊傷害 4.8%', 'plus_count': 0, 'total_rolls': 1}
                ],
                'expected_action': 'ENHANCE'
            },
            # 4. Lv1 廢裝 -> 應直接棄置 🗑️
            {
                'name': '藍調搖滾', 'slot': 5, 'level': 1, 'main_stat': '生命值%',
                'substat_details': [
                    {'std_name': '防禦力', 'full_text': '防禦力 15', 'plus_count': 0, 'total_rolls': 1}
                ],
                'expected_action': 'TRASH'
            }
        ]

        action_log = []

        for idx, drive in enumerate(mock_drives):
            row = idx // 9
            col = idx % 9
            
            # 1. 取得數值 (模擬點擊並獲取 OCR 結果)
            cx, cy = self.grabber.get_grid_cell_center(row, col)
            name = drive['name']
            slot = drive['slot']
            level = drive['level']
            main_stat = drive['main_stat']
            substat_details = drive['substat_details']

            # 2. 分析 (使用 ConfigLoader 進行權重決策)
            if level >= 15:
                should_lock, rule_name, types_cnt, min_thresh, rolls_cnt, desc = self.config_loader.evaluate_drive_level15(
                    name, slot, main_stat, substat_details
                )
                action = 'LOCK' if should_lock else 'TRASH'
            else:
                should_enhance, rule_name, initial_matched = self.config_loader.evaluate_drive_under15(
                    name, slot, main_stat, substat_details
                )
                action = 'ENHANCE' if should_enhance else 'TRASH'

            # 3. 棄置或鎖定或強化
            self.assertEqual(action, drive['expected_action'], 
                             f"驅動盤 #{idx+1} ({name}) 決策行動不符預期: {action} != {drive['expected_action']}")
            
            action_log.append({
                'cell': f"R{row+1}C{col+1}",
                'pos': (cx, cy),
                'name': name,
                'level': level,
                'action': action
            })

        print("\n=== 管道完整測試紀錄 ===")
        for log in action_log:
            print(f"位置: {log['cell']} {log['pos']} | 驅動盤: {log['name']} (Lv.{log['level']}) -> 執行動作: {log['action']}")

if __name__ == '__main__':
    unittest.main()
