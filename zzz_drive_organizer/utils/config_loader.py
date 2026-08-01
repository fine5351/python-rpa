import os
import yaml
from typing import Dict, List, Any, Optional, Tuple

from utils.ocr_engine import normalize_text

class ConfigLoader:
    def __init__(self, config_path: str = "config.yml"):
        if not os.path.isabs(config_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            abs_config_path = os.path.join(base_dir, config_path)
            if os.path.exists(abs_config_path):
                config_path = abs_config_path

        self.config_path = config_path
        self.global_settings: Dict[str, Any] = {}
        self.default_rules: List[Dict[str, Any]] = []
        self.drive_rules: List[Dict[str, Any]] = []
        self.load_config()

    def load_config(self) -> None:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"找不到配置文件: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        self.global_settings = data.get('global_settings', {})
        
        # 載入 default_rules (支援多組 default_rules 陣列或單一 default_rule)
        if 'default_rules' in data and isinstance(data['default_rules'], list):
            self.default_rules = data['default_rules']
        elif 'default_rule' in data:
            if isinstance(data['default_rule'], list):
                self.default_rules = data['default_rule']
            elif isinstance(data['default_rule'], dict) and 'rules' in data['default_rule']:
                self.default_rules = data['default_rule']['rules']
            else:
                self.default_rules = [data['default_rule']]
        else:
            self.default_rules = [{
                'rule_name': '預設通用配置',
                'desirable_substats': ['暴擊率', '暴擊傷害', '攻擊力%'],
                'min_threshold': 2
            }]

        self.drive_rules = data.get('drives', [])

    def get_rules_for_drive(self, drive_name: str) -> List[Dict[str, Any]]:
        """
        根據驅動盤名稱取得所有匹配的配置規則列表 (支援多組配置，自動進行繁簡與模糊匹配)
        """
        clean_name = normalize_text(drive_name.strip())
        matched_rules = []

        for drive_cfg in self.drive_rules:
            target_name = normalize_text(drive_cfg.get('name', '').strip())
            if target_name and (target_name in clean_name or clean_name in target_name):
                # 支援兩種格式: 包含 rules 列表，或單一規則格式
                if 'rules' in drive_cfg and isinstance(drive_cfg['rules'], list):
                    matched_rules.extend(drive_cfg['rules'])
                else:
                    matched_rules.append(drive_cfg)

        if not matched_rules:
            matched_rules.extend(self.default_rules)

        return matched_rules

    def is_rule_applicable(self, rule: Dict[str, Any], slot: int, main_stat: str) -> bool:
        """
        檢查某條配置規則是否適用於當前部位 (slot) 與主屬性 (main_stat)
        """
        # 1. 檢查部位 (slots)
        target_slots = rule.get('slots', [])
        if target_slots and isinstance(target_slots, list):
            if slot not in target_slots:
                return False

        # 2. 檢查主屬性 (desirable_main_stats)
        desirable_mains = rule.get('desirable_main_stats', [])
        if desirable_mains and isinstance(desirable_mains, list) and main_stat:
            main_stat_clean = main_stat.strip()
            matched_main = False
            for target_main in desirable_mains:
                target_clean = target_main.strip()
                if target_clean in main_stat_clean or main_stat_clean in target_clean:
                    matched_main = True
                    break
            if not matched_main:
                return False

        return True

    def count_matching_substats_for_rule(self, rule: Dict[str, Any], substat_details: List[Dict[str, Any]]) -> Tuple[int, int, List[str]]:
        """
        計算符合單一規則的：
        1. 有效屬性種類數 (matched_types)
        2. 有效屬性總詞條數 (matched_total_rolls, 包含 +N 強化次數)
        3. 符合的詞條詳細描述列表 (matched_desc_list)
        """
        desirable = rule.get('desirable_substats', [])
        matched_types = 0
        matched_total_rolls = 0
        matched_desc_list = []

        for item in substat_details:
            std_name = item.get('std_name', '')
            full_txt = item.get('full_text', '')
            rolls = item.get('total_rolls', 1)
            plus = item.get('plus_count', 0)

            for target in desirable:
                target_clean = target.strip()
                if self._is_substat_match(target_clean, full_txt) or target_clean in std_name:
                    matched_types += 1
                    matched_total_rolls += rolls
                    desc = f"{std_name}" + (f"(+{plus})" if plus > 0 else "") + f"[{rolls}詞條]"
                    matched_desc_list.append(desc)
                    break

        return matched_types, matched_total_rolls, matched_desc_list

    def evaluate_drive_level15(self, drive_name: str, slot: int, main_stat: str, substat_details: List[Dict[str, Any]]) -> Tuple[bool, str, int, int, int, List[str]]:
        """
        針對 Level 15 的驅動盤進行多配置評估
        優先評估專屬規則；若專屬規則中無適用當前部位者，自動降級套用 default_rules
        """
        rules = self.get_rules_for_drive(drive_name)
        
        # 篩選適用於當前 slot 與 main_stat 的規則
        applicable_rules = [r for r in rules if self.is_rule_applicable(r, slot, main_stat)]
        
        # 若專屬規則中沒有適合當前部位/主屬性的，自動使用 default_rules
        if not applicable_rules and self.default_rules:
            applicable_rules = [r for r in self.default_rules if self.is_rule_applicable(r, slot, main_stat)]

        best_types = 0
        best_rolls = 0
        target_threshold = 2
        best_desc = []

        for idx, rule in enumerate(applicable_rules):
            rule_name = rule.get('rule_name', f"配置_{idx+1}")
            min_thresh = rule.get('min_threshold', 2)
            min_rolls = rule.get('min_total_rolls', 0)

            types_cnt, rolls_cnt, desc_list = self.count_matching_substats_for_rule(rule, substat_details)

            if types_cnt > best_types or (types_cnt == best_types and rolls_cnt > best_rolls):
                best_types = types_cnt
                best_rolls = rolls_cnt
                target_threshold = min_thresh
                best_desc = desc_list

            pass_types = (types_cnt >= min_thresh)
            pass_rolls = (rolls_cnt >= min_rolls) if min_rolls > 0 else True

            if pass_types and pass_rolls:
                return True, rule_name, types_cnt, min_thresh, rolls_cnt, desc_list

        return False, "無符合配置", best_types, target_threshold, best_rolls, best_desc

    def evaluate_drive_under15(self, drive_name: str, slot: int, main_stat: str, substat_details: List[Dict[str, Any]]) -> Tuple[bool, str, int]:
        """
        針對 Level < 15 的驅動盤評估初始詞條是否滿足任一適用配置的 >= 2 條
        """
        rules = self.get_rules_for_drive(drive_name)
        applicable_rules = [r for r in rules if self.is_rule_applicable(r, slot, main_stat)]
        
        if not applicable_rules and self.default_rules:
            applicable_rules = [r for r in self.default_rules if self.is_rule_applicable(r, slot, main_stat)]

        max_matched = 0
        best_rule_name = ""

        for idx, rule in enumerate(applicable_rules):
            rule_name = rule.get('rule_name', f"配置_{idx+1}")
            types_cnt, rolls_cnt, desc_list = self.count_matching_substats_for_rule(rule, substat_details)
            if types_cnt > max_matched:
                max_matched = types_cnt
                best_rule_name = rule_name

            if types_cnt >= 2:
                return True, rule_name, types_cnt

        return False, best_rule_name, max_matched

    def _is_substat_match(self, target: str, detected: str) -> bool:
        """
        副屬性比對輔助函式
        例如 target="攻擊力%", detected="攻擊力 +3.2%" 或 "攻擊力 3.2%"
        """
        # 移除加號與數值進行比對
        if '%' in target:
            # 要求 target 包含 % 且 detected 也必須包含 % 號
            if '%' not in detected:
                return False
        else:
            # 若 target 不帶 % (如固定攻擊力/生命值/防禦力/穿透值)，但 detected 帶 % 號，則不算匹配
            if '%' in detected and ('暴擊' not in target and '衝擊' not in target and '屬性' not in target):
                return False

        # 基礎文字匹配 (如 '暴擊率', '暴擊傷害', '攻擊力', '生命值', '防禦力', '精通', '穿透')
        target_keyword = target.replace('%', '').strip()
        return target_keyword in detected

if __name__ == '__main__':
    # 測試 config 載入
    loader = ConfigLoader("../../zzz_drive_organizer/config.yml")
    print("Global settings:", loader.global_settings)
    print("拂曉行紀 rule:", loader.get_rule_for_drive("拂曉行紀[1]"))
    test_substats = ["暴擊傷害 +1 9.6%", "防禦力 15", "暴擊率 +2 7.2%", "生命值 +1 6%"]
    cnt = loader.count_matching_substats("拂曉行紀[1]", test_substats)
    print(f"Matched substats count: {cnt}")
