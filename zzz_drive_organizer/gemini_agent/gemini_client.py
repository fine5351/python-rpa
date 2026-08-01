import os
import io
import logging
from PIL import Image
from dotenv import load_dotenv

# 自動載入 .env 變數
load_dotenv()

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

logger = logging.getLogger("GeminiClient")

def build_system_instruction(config_rules_text: str = "") -> str:
    return f"""
你是作業系統級別的 AI 電腦操作代理人 (Gemini OS Vision Agent)。
你擁有獨立觀察螢幕截圖並發動滑鼠游標移動、點擊與鍵盤輸入的能力。

【當前任務專用領域 - 絕區零驅動盤整理與篩選】：
{config_rules_text if config_rules_text else "對照雙暴 (暴擊率, 暴擊傷害, 攻擊力%) 與有效詞條，達標留存/鎖定，否則標記棄置。"}

【電腦操作與視覺觀察核心準則】：
1. 畫面採用 0~1000 正規化座標系統 (Normalized 0-1000 Grid)：
   - (0, 0) 代表螢幕左上角，(1000, 1000) 代表右下角，(500, 500) 為正中央。
   - 截圖中的紅色圈圈與十字標記，代表【滑鼠游標目前停放的位置】。
2. 每次產生回應時，你**必須**先在文字中輸出你的視覺觀察與思考流程（Visual Inspection Step）：
   - 【視覺觀察】：說明目前游標在哪裡、選中的驅動盤面板寫了什麼（套裝、部位、主屬性、副屬性列表）。
   - 【規則比對】：此驅動盤是否符合留下/鎖定條件。
   - 【下個動作】：決定點擊鎖頭、點擊棄置垃圾桶、或是點擊下一個驅動盤格子。
3. 觀察完畢後，**呼叫單一最精確的電腦操作工具 (Function Call)**。

4. 可用的電腦操作工具庫 (Computer Operator Tools)：
   - mouse_click(x, y, button, description): 移動游標至 (x, y) 座標並點擊
   - mouse_move(x, y, description): 僅移動游標至 (x, y) 座標
   - keyboard_type(text, press_enter, description): 輸入文字
   - keyboard_press(key_name, description): 按下單一按鍵 (例如 'esc', 'enter', 'tab')
   - mouse_scroll(x, y, amount, description): 移動至 (x, y) 並滾動畫面 (負數向下滾動)
   - finish_agent(success, message): 全數驅動盤皆檢查完畢後，結束電腦操作任務。

5. **【連續處理規範 - 防止提前結束】**：
   - 完成一個驅動盤的【鎖定】或【棄置】標記後，**請立即點擊下一個驅動盤圖示格子 (從左到右，從上到下)**。
   - 絕不要在只處理一個驅動盤後就呼叫 finish_agent！只有當整個倉庫/畫面中再無未檢查的驅動盤時才能結束。
"""

def get_tool_declarations():
    tools = [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="mouse_click",
                    description="將滑鼠游標移動至螢幕 0~1000 正規化座標 (x, y) 並發動點擊",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "x": types.Schema(type="INTEGER", description="X 軸座標 (0~1000)"),
                            "y": types.Schema(type="INTEGER", description="Y 軸座標 (0~1000)"),
                            "button": types.Schema(type="STRING", description="按鍵類型 ('left', 'right', 'double')"),
                            "description": types.Schema(type="STRING", description="詳細動作說明 (例如：點擊第1行第2個驅動盤 / 點擊棄置垃圾桶 / 點擊鎖頭)")
                        },
                        required=["x", "y"]
                    )
                ),
                types.FunctionDeclaration(
                    name="mouse_move",
                    description="僅移動滑鼠游標至 0~1000 正規化座標 (x, y)",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "x": types.Schema(type="INTEGER", description="X 軸座標 (0~1000)"),
                            "y": types.Schema(type="INTEGER", description="Y 軸座標 (0~1000)"),
                            "description": types.Schema(type="STRING", description="移動說明")
                        },
                        required=["x", "y"]
                    )
                ),
                types.FunctionDeclaration(
                    name="keyboard_type",
                    description="在當前焦點視窗中打字/輸入文字",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "text": types.Schema(type="STRING", description="要輸入的文字"),
                            "press_enter": types.Schema(type="BOOLEAN", description="輸入後是否按 Enter"),
                            "description": types.Schema(type="STRING", description="打字說明")
                        },
                        required=["text"]
                    )
                ),
                types.FunctionDeclaration(
                    name="keyboard_press",
                    description="按下鍵盤單一按鍵 (如 'esc', 'enter', 'tab', 'f5')",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "key_name": types.Schema(type="STRING", description="按鍵名稱"),
                            "description": types.Schema(type="STRING", description="按鍵說明")
                        },
                        required=["key_name"]
                    )
                ),
                types.FunctionDeclaration(
                    name="mouse_scroll",
                    description="移動至 (x, y) 並滾動滑鼠滾輪 (負數向下滾動頁面)",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "x": types.Schema(type="INTEGER", description="X 軸座標 (0~1000)"),
                            "y": types.Schema(type="INTEGER", description="Y 軸座標 (0~1000)"),
                            "amount": types.Schema(type="INTEGER", description="滾動量 (負數向下滾動，如 -300)"),
                            "description": types.Schema(type="STRING", description="滾動說明")
                        },
                        required=["x", "y", "amount"]
                    )
                ),
                types.FunctionDeclaration(
                    name="finish_agent",
                    description="當畫面/倉庫中所有驅動盤均已檢查並標記完成後，呼叫此函數結束 Agent 操作",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "success": types.Schema(type="BOOLEAN", description="任務是否成功完成"),
                            "message": types.Schema(type="STRING", description="任務完成報告總結")
                        },
                        required=["success", "message"]
                    )
                )
            ]
        )
    ]
    return tools

class GeminiClient:
    def __init__(self, api_key: str = None, model_name: str = "gemini-2.5-flash", config_rules_text: str = ""):
        if genai is None:
            raise RuntimeError("The 'google-genai' SDK is not installed. Run 'pip install google-genai'.")
        
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("未偵測到 GEMINI_API_KEY！請確認已有在 .env 檔案中設定 GEMINI_API_KEY。")

        self.client = genai.Client(api_key=self.api_key) if self.api_key else genai.Client()
        self.model_name = model_name
        self.system_instruction = build_system_instruction(config_rules_text)
        logger.info(f"Gemini Vision OS Client 已初始化 (模型: {self.model_name})")

    def generate_next_action(self, image: Image.Image, user_goal: str, action_history: list[str]) -> tuple[str, list]:
        """
        Sends screenshot and context to Gemini API.
        Returns a tuple of (thought_text, function_calls).
        """
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()

        history_text = "\n".join(action_history[-6:]) if action_history else "（尚無歷史動作）"
        prompt_content = (
            f"【任務目標】：{user_goal}\n"
            f"【近期已執行的電腦操作歷史】：\n{history_text}\n\n"
            f"請細心觀察螢幕截圖，先輸出【視覺觀察與分析】：列出右側詳情面板的驅動盤屬性與當前游標位置；"
            f"接著發動電腦操作工具 (mouse_click / mouse_scroll 等)，依序檢視並標記倉庫中的每個驅動盤。"
        )

        contents = [
            types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
            prompt_content
        ]

        config = types.GenerateContentConfig(
            system_instruction=self.system_instruction,
            tools=get_tool_declarations(),
            temperature=0.1
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=config
        )

        thought_text = response.text or ""
        function_calls = response.function_calls or []

        return thought_text, function_calls
