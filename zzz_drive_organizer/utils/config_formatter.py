import os
import yaml
import logging

logger = logging.getLogger("ConfigFormatter")

def load_and_format_config(config_path: str = "config.yml") -> tuple[dict, str]:
    """
    載入 config.yml 並轉換為 Gemini Prompt 易於理解的中文規則文字
    """
    if not os.path.exists(config_path):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, "config.yml")

    if not os.path.exists(config_path):
        logger.warning(f"找不到配置檔案: {config_path}，使用預設規則。")
        return {}, "無特定 config 設定，依據通用雙暴原則整理。"

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"讀取 config.yml 失敗: {e}")
        return {}, "讀取配置失敗，依據通用原則整理。"

    global_settings = cfg.get("global_settings", {})
    default_rules = cfg.get("default_rules", [])
    drives = cfg.get("drives", [])

    lines = []
    lines.append("【預設通用留存門檻】:")
    for rule in default_rules:
        name = rule.get("rule_name", "通用規則")
        substats = ", ".join(rule.get("desirable_substats", []))
        thresh = rule.get("min_threshold", 2)
        lines.append(f"  - [{name}]: 有效副屬性包含({substats})，所需符合條數 >= {thresh} 條。")

    if drives:
        lines.append("\n【特定套裝留存與鎖定規則】:")
        for drive in drives:
            d_name = drive.get("name", "")
            for r in drive.get("rules", []):
                r_name = r.get("rule_name", "")
                slots = r.get("slots", "不限部位")
                main_stats = r.get("desirable_main_stats", [])
                sub_stats = r.get("desirable_substats", [])
                thresh = r.get("min_threshold", 2)

                main_str = f"，要求主屬性為 [{', '.join(main_stats)}]" if main_stats else ""
                sub_str = f"，有效副屬性為 [{', '.join(sub_stats)}]" if sub_stats else ""
                lines.append(f"  - [{d_name}] 部位 {slots}{main_str}{sub_str} -> 達 {thresh} 條以上則【鎖定/留存】，否則【廢棄】。")

    formatted_text = "\n".join(lines)
    return cfg, formatted_text
