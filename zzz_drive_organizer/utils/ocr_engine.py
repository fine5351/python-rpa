import re
from typing import Dict, List, Any, Tuple, Optional
from PIL import Image
import numpy as np

# 嘗試載入 rapidocr_onnxruntime 或 fallback 處理
try:
    from rapidocr_onnxruntime import RapidOCR
    HAS_RAPID_OCR = True
    ocr_engine_instance = RapidOCR()
except Exception:
    HAS_RAPID_OCR = False
    ocr_engine_instance = None


def normalize_text(text: str) -> str:
    """
    將 OCR 結果進行文字正規化 (包含異體字 撃->擊、簡轉繁、同義簡寫替換)
    """
    if not text:
        return ""
    
    # 常用簡轉繁與異體字對照表 (含日文異體字 撃)
    char_map = {
        '撃': '擊', '纪': '紀', '击': '擊', '伤': '傷', '害': '害',
        '防': '防', '御': '禦', '宝': '寶', '蓝': '藍',
        '调': '調', '爵': '爵', '士': '士', '摇': '搖',
        '滚': '滾', '混': '混', '沌': '沌', '极': '極',
        '地': '地', '暴': '暴', '雪': '雪', '啄': '啄',
        '木': '木', '鸟': '鳥', '电': '電', '音': '音',
        '拂': '拂', '晓': '曉', '行': '行', '震': '震',
        '星': '星', '统': '統', '通': '通'
    }
    
    res = []
    for char in text:
        res.append(char_map.get(char, char))
    
    normalized = "".join(res)
    # 針對常見關鍵字替換
    normalized = normalized.replace("暴击", "暴擊").replace("暴撃", "暴擊")
    normalized = normalized.replace("伤害", "傷害").replace("防御", "防禦")
    normalized = normalized.replace("防力", "防禦力")
    normalized = normalized.replace("拂晓行纪", "拂曉行紀").replace("拂曉行纪", "拂曉行紀")
    return normalized.strip()


STAT_KEYWORD_MAP = {
    '暴擊率': ['暴擊率', '暴撃率', '暴击率', '暴擊', '暴撃', '暴击'],
    '暴擊傷害': ['暴擊傷害', '暴撃傷害', '暴击伤害', '暴傷', '暴伤', '暴擊', '暴撃', '暴击'],
    '攻擊力': ['攻擊力', '攻撃力', '攻击力', '攻擊', '攻撃', '攻击'],
    '生命值': ['生命值', '生命'],
    '防禦力': ['防禦力', '防御力', '防力', '防禦', '防御'],
    '屬性精通': ['屬性精通', '屬性', '属性精通', '属性'],
    '穿透力': ['穿透力', '穿透', '穿透率'],
    '衝擊力': ['衝擊力', '衝撃力', '冲击力', '衝擊', '衝撃', '冲击'],
    '能量自動回復': ['能量自動回復', '能量回復', '能量回复', '能量恢复', '能量'],
    '異常精通': ['異常精通', '異常', '异常精通', '异常'],
    '物理屬性傷害': ['物理屬性傷害', '物理傷害', '物理'],
    '火屬性傷害': ['火屬性傷害', '火傷害', '火屬性', '火'],
    '冰屬性傷害': ['冰屬性傷害', '冰傷害', '冰屬性', '冰'],
    '電屬性傷害': ['電屬性傷害', '電傷害', '電屬性', '電'],
    '以太屬性傷害': ['以太屬性傷害', '以太傷害', '以太']
}

def extract_standard_stat_name(text: str) -> Optional[str]:
    """
    從 OCR 文字中提取標準繁體屬性名稱
    """
    if not text:
        return None
    for std_name, variants in STAT_KEYWORD_MAP.items():
        for var in variants:
            if var in text:
                return std_name
    return None


