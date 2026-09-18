# Video RPA CLI 專案 Agent 規範 (Project Agent Rules)

本文件定義本專案（Video RPA CLI 自動化影音發佈與 Gemini 視覺游標自動化系統）之專屬 Agent 行為準則、核心工程原則、多代理協同架構與領域特化規範。

- **語言規範**：一律使用繁體中文（台灣）與使用者溝通及撰寫所有規劃與紀錄文件（例如實作計畫、任務清單、驗收報告、代碼註解等）。
- **敏感憑證防護**：嚴格禁止主動讀取、寫入、傳輸或洩漏包含 `.env`、`credentials.json`、`token.json`、`token.pickle`、`id_rsa`、`.pem` 等敏感金鑰、憑證與環境變數檔案。
- **跨平台路徑規範**：專案內部所有配置、規則、文檔與程式碼註解中之檔案引用與路徑標註，**一律使用跨平台相對路徑**（以 POSIX 正斜線 `/` 表示，如 `selenium_impl/main.py`），**嚴格禁止在代碼庫中寫入特定作業系統或本機之絕對路徑**。

---

## 1. Karpathy 核心工程原則 (Karpathy Guidelines)

1. **動手前先思考 (Think Before Coding)**：實作前明確說明所有假設。若指令存在模糊空間或缺乏足夠脈絡，主動向使用者詢問以釐清需求，避免憑空猜測。
2. **簡潔至上 (Simplicity First)**：只編寫解決當前問題所需的最少程式碼，落實 YAGNI，不進行過度設計，避免添加非必要的抽象封裝或推測性功能。
3. **精準修改 (Surgical Changes)**：修改範圍嚴格限於本次請求，絕不主動重構、格式化或順便優化無關程式碼，以確保程式碼異動（diff）的乾淨度與可讀性。
4. **目標導向執行 (Goal-Driven Execution)**：將任務轉化為具體、可驗證的成功標準與驗證方法，通過客觀驗證程序方可宣告完成。

---

## 2. Loop Engineering 多代理協同架構 (Multi-Agent Architecture)

依循循環工程架構，專案遵循標準多代理角色分工與閉環演化工作流（子代理定義直接繼承全域配置）：

### 一、 核心 Agent 職責劃分
- **Planner (規劃者)**：深入分析需求規格，查閱專案既有架構與知識庫，起草實作計畫與測試情境，定義客觀量化的完成標準 (Done Criteria)。
- **Critic (批判者)**：擔任審查關卡與惡魔代言人，對比需求規格嚴格審查實作計畫，阻擋規格遺漏、死循環風險與過度設計。
- **Implementer (實作者)**：遵循核准計畫精準實作，維護 `task.md` 任務進度，嚴格落實最簡代碼與精準修改原則。
- **Tester (測試者)**：負責測試規格實現、自動化測試套件執行、品質診斷與覆蓋率分析，產出 `test_report.md`。
- **Verifier (驗證者)**：獨立唯讀審查簽核門禁，審查測試報告與執行結果，對 Done Criteria 進行最終簽核，產出 `walkthrough.md`。
- **Wiki Maintainer (知識維護者)**：分析執行軌跡與成敗根因，提煉持久模式並維護知識索引。

### 二、 協同工作流程 (Workflow)
1. **規劃與批判 (Plan & Critique)**：調用 `planner` 起草實作計畫與測試情境；調用 `critic` 進行需求合規審查。若不符合需求則退回修訂（上限 3 輪），最終提報使用者核准。
2. **實作與開發 (Implement)**：調用 `implementer` 根據核准計畫編寫程式碼與變更檔案，維護 `task.md`。
3. **測試與診斷 (Test & Diagnose)**：調用 `tester` 實現測試案例並執行測試套件、進行品質與覆蓋率診斷，產出 `test_report.md`。
4. **驗證與簽核 (Verify & Sign-off)**：由 `verifier` 獨立審閱測試報告與執行結果，對 Done Criteria 進行最終審查簽核，產出 `walkthrough.md`。
5. **熔斷與自我修正 (Circuit Breaker)**：若測試或驗證失敗，反饋錯誤日誌由 `implementer` 修正；若同一錯誤連續修正 **3 次** 仍未通過，立即中斷循環並主動向使用者回報。

