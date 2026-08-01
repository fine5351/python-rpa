import os
import cv2
import numpy as np
from PIL import Image

class TrashIconVerifier:
    def __init__(self, template_path=None):
        if template_path is None:
            template_path = os.path.join(".screenshot", "extracted_red_box_2.png")
        
        self.template = None
        if os.path.exists(template_path):
            self.template = cv2.imread(template_path)
            if self.template is not None:
                self.template_gray = cv2.cvtColor(self.template, cv2.COLOR_BGR2GRAY)

    def check_cell_has_trash_icon(self, screen_bgr, center_x, center_y, window_width=2560, window_height=1440) -> float:
        """
        檢測指定驅動盤圖示 (center_x, center_y) 的左上角標籤區塊是否含有「棄置標記圖示」
        傳回匹配信心度分數 (0.0 ~ 1.0)
        """
        h, w, _ = screen_bgr.shape
        
        # 相對點擊中心 (center_x, center_y)，標記圖示通常位在圖示的左上方/頂部
        # 標籤區塊範圍: X: center_x - 80 ~ center_x - 10, Y: center_y - 80 ~ center_y - 20
        x1 = max(0, int(center_x - 85 * (w / 2560.0)))
        x2 = min(w, int(center_x - 5 * (w / 2560.0)))
        y1 = max(0, int(center_y - 85 * (h / 1440.0)))
        y2 = min(h, int(center_y - 15 * (h / 1440.0)))

        cell_roi = screen_bgr[y1:y2, x1:x2]

        if cell_roi.size == 0:
            return 0.0

        # 色彩特徵檢測: 棄置標記通常包含特定紅/灰顏色特徵或比對模板
        hsv_roi = cv2.cvtColor(cell_roi, cv2.COLOR_BGR2HSV)
        
        # 檢測灰色背景與暗紅色垃圾桶圖標
        lower_icon_red1 = np.array([0, 80, 80])
        upper_icon_red1 = np.array([12, 255, 255])
        lower_icon_red2 = np.array([168, 80, 80])
        upper_icon_red2 = np.array([180, 255, 255])

        m1 = cv2.inRange(hsv_roi, lower_icon_red1, upper_icon_red1)
        m2 = cv2.inRange(hsv_roi, lower_icon_red2, upper_icon_red2)
        icon_red_pixels = cv2.countNonZero(m1 | m2)

        # 灰色/暗色背景標籤特徵
        lower_gray = np.array([0, 0, 40])
        upper_gray = np.array([180, 50, 160])
        m_gray = cv2.inRange(hsv_roi, lower_gray, upper_gray)
        gray_pixels = cv2.countNonZero(m_gray)

        total_pixels = float(cell_roi.shape[0] * cell_roi.shape[1])
        score = (icon_red_pixels * 3.0 + gray_pixels) / total_pixels

        # 若有模板圖案，進行 OpenCV Template Matching
        if self.template is not None:
            try:
                roi_gray = cv2.cvtColor(cell_roi, cv2.COLOR_BGR2GRAY)
                res = cv2.matchTemplate(roi_gray, self.template_gray, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                score = max(score, max_val)
            except Exception:
                pass

        return score

    def verify_row0_acceptance(self, screen_bgr, window_grabber) -> dict:
        """
        驗收 Row 0 的 7 個驅動盤
        期望結果: Col 1 (第2個) 與 Col 3 (第4個) 得分顯著 high，確認出現棄置標記圖圖標
        """
        results = {}
        for col in range(7):
            cx, cy = window_grabber.get_grid_cell_center(0, col)
            score = self.check_cell_has_trash_icon(screen_bgr, cx, cy)
            results[f"Col_{col+1}"] = {
                "center": (cx, cy),
                "score": score,
                "is_trash_marked": score > 0.15
            }
        return results

if __name__ == '__main__':
    print("TrashIconVerifier loaded successfully.")
