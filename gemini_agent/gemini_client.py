import os
import io
import logging
from PIL import Image
from dotenv import load_dotenv

# 載入 .env 環境變數 (參照 game-assistant 機制)
load_dotenv()

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

logger = logging.getLogger("GeminiClient")

SYSTEM_INSTRUCTION = """
你是能夠自動操控電腦 OS/GUI 的 AI 助手 (Gemini Vision Cursor Agent)。
你將收到使用者傳送的「任務目標描述」與「當前螢幕截圖」。

重點規則說明：
1. 螢幕畫面採用 0~1000 的 Normalized 座標系統：
   - (0, 0) 代表畫面左上角。
   - (1000, 1000) 代表畫面右下角。
   - (500, 500) 代表畫面中央正中心。
2. 截圖畫面上若有紅色圈圈與十字線，代表【當前游標停留的位置】。
3. 每次觀察畫面後，你必須判斷下一步該執行的動作，並**呼叫對應的工具 (Function Call)**。
4. 可用的工具包含：
   - click_at(x, y, description): 點擊指定座標 (x, y 在 0~1000 範圍內)
   - right_click_at(x, y, description): 右鍵點擊
   - double_click_at(x, y, description): 雙擊
   - type_text(text, press_enter, description): 輸入文字
   - scroll_screen(amount, description): 滾動螢幕 (正值向上, 負值向下)
   - drag_and_drop(start_x, start_y, end_x, end_y, description): 拖曳游標
   - finish_task(success, message): 任務宣告結束或無法繼續
5. 一次請呼叫一個最主要的工具動作。若任務已完成，請務必呼叫 finish_task。
"""

def get_tool_declarations():
    """
    Returns tool definitions for Gemini API using google-genai SDK.
    """
    tools = [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="click_at",
                    description="點擊螢幕上的 Normalized 座標 (0~1000)",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "x": types.Schema(type="INTEGER", description="X 軸座標 (0~1000)"),
                            "y": types.Schema(type="INTEGER", description="Y 軸座標 (0~1000)"),
                            "description": types.Schema(type="STRING", description="此點擊動作之說明")
                        },
                        required=["x", "y"]
                    )
                ),
                types.FunctionDeclaration(
                    name="right_click_at",
                    description="在螢幕上的 Normalized 座標 (0~1000) 點擊滑鼠右鍵",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "x": types.Schema(type="INTEGER", description="X 軸座標 (0~1000)"),
                            "y": types.Schema(type="INTEGER", description="Y 軸座標 (0~1000)"),
                            "description": types.Schema(type="STRING", description="此右鍵動作之說明")
                        },
                        required=["x", "y"]
                    )
                ),
                types.FunctionDeclaration(
                    name="double_click_at",
                    description="在螢幕上的 Normalized 座標 (0~1000) 雙擊滑鼠左鍵",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "x": types.Schema(type="INTEGER", description="X 軸座標 (0~1000)"),
                            "y": types.Schema(type="INTEGER", description="Y 軸座標 (0~1000)"),
                            "description": types.Schema(type="STRING", description="此雙擊動作之說明")
                        },
                        required=["x", "y"]
                    )
                ),
                types.FunctionDeclaration(
                    name="type_text",
                    description="在當前焦點或輸入框中鍵入文字",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "text": types.Schema(type="STRING", description="欲輸入的文字內容"),
                            "press_enter": types.Schema(type="BOOLEAN", description="輸入完後是否按下 Enter 鍵"),
                            "description": types.Schema(type="STRING", description="輸入文字之說明")
                        },
                        required=["text"]
                    )
                ),
                types.FunctionDeclaration(
                    name="scroll_screen",
                    description="滾動螢幕",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "amount": types.Schema(type="INTEGER", description="滾動量 (正數向上, 負數向下)"),
                            "description": types.Schema(type="STRING", description="滾動動作說明")
                        },
                        required=["amount"]
                    )
                ),
                types.FunctionDeclaration(
                    name="drag_and_drop",
                    description="從起點座標拖曳至終點座標",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "start_x": types.Schema(type="INTEGER", description="起點 X 座標 (0~1000)"),
                            "start_y": types.Schema(type="INTEGER", description="起點 Y 座標 (0~1000)"),
                            "end_x": types.Schema(type="INTEGER", description="終點 X 座標 (0~1000)"),
                            "end_y": types.Schema(type="INTEGER", description="終點 Y 座標 (0~1000)"),
                            "description": types.Schema(type="STRING", description="拖曳動作說明")
                        },
                        required=["start_x", "start_y", "end_x", "end_y"]
                    )
                ),
                types.FunctionDeclaration(
                    name="finish_task",
                    description="當任務完成或無法繼續時呼叫此函數結束 Agent 循環",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "success": types.Schema(type="BOOLEAN", description="任務是否成功完成"),
                            "message": types.Schema(type="STRING", description="任務完成總結與訊息說明")
                        },
                        required=["success", "message"]
                    )
                )
            ]
        )
    ]
    return tools

class GeminiClient:
    def __init__(self, api_key: str = None, model_name: str = "gemini-2.5-flash"):
        if genai is None:
            raise RuntimeError("The 'google-genai' SDK is not installed. Run 'pip install google-genai'.")
        
        # 優先從傳入參數取得，次之從 dotenv/環境變數 OS 讀取
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("未偵測到 GEMINI_API_KEY！請確認已在 .env 檔案中設定 GEMINI_API_KEY 或設定環境變數。")

        self.client = genai.Client(api_key=self.api_key) if self.api_key else genai.Client()
        self.model_name = model_name
        logger.info(f"GeminiClient 已初始化 (模型: {self.model_name})")

    def generate_next_action(self, image: Image.Image, user_goal: str, action_history: list[str]) -> list:
        """
        Sends screenshot, user goal, and action history to Gemini Vision model,
        returning the function calls generated by the model.
        """
        # Buffer PIL Image to PNG Bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()

        # Build prompt context
        history_text = "\n".join(action_history) if action_history else "（尚無歷史動作）"
        prompt_content = (
            f"【任務目標】：{user_goal}\n"
            f"【過去已執行的動作歷史】：\n{history_text}\n\n"
            f"請觀察當前螢幕截圖，決定下一步應採取的游標/鍵盤動作呼叫。"
        )

        contents = [
            types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
            prompt_content
        ]

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=get_tool_declarations(),
            temperature=0.1
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=config
        )

        function_calls = []
        if response.function_calls:
            function_calls = response.function_calls
        return function_calls
