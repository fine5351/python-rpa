import os
import sys
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.ocr_engine import OCREngine
from utils.config_loader import ConfigLoader

def test_screenshot_212021():
    img_path = r"F:\Download\Snipaste_2026-07-25_21-20-21.png"
    if not os.path.exists(img_path):
        print(f"Test image not found: {img_path}")
        return

    img = Image.open(img_path)
    ocr = OCREngine()
    parsed = ocr.parse_drive_detail(img)

    print("\n========== 圖片 Snipaste_2026-07-25_21-20-21.png OCR 結果 ==========")
    print(f"驅動盤名稱: '{parsed['name']}'")
    print(f"部位 (Slot): {parsed['slot']}")
    print(f"等級 (Level): Lv.{parsed['level']}")
    print(f"主屬性 (Main Stat): '{parsed['main_stat']}'")
    print(f"副屬性 (Substats): {parsed['substats']}")
    print(f"副屬性詳情 (Substat Details): {parsed.get('substat_details', [])}")

    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../config.yml'))
    loader = ConfigLoader(config_path)

    should_lock, rule_name, types_cnt, min_thresh, rolls_cnt, desc_list = loader.evaluate_drive_level15(
        parsed['name'], parsed['slot'], parsed['main_stat'], parsed.get('substat_details', [])
    )
    print("\n========== 評估結果 ==========")
    print(f"是否鎖定: {should_lock}")
    print(f"符合配置: [{rule_name}]")
    print(f"匹配有效屬性種類: {types_cnt} 種 (門檻: {min_thresh})")
    print(f"有效總詞條數 (含+N): {rolls_cnt} 條 (暴擊率+3算4, 暴擊傷害算1)")
    print(f"詳細匹配列表: {desc_list}")

if __name__ == '__main__':
    test_screenshot_212021()
