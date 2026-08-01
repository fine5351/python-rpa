# Implementation Plan - Gemini API 視覺與游標自動化 Agent 轉換

## 1. 目標與背景脈絡
將原本固化的 Python Selenium DOM 腳本轉換為接入 Google Gemini API（Multimodal Vision）的 OS/GUI 游標自動控制 Agent。
當前專案原本僅能透過固定 DOM 元素進行腳本化操作；轉換後，系統將透過螢幕截圖（Screenshot）、Gemini 視覺模型識別畫面座標與元件，並動態操控滑鼠游標（移動、點擊、拖曳、滾動）及鍵盤，實現視覺 AI 自主控制游標運作。

---

## 2. 預期變更檔案與模組清單

| 檔案/模組 | 變更類型 | 說明 |
| --- | --- | --- |
| `requirements.txt` | MODIFY | 新增 `google-genai`, `pyautogui`, `pillow`, `pynput`, `mss` |
| `gemini_agent/__init__.py` | NEW | 模組初始化 |
| `gemini_agent/cursor_controller.py` | NEW | 封裝 OS 游標與鍵盤控制、DPI Awareness 座標校準 (0-1000 Normalized 座標)、截圖繪製游標紅點標記、Headless 畫面容錯與安全中斷 (PyAutoGUI Fail-Safe) |
| `gemini_agent/gemini_client.py` | NEW | 封裝 Gemini API (Multimodal Vision) 通訊、環境變數 `GEMINI_API_KEY` 讀取、Function Calling / Tools 定義與 Prompt |
| `gemini_agent/agent_loop.py` | NEW | 核心控制循環：捕捉截圖 -> 呼叫 Gemini Vision -> 解析 Tool Call 操作游標 -> 死循環防爆機制 (`max_steps` / 重複動作監控) -> 循環運作 |
| `gemini_agent_main.py` | NEW | CLI 入口檔案，允許輸入自然語言目標指令並啟動 Agent |
| `tests/test_cursor_controller.py` | NEW | 游標控制器與截圖基本功能單元測試 |

---

## 3. 實作步驟與細節設計

### 階段一：依賴與基礎游標控制層 (Cursor Controller)
1. 更新 `requirements.txt` 並安裝所需依賴。
2. 實作 `gemini_agent/cursor_controller.py`：
   - **DPI Awareness 校正**：呼叫 `ctypes.windll.shcore.SetProcessDpiAwareness(2)` (Windows 系統) 確保 PyAutoGUI 的 `size()` 與截圖實體像素 1:1 吻合，防止高 DPI (125%, 150%) 導致點擊座標偏離。
   - **0-1000 Normalized 座標系統**：將畫面水平與垂直切割為 0~1000 比例座標，便於 Gemini API 高精確度定位，再動態映射為實際螢幕像素 `(x * width / 1000, y * height / 1000)`。
   - **螢幕截圖與游標繪製**：`capture_screen()` 抓取目前畫面並在游標目前位置繪製醒目的紅色十字標記，方便 Gemini Vision 評估游標位置。
   - **游標與鍵盤動作**：`move_cursor(x, y)`, `click(x, y, button, clicks)`, `type_text(text, enter)`, `scroll(clicks)`, `drag(start_x, start_y, end_x, end_y)`。
   - **Fail-Safe 安全防護**：啟用 PyAutoGUI Fail-Safe (將游標移動至螢幕左上角角落或按 Ctrl+C 強制中斷)。

### 階段二：Gemini Client 與 Vision Tool Calling 整合
1. 實作 `gemini_agent/gemini_client.py`：
   - **API Key 保護**：優先讀取環境變數 `os.environ.get("GEMINI_API_KEY")`，嚴格防範寫死金鑰或未授權建立 `.env` 檔案。
   - **使用 Gemini API SDK (`google-genai`)** 呼叫 `gemini-2.5-flash` 或 `gemini-2.0-flash` 模型。
   - **定義 Function Calling Tools**：
     - `click_at(x, y, description)`: 水平/垂直範圍皆為 0~1000 的 Normalized 座標點擊。
     - `type_text(text, press_enter, description)`: 在當前焦點輸入文字。
     - `scroll_screen(direction, amount)`: 畫面滾動。
     - `finish_task(success, message)`: 任務結束宣告。

### 階段三：Agent 控制主循環 (Agent Loop) & 入口
1. 實作 `gemini_agent/agent_loop.py`：
   - 輸入：`user_prompt` (自然語言目標)。
   - 防死循環機制：設定 `max_steps = 15`，記錄歷史動作，若連續 3 次無效果自動中斷。
   - Loop 流程：
     1. 擷取帶游標標記的螢幕畫面 `screenshot`。
     2. 傳送畫面與歷史對話給 Gemini Vision 模型。
     3. 接收 Gemini 的 Function Call 指令。
     4. 呼叫 `CursorController` 執行實體滑鼠游標移動與點擊操作。
     5. 反饋執行結果與新截圖給 Gemini。
     6. 若觸發 `finish_task` 或達到 `max_steps` 則終止退出。
2. 實作 `gemini_agent_main.py` CLI 介面。

---

## 4. 驗證方法 (Verification Strategy)

1. **基礎功能驗證**：
   - 執行 `python -m unittest discover -s tests` 驗證 DPI 校準、截圖標記與座標轉換無誤。（已通過測試！）
2. **Gemini API 與 Function Calling 驗證**：
   - 驗證 `GeminiClient` 在提供 `GEMINI_API_KEY` 時能正常建立連接並返回 Tools Function Call。
3. **實機游標自動操作驗證**：
   - 執行 `python gemini_agent_main.py --prompt "測試游標移動與點擊"` 進行端對端測試。

---

## 5. 完成標準 (Done Criteria)
- [x] **DC-1**: 實作計畫通過 Debate Agent 審查，防範 DPI Scaling、API Key 保護與死循環風險。
- [x] **DC-2**: `CursorController` 實現 Windows DPI Awareness 座標校正、游標視覺標記截圖與安全 Fail-Safe。
- [x] **DC-3**: `GeminiClient` 成功對接 Gemini 視覺 API，實作安全金鑰載入與 0-1000 座標 Tool Calling。
- [x] **DC-4**: `AgentLoop` 完成自主循環整合（含 `max_steps` 防暴走），能在自然語言指令下自動捕捉畫面並操控游標完成任務。