class OCREngine:
    """
    絕區零驅動盤 UI 專用 OCR 解析引擎
    解析：套裝名稱、部位、等級、主屬性與副屬性
    """
    def __init__(self):
        self.has_rapid_ocr = HAS_RAPID_OCR
        self.engine = ocr_engine_instance

    def recognize_image_boxes(self, img_input) -> List[Dict[str, Any]]:
        """
        將 PIL Image 或 numpy ndarray 輸入 OCR 引擎，返回包含 BBox、Y 座標與同列水平合併後的清單
        """
        if isinstance(img_input, Image.Image):
            img_np = np.array(img_input)
        else:
            img_np = img_input

        raw_results = []
        if self.has_rapid_ocr and self.engine:
            try:
                ocr_res, _ = self.engine(img_np)
                if ocr_res:
                    for line in ocr_res:
                        box, raw_text, score = line[0], line[1], float(line[2])
                        text = normalize_text(raw_text)
                        y_center = (box[0][1] + box[2][1]) / 2.0
                        x_center = (box[0][0] + box[1][0]) / 2.0
                        raw_results.append({
                            'text': text,
                            'raw_text': raw_text,
                            'box': box,
                            'y_center': y_center,
                            'x_center': x_center,
                            'score': score
                        })
            except Exception as e:
                print(f"[OCR Exception] RapidOCR Error: {e}")

        # 先依照 Y 座標粗略排序
        raw_results.sort(key=lambda item: item['y_center'])

        # 同水平列 (Row Merging) 方框合併：將 Y 軸差距小於 14px 的文字框進行水平拼接
        merged_rows: List[List[Dict[str, Any]]] = []
        for item in raw_results:
            placed = False
            for row in merged_rows:
                avg_y = sum(i['y_center'] for i in row) / len(row)
                if abs(item['y_center'] - avg_y) < 14.0:
                    row.append(item)
                    placed = True
                    break
            if not placed:
                merged_rows.append([item])

        results = []
        for row in merged_rows:
            row.sort(key=lambda item: item['x_center'])
            combined_text = " ".join([i['text'] for i in row])
            combined_raw = " ".join([i['raw_text'] for i in row])
            avg_y = sum(i['y_center'] for i in row) / len(row)
            min_x = min(i['x_center'] for i in row)
            box_0 = row[0]['box']
            box_last = row[-1]['box']
            combined_box = [box_0[0], box_last[1], box_last[2], box_0[3]]

            results.append({
                'text': combined_text,
                'raw_text': combined_raw,
                'box': combined_box,
                'y_center': avg_y,
                'x_center': min_x,
                'score': sum(i['score'] for i in row) / len(row)
            })

        # 最終依照平均 Y 座標由上至下排序
        results.sort(key=lambda item: item['y_center'])
        return results

    def parse_drive_detail(self, detail_crop_img: Image.Image) -> Dict[str, Any]:
        """
        解析右側 DETAIL 區塊截圖 (基於同列合併後的雙向關鍵字解析主屬性與副屬性)
        """
        lines = self.recognize_image_boxes(detail_crop_img)

        parsed = {
            'name': '未知驅動盤',
            'slot': 1,
            'level': 1,
            'main_stat': '',
            'substats': [],
            'raw_texts': [l['text'] for l in lines]
        }

        if not lines:
            return parsed

        # 1. 尋找套裝名稱與部位 [x]
        for l in lines:
            t = l['text']
            if '[' in t and ']' in t:
                slot_match = re.search(r'\[(\d+)\]', t)
                if slot_match:
                    parsed['slot'] = int(slot_match.group(1))
                parsed['name'] = re.sub(r'\[.*?\]', '', t).strip()
                break
            elif any(kw in t for kw in ['拂曉', '啄木鳥', '極地', '震星', '混沌', '藍調', '爵士', '搖滾', '自由', '河谷', '河谷之歌', '炎獄', '靜音']):
                parsed['name'] = t.strip()
                break

        # 若未能在標題找到部位，尋找頂部獨立數字 (1~6)
        if parsed['slot'] == 1:
            for l in lines[:5]:
                t = l['text'].strip()
                if t in ['1', '2', '3', '4', '5', '6']:
                    parsed['slot'] = int(t)
                    break

        # 2. 尋找等級 (例如 '等級15/15', '等級 15/15', '15/15', '1/15')
        for l in lines:
            t = l['text']
            if '等級' in t or '/15' in t or '等' in t:
                lvl_match = re.search(r'(\d+)\s*/\s*15', t)
                if lvl_match:
                    parsed['level'] = int(lvl_match.group(1))
                    break
                else:
                    digit_match = re.search(r'15|12|9|6|3|1|0', t)
                    if digit_match:
                        parsed['level'] = int(digit_match.group(0))
                        break

        # 3. 收集所有包含屬性關鍵字的文字列 (同列合併後)
        attr_items = []
        for l in lines:
            t_norm = l['text']
            t_raw = l['raw_text']
            # 排除純標題與按鈕標籤
            if t_norm not in ['主屬性', '主性', '副屬性', '副性', '套裝效果', '查裝效果', 'DETAIL', '查看', '解除鎖定', '鎖定', '標記棄置']:
                std_name = extract_standard_stat_name(t_norm) or extract_standard_stat_name(t_raw)
                if std_name:
                    attr_items.append({
                        'std_name': std_name,
                        'full_text': t_norm,
                        'line_info': l
                    })

        if attr_items:
            # 第一條屬性列為「主屬性」
            parsed['main_stat'] = attr_items[0]['std_name']

            # 第二條及之後出現的屬性列為「副屬性」 (最多 4 條)
            substats_found = []
            substat_details = []

            for item in attr_items[1:]:
                txt = item['full_text']
                raw = item['line_info']['raw_text']

                # 尋找 +N 加成次數
                plus_match = re.search(r'\+(\d+)', txt) or re.search(r'\+(\d+)', raw)
                plus_count = int(plus_match.group(1)) if plus_match else 0
                total_rolls = 1 + plus_count  # 初始 1 條 + 強化升級次數

                if txt not in substats_found:
                    substats_found.append(txt)
                    substat_details.append({
                        'std_name': item['std_name'],
                        'full_text': txt,
                        'plus_count': plus_count,
                        'total_rolls': total_rolls
                    })

            parsed['substats'] = substats_found[:4]
            parsed['substat_details'] = substat_details[:4]

        return parsed

if __name__ == '__main__':
    ocr = OCREngine()
    print(f"RapidOCR available: {ocr.has_rapid_ocr}")
