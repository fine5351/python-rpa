# 絕區零 (Zenless Zone Zero) 驅動盤自動整理腳本

本專案是一個專為《絕區零》設計的驅動盤自動化整理腳本。透過影像辨識 (OCR) 與自動化控制，依照使用者在 `config.yml` 中設定的詞條條件與門檻，自動判定驅動盤要**鎖定**或**棄置**。

---

## 🌟 核心功能特點

1. **`config.yml` 靈活配置**：
   - 支持設定各個驅動盤 (套裝名稱) 的**所需詞條 (Desirable Substats)** 與**門檻詞條數 (Min Threshold)**。
   - 支援全域預設規則 (`default_rule`)，未單獨設定的驅動盤將自動套用預設門檻。
2. **智慧等級與詞條判定邏輯**：
   - **等級等於 15 的驅動盤**：
     - 若符合「所需詞條」的數量 $\ge$ 門檻詞條數 $\rightarrow$ 點擊**鎖定** 🔒。
     - 若未達到門檻詞條數 $\rightarrow$ 點擊**棄置** 🗑️。
   - **等級不足 15 的驅動盤 (如 Level 1)**：
     - 檢查初始副屬性符合「所需詞條」的數量是否 $\ge 2$ 條。
     - 若符合 $\ge 2$ 條 $\rightarrow$ 自動執行**強化至 Lv 15** $\rightarrow$ 重新讀取 15 級後的副屬性 $\rightarrow$ 依據 Lv 15 門檻規則執行**鎖定**或**棄置**。
     - 若符合 $< 2$ 條 $\rightarrow$ 直接點擊**棄置** 🗑️。
3. **全自動分頁與滾動**：
   - 一次性整理所有驅動盤。當一頁 (4 行 $\times$ 9 列 = 36 格) 整理完畢後，自動向下滾動 4 行繼續處理下一頁。
4. **熱鍵快捷控制**：
   - `F5`：啟動 / 繼續自動整理腳本。
   - `F6`：暫停 / 停止自動整理腳本。

---

## 📁 檔案結構

```text
D:\work\workspace\python\rpa\zzz_drive_organizer/
├── config.yml                # 詞條門檻與規則配置文件
├── requirements.txt          # Python 依賴清單
├── main.py                   # 主程式 (含 F5/F6 熱鍵與主邏輯)
├── README.md                 # 說明文件
└── utils/
    ├── __init__.py
    ├── config_loader.py      # yml 配置檔解析與詞條比對模組
    ├── window_grabber.py     # 遊戲視窗定位與相對座標轉換模組
    ├── ocr_engine.py         # 驅動盤名稱、等級、副屬性 OCR 解析引擎
    └── game_controller.py    # 模擬滑鼠點擊、強化、鎖定、棄置與滾動
```

---

## ⚙️ `config.yml` 配置說明

您可以在 `config.yml` 檔中依據您的遊戲需求調整各大套裝驅動盤的門檻：

```yaml
global_settings:
  hotkey_start: "F5"             # 啟動熱鍵
  hotkey_stop: "F6"              # 停止熱鍵
  scroll_rows_per_page: 4        # 每頁滾動行數 (4 行)

# 預設全域規則 (未單獨設定時套用，支援多組預設配置，符合任一即鎖定)
default_rules:
  - rule_name: "通用雙暴輸出流"
    desirable_substats:
      - "暴擊率"
      - "暴擊傷害"
      - "攻擊力%"
    min_threshold: 2

  - rule_name: "通用精通輔助流"
    desirable_substats:
      - "異常精通"
      - "屬性精通"
      - "能量自動回復%"
      - "攻擊力%"
    min_threshold: 2

# 特定驅動盤規則 (支援指定部位 slots、主屬性 desirable_main_stats 與副屬性 desirable_substats)
drives:
  - name: "拂曉行紀"
    rules:
      # 配置一：1 號位專用 (主屬性: 生命值, 副屬性: 攻擊力%, 暴擊率, 暴擊傷害)
      - rule_name: "1號位-雙暴輸出"
        slots: [1]                       # 指定套用於 1 號位 (可填 [1, 2] 等)
        desirable_main_stats:            # 指定允許的主屬性 (1號位為固定生命值)
          - "生命值"
        desirable_substats:              # 所需副屬性
          - "攻擊力%"
          - "暴擊率"
          - "暴擊傷害"
        min_threshold: 2                 # 副屬性達 2 條鎖定

      # 配置二：4 號位專用 (主屬性要求暴擊率或暴擊傷害)
      - rule_name: "4號位-雙暴主C"
        slots: [4]
        desirable_main_stats:
          - "暴擊率"
          - "暴擊傷害"
        desirable_substats:
          - "攻擊力%"
          - "暴擊率"
          - "暴擊傷害"
          - "穿透力"
        min_threshold: 2
```

---

## 🚀 使用步驟

1. **安裝依賴套件**：
   ```bash
   pip install -r requirements.txt
   ```
2. **啟動腳本**：
   ```bash
   python main.py
   ```
3. **開啟遊戲**：
   - 開啟《絕區零》遊戲畫面，進入**驅動倉庫**頁面。
   - 按下 **`F5`** 鍵啟動自動整理！
   - 需要暫停或停止時，隨時按下 **`F6`** 鍵即可。