---

## 3. 專案領域特化工程規範 (Video RPA & Gemini Agent Specifics)

### 一、 Selenium 影音自動發佈與四層自癒架構
專案支援 YouTube、Bilibili、小紅書 (rednote) 與 TikTok 多平台影音發佈，內建四層自癒機制：
- **Level 0 (彈窗檢查與關閉)**：優先透過 `SmartDriver` 檢查並排除已知干擾彈窗。
- **Level 1 (候選選擇器加權嘗試)**：依據平台知識庫中之權重依序嘗試選擇器。
- **Level 2 (Multimodal Vision AI)**：當所有候選選擇器皆失效時，觸發視覺模型分析畫面並定位目標元素。
- **Level 3 (人機協同介入 / HITL)**：提供人工接管與元素拾取機制。

### 二、 操作軌跡追蹤與自動首位晉升固化機制 (Operation Trail & Consolidation)
- **非首選命中追蹤**：步驟若由第 2 個（或之後）候選選擇器或 AI 定位命中，必須透過 `OperationTrailTracker` 記錄偏離軌跡。
- **即時首位晉升回寫**：生效之選擇器必須**立即晉升為 Index 0**，賦予最高權重並即時回寫至知識庫（如 `selenium_impl/knowledge/rednote_knowledge.json`），確保後續執行第 1 次就命中，消除等待延遲。
- **任務結束固化報告**：任務終止或完成時，必須於 `finally` 區塊輸出醒目的 `🚨【RPA 固化提醒】`，明確指出偏離步驟、失效原首選、新首選與建議固化之腳本檔案。

### 三、 Gemini 視覺與 OS 游標自動控制規範 (Gemini Cursor Agent)
- **Windows DPI Awareness 座標校準**：Windows 環境下必須顯式宣告 `ctypes.windll.shcore.SetProcessDpiAwareness(2)`，避免因螢幕縮放比例（125%、150% 等）導致截圖像素與滑鼠座標偏離。
- **0-1000 Normalized 座標系統**：Gemini Vision 輸出之座標必須採 0~1000 正規化比例，再動態換算為螢幕實體像素 `(x * width / 1000, y * height / 1000)`。
- **安全防護 (Fail-Safe) 與防暴走機制**：
  - 必須啟用 PyAutoGUI Fail-Safe（游標移至螢幕角落立即安全中斷）。
  - Agent 控制循環必須強制設定 `max_steps`（預設上限 15 步）與重複無效動作監控，杜絕死循環。
- **API Key 憑證防護**：僅允許讀取環境變數 `GEMINI_API_KEY`，嚴禁將 Key 寫死於原始碼中，亦嚴禁未經授權擅自建立 `.env` 檔案。

### 四、 專案測試與驗證方法
- **單元測試套件**：修改代碼後必須執行測試驗證：
  ```bash
  python -m unittest discover -s tests
  ```
  重點涵蓋 `tests/test_trail_tracker.py` 與 `tests/test_youtube_self_healing.py`。
- **待固化軌跡檢視**：
  ```bash
  python ./selenium_impl/main.py --show-trail
  ```

---

## 4. 安全防護與命令執行規範 (Security & Execution Guidelines)

1. **沙箱環境隔離與限制**：
   - 代理預設於沙箱模式 (`BypassSandbox: false`) 內運行，嚴格遵守沙箱邊界。
   - 嚴禁透過 Shell 封裝（如 `cmd /c`、`powershell -Command` 等）或命令別名規避沙箱限制。
2. **沙箱內指令免確認授權**：
   - 於沙箱模式 (`BypassSandbox: false`) 下執行下列指令時，**無需向使用者請求確認，直接執行**：
     - `node`（執行或語法檢查 JavaScript）
     - `npm` / `npx`（套件管理與執行，僅限沙箱內）
     - `python` / `py`（執行 Python 腳本）
3. **高風險操作雙重驗證 (Human-in-the-Loop)**：
   - 需繞過沙箱 (`BypassSandbox: true`) 的指令，仍須向使用者確認。
   - 刪除檔案與破壞性指令（如 `Remove-Item`、`git rm`、`git clean` 等）無論是否在沙箱內，**一律需要使用者確認**。
