# -*- coding: utf-8 -*-
import os
import sys
import time
from typing import Tuple

try:
    from PIL import ImageGrab, Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import win32gui
    import win32con
    import win32api
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

class WindowGrabber:
    """
    Screen and window grabber for Zenless Zone Zero
    """
    def __init__(self, window_title_keywords: list = None):
        if window_title_keywords is None:
            self.window_title_keywords = ["絕區零", "ZenlessZoneZero", "Zenless Zone Zero"]
        else:
            self.window_title_keywords = window_title_keywords

        self.hwnd = None
        self.window_rect: Tuple[int, int, int, int] = (0, 0, 1920, 1080)

        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                import ctypes
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    def find_game_window(self) -> bool:
        """
        Find Zenless Zone Zero game window handle
        """
        if not HAS_WIN32:
            return False

        found_hwnds = []
        def enum_windows_callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if any(kw.lower() in title.lower() for kw in self.window_title_keywords):
                    found_hwnds.append((hwnd, title))
            return True

        try:
            win32gui.EnumWindows(enum_windows_callback, None)
        except Exception:
            pass

        if found_hwnds:
            hwnd, title = found_hwnds[0]
            left, top, right, bottom = win32gui.GetClientRect(hwnd)
            left_top = win32gui.ClientToScreen(hwnd, (left, top))
            right_bottom = win32gui.ClientToScreen(hwnd, (right, bottom))
            w = right_bottom[0] - left_top[0]
            h = right_bottom[1] - left_top[1]
            self.hwnd = hwnd
            self.window_rect = (left_top[0], left_top[1], w, h)
            print(f"[WindowGrabber] Found game window: {title} ({self.window_rect})")
            return True
        else:
            print("[WindowGrabber] ZZZ window not found in HWND, using default screen coords.")
            return False

    def grab_screen_area(self, area_box: Tuple[float, float, float, float] = None) -> Image.Image:
        """
        Grab screen area by ratio box (rel_x1, rel_y1, rel_x2, rel_y2)
        """
        wx, wy, ww, wh = self.window_rect

        if area_box is not None:
            rx1, ry1, rx2, ry2 = area_box
            crop_x1 = int(wx + ww * rx1)
            crop_y1 = int(wy + wh * ry1)
            crop_x2 = int(wx + ww * rx2)
            crop_y2 = int(wy + wh * ry2)
            bbox = (crop_x1, crop_y1, crop_x2, crop_y2)
        else:
            bbox = (wx, wy, wx + ww, wy + wh)

        try:
            img = ImageGrab.grab(bbox=bbox)
            return img
        except Exception as e:
            print(f"[WindowGrabber] Screen grab fallback notice: {e}")
            dummy = Image.new('RGB', (bbox[2] - bbox[0], bbox[3] - bbox[1]), color=(20, 20, 20))
            return dummy

    def get_grid_cell_center(self, row: int, col: int) -> Tuple[int, int]:
        """
        Calculate grid cell center (4 rows x 7 cols)
        start_x_ratio = 0.2270 (Col 0 = 581px at 2560x1440)
        start_y_ratio = 0.2542 (Row 0 = 366px at 2560x1440)
        """
        wx, wy, ww, wh = self.window_rect

        start_x_ratio = 0.2270
        step_x_ratio = 0.0703
        
        start_y_ratio = 0.2542
        step_y_ratio = 0.1611

        cell_x = wx + ww * (start_x_ratio + col * step_x_ratio)
        cell_y = wy + wh * (start_y_ratio + row * step_y_ratio)

        return (int(cell_x), int(cell_y))

    def get_action_button_pos(self, action_name: str) -> Tuple[int, int]:
        """
        Get action button screen coordinates
        """
        wx, wy, ww, wh = self.window_rect
        
        button_ratios = {
            'trash': (0.7535, 0.7722),               # Trash icon button (1929, 1112)
            'lock': (0.7961, 0.7722),                # Lock icon button (2038, 1112)
            'enhance': (0.8890, 0.7720),             # Enhance button (2276, 1111)
            'confirm_dialog': (0.580, 0.720),        # Standard confirm
            'lock_override_dialog': (0.569, 0.577)  # Lock override confirm (1457, 830)
        }

        rx, ry = button_ratios.get(action_name, (0.7961, 0.7722))
        return (int(wx + ww * rx), int(wy + wh * ry))

    def get_detail_area_box(self) -> Tuple[float, float, float, float]:
        """
        Get Detail area ratio box
        """
        return (0.680, 0.050, 0.990, 0.980)
