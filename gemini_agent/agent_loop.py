import time
import logging
import pyautogui
from gemini_agent.cursor_controller import CursorController
from gemini_agent.gemini_client import GeminiClient

logger = logging.getLogger("AgentLoop")

class AgentLoop:
    """
    Main Execution Loop for Gemini Vision Cursor Agent.
    """
    def __init__(self, gemini_client: GeminiClient = None, max_steps: int = 15):
        self.controller = CursorController()
        self.client = gemini_client or GeminiClient()
        self.max_steps = max_steps
        self.action_history = []

    def run(self, user_goal: str) -> dict:
        logger.info(f"=== Starting Gemini Cursor Agent Loop for Goal: '{user_goal}' ===")
        logger.info(f"Max steps limit: {self.max_steps}")
        
        step_count = 0
        finished = False
        final_result = {"success": False, "message": "Task did not complete within max steps."}

        while step_count < self.max_steps and not finished:
            step_count += 1
            logger.info(f"\n--- Step {step_count} / {self.max_steps} ---")

            try:
                # 1. Capture current screen screenshot with cursor marker
                screenshot = self.controller.capture_screen(draw_cursor=True)

                # 2. Query Gemini for next action tool calls
                logger.info("Analyzing screen and requesting next action from Gemini Vision API...")
                function_calls = self.client.generate_next_action(screenshot, user_goal, self.action_history)

                if not function_calls:
                    logger.warning("No function calls returned by Gemini. Retrying step after brief pause...")
                    time.sleep(1.0)
                    continue

                # 3. Execute function calls returned by Gemini
                for call in function_calls:
                    fn_name = call.name
                    args = call.args or {}
                    desc = args.get("description", "")
                    
                    logger.info(f"Received Action Tool Call: {fn_name}({args})")

                    if fn_name == "click_at":
                        x, y = int(args.get("x", 0)), int(args.get("y", 0))
                        px, py = self.controller.click_at(x, y)
                        act_msg = f"Step {step_count}: 點擊座標 ({x}, {y}) [Screen Pixel ({px}, {py})] - {desc}"
                        self.action_history.append(act_msg)

                    elif fn_name == "right_click_at":
                        x, y = int(args.get("x", 0)), int(args.get("y", 0))
                        px, py = self.controller.click_at(x, y, button="right")
                        act_msg = f"Step {step_count}: 右鍵點擊座標 ({x}, {y}) [Screen Pixel ({px}, {py})] - {desc}"
                        self.action_history.append(act_msg)

                    elif fn_name == "double_click_at":
                        x, y = int(args.get("x", 0)), int(args.get("y", 0))
                        px, py = self.controller.click_at(x, y, clicks=2)
                        act_msg = f"Step {step_count}: 雙擊座標 ({x}, {y}) [Screen Pixel ({px}, {py})] - {desc}"
                        self.action_history.append(act_msg)

                    elif fn_name == "type_text":
                        text = str(args.get("text", ""))
                        press_enter = bool(args.get("press_enter", False))
                        self.controller.type_text(text, press_enter=press_enter)
                        act_msg = f"Step {step_count}: 輸入文字 '{text}' (Enter={press_enter}) - {desc}"
                        self.action_history.append(act_msg)

                    elif fn_name == "scroll_screen":
                        amount = int(args.get("amount", 0))
                        self.controller.scroll(amount)
                        act_msg = f"Step {step_count}: 滾動螢幕 ({amount}) - {desc}"
                        self.action_history.append(act_msg)

                    elif fn_name == "drag_and_drop":
                        sx, sy = int(args.get("start_x", 0)), int(args.get("start_y", 0))
                        ex, ey = int(args.get("end_x", 0)), int(args.get("end_y", 0))
                        self.controller.drag(sx, sy, ex, ey)
                        act_msg = f"Step {step_count}: 從 ({sx},{sy}) 拖曳至 ({ex},{ey}) - {desc}"
                        self.action_history.append(act_msg)

                    elif fn_name == "finish_task":
                        success = bool(args.get("success", True))
                        message = str(args.get("message", "Task finished."))
                        logger.info(f"Task finished call received. Success={success}, Message='{message}'")
                        finished = True
                        final_result = {"success": success, "message": message, "steps": step_count}
                        act_msg = f"Step {step_count}: 任務結束 - {message}"
                        self.action_history.append(act_msg)
                        break

                time.sleep(1.0)

            except pyautogui.FailSafeException:
                logger.error("PyAutoGUI FailSafeException triggered! Mouse was moved to screen corner.")
                final_result = {"success": False, "message": "Emergency Stop: Mouse pushed to screen corner (PyAutoGUI Fail-Safe)."}
                break
            except KeyboardInterrupt:
                logger.warning("Agent Loop interrupted by user via KeyboardInterrupt (Ctrl+C).")
                final_result = {"success": False, "message": "Interrupted by user (Ctrl+C)."}
                break
            except Exception as e:
                logger.error(f"Error during step {step_count}: {e}", exc_info=True)
                self.action_history.append(f"Step {step_count}: 發生錯誤 - {e}")
                time.sleep(1.0)

        logger.info(f"=== Agent Loop Ended. Result: {final_result} ===")
        return final_result
