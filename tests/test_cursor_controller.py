import os
import unittest
from PIL import Image
from gemini_agent.cursor_controller import CursorController
from gemini_agent.gemini_client import get_tool_declarations

class TestCursorController(unittest.TestCase):
    def setUp(self):
        self.controller = CursorController()

    def test_screen_size(self):
        w, h = self.controller.get_screen_size()
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)

    def test_denormalize_coords_clamping(self):
        w, h = self.controller.get_screen_size()
        
        # 1. Normal middle coords (500, 500)
        px, py = self.controller.denormalize_coords(500, 500)
        self.assertAlmostEqual(px, w // 2, delta=2)
        self.assertAlmostEqual(py, h // 2, delta=2)

        # 2. Top-Left (0, 0)
        px0, py0 = self.controller.denormalize_coords(0, 0)
        self.assertEqual(px0, 0)
        self.assertEqual(py0, 0)

        # 3. Bottom-Right (1000, 1000)
        px1000, py1000 = self.controller.denormalize_coords(1000, 1000)
        self.assertEqual(px1000, w - 1)
        self.assertEqual(py1000, h - 1)

        # 4. Out of bounds values (-100, 1500)
        px_oob, py_oob = self.controller.denormalize_coords(-100, 1500)
        self.assertEqual(px_oob, 0)
        self.assertEqual(py_oob, h - 1)

    def test_capture_screen(self):
        img = self.controller.capture_screen(draw_cursor=True)
        self.assertIsInstance(img, Image.Image)
        w, h = self.controller.get_screen_size()
        self.assertEqual(img.width, w)
        self.assertEqual(img.height, h)

    def test_tool_declarations(self):
        tools = get_tool_declarations()
        self.assertGreater(len(tools), 0)
        fn_names = [fn.name for fn in tools[0].function_declarations]
        self.assertIn("click_at", fn_names)
        self.assertIn("type_text", fn_names)
        self.assertIn("finish_task", fn_names)

if __name__ == "__main__":
    unittest.main()
