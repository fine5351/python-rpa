import sys
import time
import ctypes
import logging
import pyautogui
from PIL import Image, ImageDraw

logger = logging.getLogger("CursorController")

# PyAutoGUI Safety settings
pyautogui.PAUSE = 0.2
pyautogui.FAILSAFE = True

# Win32 Mouse Event Constants
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_ABSOLUTE = 0x8000

class CursorController:
    """
    OS Level Cursor and Keyboard Operator supporting direct Win32 API and PyAutoGUI.
    """
    def __init__(self):
        self._init_dpi()
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"Initialized OS Cursor Controller with Resolution: {self.screen_width}x{self.screen_height}")

    def _init_dpi(self):
        if sys.platform == "win32":
            try:
                # Set Per-Monitor DPI Awareness
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass

    def get_screen_size(self) -> tuple[int, int]:
        return pyautogui.size()

    def get_cursor_position(self) -> tuple[int, int]:
        return pyautogui.position()

    def denormalize_coords(self, nx: int, ny: int) -> tuple[int, int]:
        """
        Converts 0-1000 normalized coordinates into actual screen pixel coordinates.
        """
        width, height = pyautogui.size()
        nx = max(0, min(1000, nx))
        ny = max(0, min(1000, ny))

        px = int((nx / 1000.0) * width)
        py = int((ny / 1000.0) * height)

        px = max(0, min(width - 1, px))
        py = max(0, min(height - 1, py))
        return px, py

    def capture_screen(self, draw_cursor: bool = True) -> Image.Image:
        """
        Captures full desktop screen and draws current cursor position.
        """
        screenshot = None
        # Try mss
        try:
            import mss
            with mss.MSS() as sct:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                sct_img = sct.grab(monitor)
                screenshot = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except Exception:
            pass

        # Fallback pyautogui / ImageGrab
        if screenshot is None:
            try:
                screenshot = pyautogui.screenshot()
            except Exception:
                try:
                    from PIL import ImageGrab
                    screenshot = ImageGrab.grab()
                except Exception:
                    w, h = pyautogui.size()
                    screenshot = Image.new("RGB", (w, h), color=(30, 30, 30))

        if draw_cursor and screenshot:
            cx, cy = pyautogui.position()
            screenshot = screenshot.copy()
            draw = ImageDraw.Draw(screenshot)
            
            # Red pointer circle & crosshair
            r = 15
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline="red", width=3)
            draw.line((cx - r - 8, cy, cx + r + 8, cy), fill="red", width=2)
            draw.line((cx, cy - r - 8, cx, cy + r + 8), fill="red", width=2)
            draw.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill="yellow")

        return screenshot

    def move_to(self, nx: int, ny: int):
        """
        Moves OS cursor to normalized (nx, ny) position using both Win32 SetCursorPos and PyAutoGUI.
        """
        px, py = self.denormalize_coords(nx, ny)
        logger.info(f"[OS Agent Action] Moving cursor to normalized ({nx}, {ny}) -> Screen ({px}, {py})")
        
        if sys.platform == "win32":
            ctypes.windll.user32.SetCursorPos(px, py)
        pyautogui.moveTo(px, py, duration=0.15)

    def click_at(self, nx: int, ny: int, button: str = "left", clicks: int = 1):
        """
        Moves cursor and performs mouse click.
        """
        px, py = self.denormalize_coords(nx, ny)
        logger.info(f"[OS Agent Action] Click at normalized ({nx}, {ny}) -> Screen ({px}, {py}) [{button}, {clicks} clicks]")
        
        # Move first
        self.move_to(nx, ny)
        time.sleep(0.1)

        # Execute Click via PyAutoGUI or Win32 API
        if sys.platform == "win32":
            ctypes.windll.user32.SetCursorPos(px, py)
            down_flag = MOUSEEVENTF_LEFTDOWN if button == "left" else MOUSEEVENTF_RIGHTDOWN
            up_flag = MOUSEEVENTF_LEFTUP if button == "left" else MOUSEEVENTF_RIGHTUP
            for _ in range(clicks):
                ctypes.windll.user32.mouse_event(down_flag, 0, 0, 0, 0)
                time.sleep(0.05)
                ctypes.windll.user32.mouse_event(up_flag, 0, 0, 0, 0)
                time.sleep(0.05)
        else:
            pyautogui.click(px, py, button=button, clicks=clicks)

    def type_text(self, text: str, press_enter: bool = False):
        """
        Types text via clipboard paste or write.
        """
        logger.info(f"[OS Agent Action] Typing text: '{text}' (Enter={press_enter})")
        try:
            import pyperclip
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
        except Exception:
            pyautogui.write(text, interval=0.02)

        if press_enter:
            pyautogui.press('enter')

    def press_key(self, key_name: str):
        """
        Presses a single key (e.g. 'esc', 'enter', 'tab', 'f5').
        """
        logger.info(f"[OS Agent Action] Pressing key: '{key_name}'")
        pyautogui.press(key_name)

    def scroll(self, nx: int, ny: int, amount: int):
        """
        Moves to (nx, ny) and scrolls screen.
        """
        px, py = self.denormalize_coords(nx, ny)
        logger.info(f"[OS Agent Action] Scroll at ({px}, {py}) with amount: {amount}")
        self.move_to(nx, ny)
        pyautogui.scroll(amount)

    def drag(self, start_nx: int, start_ny: int, end_nx: int, end_ny: int):
        """
        Drags mouse from start to end position.
        """
        spx, spy = self.denormalize_coords(start_nx, start_ny)
        epx, epy = self.denormalize_coords(end_nx, end_ny)
        logger.info(f"[OS Agent Action] Dragging from ({spx}, {spy}) to ({epx}, {epy})")
        self.move_to(start_nx, start_ny)
        pyautogui.dragTo(epx, epy, duration=0.5, button='left')
