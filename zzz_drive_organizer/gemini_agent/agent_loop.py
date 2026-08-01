import time
import logging
import pyautogui
from gemini_agent.cursor_controller import CursorController
from gemini_agent.gemini_client import GeminiClient

logger = logging.getLogger("AgentLoop")

class AgentLoop:
    """
    Main Execution Loop for Gemini Computer Operator Agent.
    """
    def __init__(self, gemini_client: GeminiClient = None, max_steps: int = 50):
        self.controller = CursorController()
        self.client = gemini_client or GeminiClient()
        self.max_steps = max_steps
        self.action_history = []

    def run(self, user_goal: str) -> dict:
        logger.info(f"=== 啟動 Gemini Computer Operator Agent Loop ===")
        logger.info(f"任務目標: '{user_goal}'")
        logger.info(f"最大動作限制: {self.max_steps} 步")
        
        step_count = 0
        finished = False
        final_result = {"success": False, "message": "超過最大步數限制。"}

        while step_count < self.max_steps and not finished:
            step_count += 1
            print(f"\n=======================================================")
            print(f" 🤖 Gemini OS Agent Loop - 步驟 [{step_count} / {self.max_steps}]")
            print(f"=======================================================")

            try:
                # 1. 抓取帶游標標記的最新螢幕截圖
                screenshot = self.controller.capture_screen(draw_cursor=True)

                # 2. 請求 Gemini 進行視覺辨識與決策
                logger.info("發送螢幕截圖至 Gemini Vision API 進行視覺分析與判斷...")
                thought_text, function_calls = self.client.generate_next_action(
                    screenshot, user_goal, self.action_history
                )

                if thought_text:
                    print("\n🧠 【Gemini Vision 視覺分析與思維 Log】:")
                    print(thought_text.strip())
                    print("-" * 50)

                if not function_calls:
                    logger.warning("Gemini 未返回 Tool Call，延遲 1 秒後重試...")
                    time.sleep(1.0)
                    continue

                # 3. 執行電腦操作 Tool Calls
                for call in function_calls:
                    fn_name = call.name
                    args = call.args or {}
                    desc = args.get("description", "")
                    
                    logger.info(f"👉 執行電腦動作: {fn_name}({args})")

                    if fn_name in ["mouse_click", "click_at"]:
                        x, y = int(args.get("x", 0)), int(args.get("y", 0))
                        button = str(args.get("button", "left"))
                        clicks = 2 if button == "double" else 1
                        btn = "left" if button not in ["right", "middle"] else button

                        self.controller.click_at(x, y, button=btn, clicks=clicks)
                        act_msg = f"Step {step_count}: 點擊座標 ({x}, {y}) [{btn}] - {desc}"
                        self.action_history.append(act_msg)

                    elif fn_name in ["mouse_move", "move_to"]:
                        x, y = int(args.get("x", 0)), int(args.get("y", 0))
                        self.controller.move_to(x, y)
                        act_msg = f"Step {step_count}: 移動游標至 ({x}, {y}) - {desc}"
                        self.action_history.append(act_msg)

                    elif fn_name in ["keyboard_type", "type_text"]:
                        text = str(args.get("text", ""))
                        press_enter = bool(args.get("press_enter", False))
                        self.controller.type_text(text, press_enter=press_enter)
                        act_msg = f"Step {step_count}: 打字 '{text}' (Enter={press_enter}) - {desc}"
                        self.action_history.append(act_msg)

                    elif fn_name in ["keyboard_press", "press_key"]:
                        key_name = str(args.get("key_name", "enter"))
                        self.controller.press_key(key_name)
                        act_msg = f"Step {step_count}: 按下按鍵 '{key_name}' - {desc}"
                        self.action_history.append(act_msg)

                    elif fn_name in ["mouse_scroll", "scroll_screen"]:
                        x = int(args.get("x", 500))
                        y = int(args.get("y", 500))
                        amount = int(args.get("amount", -300))
                        self.controller.scroll(x, y, amount)
                        act_msg = f"Step {step_count}: 在 ({x},{y}) 滾動畫面 ({amount}) - {desc}"
                        self.action_history.append(act_msg)

                    elif fn_name in ["finish_agent", "finish_task"]:
                        success = bool(args.get("success", True))
                        message = str(args.get("message", "電腦操作任務完成。"))
                        logger.info(f"收到結束號誌！ Success={success}, Message='{message}'")
                        finished = True
                        final_result = {"success": success, "message": message, "steps": step_count}
                        act_msg = f"Step {step_count}: 任務結束 - {message}"
                        self.action_history.append(act_msg)
                        break

                time.sleep(0.4)

            except pyautogui.FailSafeException:
                logger.error("【緊急中斷】滑鼠已被推至螢幕角落 (PyAutoGUI Fail-Safe 觸發)。")
                final_result = {"success": False, "message": "緊急中斷：滑鼠推至螢幕角落。"}
                break
            except KeyboardInterrupt:
                logger.warning("使用者中斷 (Ctrl+C)。")
                final_result = {"success": False, "message": "使用者手動中斷。"}
                break
            except Exception as e:
                logger.error(f"步驟 {step_count} 執行發生例外: {e}", exc_info=True)
                self.action_history.append(f"Step {step_count}: 發生例外 - {e}")
                time.sleep(1.0)

        logger.info(f"=== Agent Loop 結束。結果: {final_result} ===")
        return final_result
