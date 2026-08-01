# -*- coding: utf-8 -*-
import os
import sys
import time
import ctypes
import threading
import argparse
import logging
from dotenv import load_dotenv

# 載入 .env 環境變數 (參照 game-assistant 機制)
load_dotenv()

# 設定根目錄路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from utils.config_formatter import load_and_format_config
from gemini_agent.gemini_client import GeminiClient
from gemini_agent.agent_loop import AgentLoop

# Setup basic logging to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ZZZ_Drive_Organizer")

def check_and_elevate_admin():
    """
    檢查是否具備系統管理員權限 (Windows UIPI 限制普通權限對全螢幕視窗發送點擊)
    """
    if sys.platform != "win32":
        return
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        is_admin = False

    if not is_admin:
        print("\n=====================================================================")
        print("【⚠️ 權限提示】當前終端機尚未取得「系統管理員權限」！")
        print("  Windows UIPI 會封鎖普通權限對遊戲視窗發送滑鼠點擊。")
        print("  👉 建議以『系統管理員身分執行』PowerShell / CMD！")
        print("=====================================================================\n")
        try:
            script = os.path.abspath(sys.argv[0])
            params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, f'"{script}" {params}', None, 1
            )
        except Exception:
            pass

class ZZZDriveOrganizerAgent:
    def __init__(self, config_path: str = "config.yml", max_steps: int = 50):
        check_and_elevate_admin()
        
        # 載入 config.yml 配置
        self.raw_config, self.rules_text = load_and_format_config(config_path)
        logger.info("\n=== 已成功加載 config.yml 驅動盤整理規則 ===")
        print(self.rules_text)
        print("===================================================\n")

        # 取得 API Key
        self.api_key = os.getenv("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("【警告】未偵測到 GEMINI_API_KEY！請確認已有在 .env 檔案中設定 GEMINI_API_KEY。")

        # 初始化 Gemini API Client 與 Agent Loop
        self.client = GeminiClient(api_key=self.api_key, config_rules_text=self.rules_text)
        self.agent_loop = AgentLoop(gemini_client=self.client, max_steps=max_steps)
        self.is_running = False
        self.worker_thread = None

        # 熱鍵註冊 (F5 啟動 / F6 暫停)
        self._setup_hotkeys()

    def _setup_hotkeys(self):
        try:
            import keyboard
            global_cfg = self.raw_config.get('global_settings', {})
            hk_start = global_cfg.get('hotkey_start', 'F5')
            hk_stop = global_cfg.get('hotkey_stop', 'F6')

            print(f"[系統訊息] 熱鍵註冊完成：[{hk_start}] 啟動/繼續整理，[{hk_stop}] 暫停/停止整理")
            keyboard.add_hotkey(hk_start, self.start_organizing)
            keyboard.add_hotkey(hk_stop, self.stop_organizing)
        except Exception as e:
            logger.warning(f"熱鍵註冊跳過 (需權限或無鍵盤庫): {e}")

    def start_organizing(self):
        if not self.is_running:
            print("\n[F5 按下] 啟動絕區零驅動盤自動鎖定與棄置整理任務...")
            self.is_running = True
            if self.worker_thread is None or not self.worker_thread.is_alive():
                self.worker_thread = threading.Thread(target=self._run_loop, daemon=True)
                self.worker_thread.start()

    def stop_organizing(self):
        if self.is_running:
            print("\n[F6 按下] 暫停/停止驅動盤整理任務...")
            self.is_running = False

    def _run_loop(self):
        goal = (
            "依據載入的 config.yml 規則，連續檢查絕區零倉庫中的驅動盤："
            "符合留存門檻則確保【鎖定】，不符合則點擊【棄置(垃圾桶圖示)】。"
            "完成單個驅動盤標記後，請點擊下一個驅動盤圖示繼續遍歷檢查，全部處理完畢後方可結束。"
        )
        self.agent_loop.run(user_goal=goal)

    def run_direct(self):
        """
        直接啟動 Agent 運作
        """
        self._run_loop()

def main():
    parser = argparse.ArgumentParser(description="絕區零驅動盤自動鎖定與棄置 Agent (Gemini Vision 驅動)")
    parser.add_argument("--config", type=str, default="config.yml", help="配置文件路徑 (預設 config.yml)")
    parser.add_argument("--max-steps", type=int, default=50, help="Agent 最大連續整理步數 (預設 50 步)")
    parser.add_argument("--auto-start", action="store_true", default=True, help="是否自動直接啟動整理任務 (預設 True)")

    args = parser.parse_args()

    app = ZZZDriveOrganizerAgent(config_path=args.config, max_steps=args.max_steps)

    if args.auto_start:
        print("\n[自動啟動] 開始透過 Gemini Vision 進行驅動盤自動鎖定與棄置...")
        try:
            app.run_direct()
        except KeyboardInterrupt:
            logger.info("使用者中斷 (Ctrl+C)。程式結束。")
            sys.exit(0)
    else:
        print("\n[等待熱鍵] 請切換至絕區零驅動盤畫面，按下 [F5] 啟動自動整理，按 [F6] 暫停。")
        try:
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            sys.exit(0)

if __name__ == "__main__":
    main()
