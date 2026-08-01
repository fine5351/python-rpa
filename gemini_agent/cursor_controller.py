import sys
import ctypes
import logging
import pyautogui
from PIL import Image, ImageDraw

logger = logging.getLogger("CursorController")

# Configure PyAutoGUI safety settings
pyautogui.PAUSE = 0.5
pyautogui.FAILSAFE = True

# Windows DPI Awareness setup to avoid coordinate offset in High-DPI screens
if sys.platform == "win32":
    try:
        # 2 = PROCESS_PER_MONITOR_DPI_AWARE
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        logger.info("Windows DPI Awareness successfully set to Per-Monitor DPI Aware.")
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
            logger.info("Windows DPI Awareness set using user32.SetProcessDPIAware.")
        except Exception as e:
            logger.warning(f"Could not set Windows DPI Awareness: {e}")

class CursorController:
    """
    Handles OS Screen Capture and Mouse/Keyboard operations with Normalized (0-1000) coordinates.
    """
    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"Initialized CursorController with Screen Resolution: {self.screen_width}x{self.screen_height}")

    def get_screen_size(self) -> tuple[int, int]:
        return pyautogui.size()

    def denormalize_coords(self, nx: int, ny: int) -> tuple[int, int]:
        """
        Converts 0-1000 normalized coordinates into actual screen pixel coordinates.
        Clamps values to screen boundaries [0, width-1] and [0, height-1].
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
        Captures current screen with fallback to Dummy Canvas in headless/locked sessions.
        Optionally draws visual marker at current cursor location.
        """
        screenshot = None
        
        # Method 1: Try mss
        try:
            import mss
            with mss.MSS() as sct:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                sct_img = sct.grab(monitor)
                screenshot = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except Exception as e:
            logger.debug(f"mss screenshot failed ({e})")

        # Method 2: Fallback to pyautogui / ImageGrab
        if screenshot is None:
            try:
                screenshot = pyautogui.screenshot()
            except Exception as e:
                logger.debug(f"pyautogui screenshot failed ({e})")
                try:
                    from PIL import ImageGrab
                    screenshot = ImageGrab.grab()
                except Exception as ex:
                    logger.debug(f"PIL ImageGrab failed ({ex})")

        # Method 3: Fallback to Dummy Canvas (Headless/Locked Session Safety)
        if screenshot is None:
            w, h = pyautogui.size()
            logger.warning(f"OS Screen capture unavailable (headless or session locked). Generating {w}x{h} dummy canvas.")
            screenshot = Image.new("RGB", (w, h), color=(30, 30, 30))
            draw = ImageDraw.Draw(screenshot)
            draw.text((w // 2 - 150, h // 2), "Headless / Dummy Desktop View", fill="white")

        if draw_cursor and screenshot:
            cx, cy = pyautogui.position()
            screenshot = screenshot.copy()
            draw = ImageDraw.Draw(screenshot)
            
            # Red circle marker with crosshair
            r = 12
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline="red", width=3)
            draw.line((cx - r - 6, cy, cx + r + 6, cy), fill="red", width=2)
            draw.line((cx, cy - r - 6, cx, cy + r + 6), fill="red", width=2)
            
            # Draw a small center dot
            draw.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill="yellow")

        return screenshot

    def click_at(self, nx: int, ny: int, button: str = "left", clicks: int = 1) -> tuple[int, int]:
        """
        Moves cursor to normalized (nx, ny) and clicks.
        """
        px, py = self.denormalize_coords(nx, ny)
        logger.info(f"Clicking at normalized ({nx}, {ny}) -> Screen ({px}, {py}) with {button} button ({clicks} clicks)")
        try:
            pyautogui.moveTo(px, py, duration=0.2)
            pyautogui.click(px, py, button=button, clicks=clicks)
        except Exception as e:
            logger.warning(f"PyAutoGUI click operation exception: {e}")
        return px, py

    def move_to(self, nx: int, ny: int) -> tuple[int, int]:
        """
        Moves cursor to normalized (nx, ny) without clicking.
        """
        px, py = self.denormalize_coords(nx, ny)
        logger.info(f"Moving cursor to normalized ({nx}, {ny}) -> Screen ({px}, {py})")
        try:
            pyautogui.moveTo(px, py, duration=0.2)
        except Exception as e:
            logger.warning(f"PyAutoGUI move operation exception: {e}")
        return px, py

    def type_text(self, text: str, press_enter: bool = False):
        """
        Types text using pyautogui or clipboard paste for unicode support.
        """
        logger.info(f"Typing text (enter={press_enter}): '{text}'")
        try:
            import pyperclip
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
        except Exception:
            pyautogui.write(text, interval=0.02)

        if press_enter:
            pyautogui.press('enter')

    def scroll(self, amount: int):
        """
        Scrolls screen. Positive amount scrolls up, negative scrolls down.
        """
        logger.info(f"Scrolling screen: {amount}")
        try:
            pyautogui.scroll(amount)
        except Exception as e:
            logger.warning(f"PyAutoGUI scroll exception: {e}")

    def drag(self, start_nx: int, start_ny: int, end_nx: int, end_ny: int):
        """
        Drags cursor from start (start_nx, start_ny) to end (end_nx, end_ny).
        """
        spx, spy = self.denormalize_coords(start_nx, start_ny)
        epx, epy = self.denormalize_coords(end_nx, end_ny)
        logger.info(f"Dragging cursor from ({spx}, {spy}) to ({epx}, {epy})")
        try:
            pyautogui.moveTo(spx, spy, duration=0.2)
            pyautogui.dragTo(epx, epy, duration=0.5, button='left')
        except Exception as e:
            logger.warning(f"PyAutoGUI drag exception: {e}")
