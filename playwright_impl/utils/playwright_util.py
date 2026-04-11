import os
import sys
import logging
from playwright.async_api import BrowserContext, async_playwright

logger = logging.getLogger(__name__)

# Ensure constants works
current_dir = os.path.dirname(os.path.abspath(__file__))
rpa_root = os.path.dirname(os.path.dirname(current_dir))
if rpa_root not in sys.path:
    sys.path.insert(0, rpa_root)

class PlaywrightUtil:
    CHROME_DATA_DIR = "d:/work/workspace/java/rpa/chrome-data"
    
    @staticmethod
    async def get_browser_context(p) -> BrowserContext:
        """
        Launches a persistent browser context pointing to the specific user-data-dir.
        Using channel='chrome' uses the actual Google Chrome browser to maintain compatibility.
        """
        try:
            logger.info(f"Launching Playwright persistently in: {PlaywrightUtil.CHROME_DATA_DIR}")
            context = await p.chromium.launch_persistent_context(
                user_data_dir=PlaywrightUtil.CHROME_DATA_DIR,
                channel="chrome",
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox"
                ]
            )
            return context
        except Exception as e:
            logger.error(f"Failed to launch playwright context: {e}")
            raise
