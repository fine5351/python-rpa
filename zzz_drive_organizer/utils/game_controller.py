# -*- coding: utf-8 -*-
import time
import pyautogui
from typing import Tuple

pyautogui.FAILSAFE = False

try:
    import win32gui
    import win32con
    import win32api
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

from utils.window_grabber import WindowGrabber

class GameController:
    """
    Game controller for Zenless Zone Zero RPA operation
    """
    def __init__(self, window_grabber: WindowGrabber, delay: float = 0.25):
        self.grabber = window_grabber
        self.delay = delay

    def bring_game_to_foreground(self) -> bool:
        """
        Bring game window to foreground
        """
        if not HAS_WIN32 or not self.grabber.hwnd:
            return False
        try:
            hwnd = self.grabber.hwnd
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.3)
            print("[GameController] Game window brought to foreground successfully.")
            return True
        except Exception as e:
            print(f"[GameController] Bring to foreground notice: {e}")
            return False

    def robust_click(self, x: int, y: int) -> None:
        """
        Robust click with DirectInput fallback
        """
        try:
            pyautogui.moveTo(x, y, duration=0.03)
            time.sleep(0.02)
            pyautogui.click(x, y)
        except Exception:
            pass

        if HAS_WIN32 and self.grabber.hwnd:
            try:
                lparam = win32api.MAKELONG(x, y)
                win32gui.SendMessage(self.grabber.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
                time.sleep(0.04)
                win32gui.SendMessage(self.grabber.hwnd, win32con.WM_LBUTTONUP, 0, lparam)
            except Exception:
                pass
        else:
            pyautogui.mouseDown(button='left')
            time.sleep(0.08)
            pyautogui.mouseUp(button='left')

        time.sleep(self.delay)

    def select_grid_cell(self, row: int, col: int) -> Tuple[int, int]:
        """
        Select grid cell (row: 0-3, col: 0-6)
        """
        cx, cy = self.grabber.get_grid_cell_center(row, col)
        self.robust_click(cx, cy)
        return (cx, cy)

    def handle_confirm_dialog(self, ocr_engine=None) -> None:
        """
        Confirm dialog handler with multi-point fallback
        """
        time.sleep(0.35)
        wx, wy, ww, wh = self.grabber.window_rect
        clicked_by_ocr = False

        if ocr_engine:
            try:
                dialog_crop = self.grabber.grab_screen_area((0.30, 0.45, 0.75, 0.85))
                ocr_boxes = ocr_engine.recognize_image_boxes(dialog_crop)
                
                for item in ocr_boxes:
                    txt = item['text']
                    if any(kw in txt for kw in ['確定', '確認', '分解', '棄置', 'OK', 'Confirm']):
                        rel_x = item['x_center'] / float(dialog_crop.width)
                        rel_y = item['y_center'] / float(dialog_crop.height)
                        abs_x = int(wx + ww * (0.30 + rel_x * 0.45))
                        abs_y = int(wy + wh * (0.45 + rel_y * 0.40))
                        
                        self.robust_click(abs_x, abs_y)
                        clicked_by_ocr = True
                        print(f"      [OCR Confirm] Clicked dialog confirm button at ({abs_x}, {abs_y})")
                        break
            except Exception as e:
                print(f"[GameController] OCR dialog scan notice: {e}")

        if not clicked_by_ocr:
            sweep_ratios = [
                (0.569, 0.577), # Lock override dialog confirm (1457px, 830px)
                (0.580, 0.720), # Standard confirm right
                (0.600, 0.680), # High confirm
                (0.500, 0.720)  # Center confirm
            ]

            for rx, ry in sweep_ratios:
                click_x = int(wx + ww * rx)
                click_y = int(wy + wh * ry)
                self.robust_click(click_x, click_y)
                time.sleep(0.08)

            try:
                pyautogui.press('enter')
                time.sleep(0.05)
                pyautogui.press('space')
            except Exception:
                pass

        time.sleep(0.15)

    def click_lock_button(self) -> None:
        """
        Click lock button (Key T)
        """
        bx, by = self.grabber.get_action_button_pos('lock')
        print(f"      [Action] Click Lock Button | Coords: ({bx}, {by})")
        self.robust_click(bx, by)
        try:
            pyautogui.press('t')
        except Exception:
            pass

    def click_trash_button(self, ocr_engine=None) -> None:
        """
        Click trash button (Key R) and handle popup
        """
        bx, by = self.grabber.get_action_button_pos('trash')
        print(f"      [Action] Click Trash Button | Coords: ({bx}, {by})")
        self.robust_click(bx, by)
        try:
            pyautogui.press('r')
        except Exception:
            pass

        self.handle_confirm_dialog(ocr_engine)

    def perform_enhance_to_15(self, ocr_engine=None) -> bool:
        """
        Perform auto enhance to Level 15
        """
        print("[GameController] Starting enhance to Level 15 process...")
        wx, wy, ww, wh = self.grabber.window_rect

        ex, ey = self.grabber.get_action_button_pos('enhance')
        self.robust_click(ex, ey)
        time.sleep(0.5)

        auto_add_x = int(wx + ww * 0.75)
        auto_add_y = int(wy + wh * 0.85)
        self.robust_click(auto_add_x, auto_add_y)
        time.sleep(0.3)

        confirm_x = int(wx + ww * 0.88)
        confirm_y = int(wy + wh * 0.85)
        self.robust_click(confirm_x, confirm_y)
        time.sleep(1.2)

        self.handle_confirm_dialog(ocr_engine)

        pyautogui.click(int(wx + ww * 0.5), int(wy + wh * 0.1))
        time.sleep(0.2)
        pyautogui.press('escape')
        time.sleep(0.4)

        print("[GameController] Enhance to Level 15 completed.")
        return True

    def scroll_down_pages(self, rows: int = 4) -> None:
        """
        Scroll down grid by specified rows
        """
        wx, wy, ww, wh = self.grabber.window_rect
        cx, cy = self.grabber.get_grid_cell_center(2, 3)

        try:
            pyautogui.moveTo(cx, cy, duration=0.05)
            time.sleep(0.05)
            scroll_amount = -int(rows * 180)
            pyautogui.scroll(scroll_amount)
            print(f"      [Action] Scroll down {rows} rows at ({cx}, {cy})")
        except Exception:
            pass

        time.sleep(0.4)
