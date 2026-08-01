import os
import sys
import argparse
import logging
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

from gemini_agent.gemini_client import GeminiClient
from gemini_agent.agent_loop import AgentLoop

# Setup basic logging to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GeminiAgentMain")

def main():
    parser = argparse.ArgumentParser(description="Gemini Vision Cursor Automation Agent CLI")
    parser.add_argument("--prompt", "--goal", type=str, help="自然語言目標指令 (例如: '請在螢幕上記事本打字 Hello Gemini')", required=False)
    parser.add_argument("--max-steps", type=int, default=15, help="Agent 最大連動執行步數 (預設 15 步)")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash", help="Gemini 視覺模型名稱 (預設 gemini-2.5-flash)")
    parser.add_argument("--api-key", type=str, default=None, help="Gemini API Key (如未指定則自動從 .env 或 GEMINI_API_KEY 環境變數讀取)")

    args = parser.parse_args()

    user_goal = args.prompt
    if not user_goal:
        print("\n=== Gemini Vision Cursor Agent ===")
        user_goal = input("請輸入您的目標指令 (例如: '移動游標點擊畫面中央並輸入測試文字'): ").strip()
        if not user_goal:
            logger.error("未輸入目標指令，程式結束。")
            sys.exit(1)

    api_key = args.api_key or os.getenv("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("未偵測到 GEMINI_API_KEY！請確認是否有在當前目錄下建立 .env 檔案並寫入 GEMINI_API_KEY=your_key。")

    try:
        client = GeminiClient(api_key=api_key, model_name=args.model)
        agent = AgentLoop(gemini_client=client, max_steps=args.max_steps)
        result = agent.run(user_goal=user_goal)
        print("\n執行結果報告:")
        print(f"成功狀態: {result.get('success')}")
        print(f"訊息: {result.get('message')}")
    except KeyboardInterrupt:
        logger.info("系統接收到中斷訊號，正在中斷 Gemini Agent Loop...")
        sys.exit(0)

if __name__ == "__main__":
    main()
