import logging
import os
import time
from typing import List, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from constants.auto_append_hashtag import AutoAppendHashtag
from selenium_impl.core.knowledge_store import KnowledgeStore
from selenium_impl.core.smart_driver import SmartDriver
from selenium_impl.core.vision_analyzer import VisionAnalyzer
try:
    from selenium_impl.utils.webdriver_util import WebDriverUtil
except ImportError:
    from utils.webdriver_util import WebDriverUtil

logger = logging.getLogger(__name__)


class YouTubeService:
    """YouTube upload automation service powered by self-healing SmartDriver,
    screen prompt detection, and KnowledgeStore evolution."""

    def __init__(self, knowledge_file: Optional[str] = None):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        default_file = os.path.normpath(os.path.join(current_dir, "..", "knowledge", "youtube_knowledge.json"))
        self.store = KnowledgeStore(knowledge_file or default_file)
        self.vision = VisionAnalyzer()
        self.smart_driver: Optional[SmartDriver] = None

    def _ensure_smart_driver(self, driver):
        if self.smart_driver is None or self.smart_driver.driver != driver:
            self.smart_driver = SmartDriver(driver, self.store, self.vision)

    def upload_video(self, file_path: str, title: str, description: str, playlist: str, visibility: str,
                     hashtags: List[str], keep_open_on_failure: bool) -> bool:
        driver = None
        success = False
        try:
            driver = WebDriverUtil.initialize_driver()
            self._ensure_smart_driver(driver)
            self.start_upload_form(driver, file_path, title, description, playlist, visibility, hashtags)
            self.wait_and_publish(driver)
            success = True
            return True
        except Exception as e:
            logger.error(f"Error during YouTube upload: {e}", exc_info=True)
            return False
        finally:
            if driver is not None:
                if success or not keep_open_on_failure:
                    driver.quit()
                    logger.info("Browser closed successfully.")
                else:
                    logger.warning("Browser left open for debugging.")

    def start_upload_form(self, driver, file_path: str, title: str, description: str, playlist: str,
                          visibility: str, hashtags: List[str]):
        self._ensure_smart_driver(driver)
        final_description = self._build_description(title, description, hashtags)
        self._navigate_to_studio(driver)
        self._click_create_button(driver)
        self._select_upload_option(driver)
        self._upload_file(driver, file_path)
        self._enter_title_and_description(driver, title, final_description)
        self._select_playlist(driver, playlist)
        self._set_kids_restriction(driver)
        self._navigate_wizard_pages(driver)
        self._set_visibility(driver, visibility)

    def wait_and_publish(self, driver):
        self._ensure_smart_driver(driver)
        self._save_and_close(driver)

    def _build_description(self, title: str, description: str, hashtags: List[str]) -> str:
        if not description:
            description = ""
        description += "\n\n"

        if hashtags:
            for tag in hashtags:
                if tag not in description:
                    description += f"#{tag} "

        if title:
            for keyword in AutoAppendHashtag.AUTO_HASHTAG_KEYWORDS:
                if keyword in title:
                    description += f"#{keyword} "

        return description

    def _navigate_to_studio(self, driver):
        logger.info("步驟 : 前往 YouTube Studio (https://studio.youtube.com)...")
        driver.get("https://studio.youtube.com")
        self.smart_driver.check_and_dismiss_known_popups()

        time.sleep(2)
        current_url = driver.current_url.lower()
        if "accounts.google.com" in current_url or "signin" in current_url:
            print("\n" + "=" * 64)
            print("🚨 [登入檢查] 檢測到 YouTube / Google 尚未登入或憑證已失效！")
            print("瀏覽器已停留在登入頁面，請在開啟的視窗中完成 Google 登入。")
            print("系統正即時偵測中，登入成功後將自動無縫接續上傳流程...")
            print("=" * 64 + "\n")
            logger.warning("檢測到 YouTube 尚未登入，等待使用者在瀏覽器完成登入中 (最長等待 5 分鐘)...")

            login_start = time.time()
            while time.time() - login_start < 300:
                time.sleep(3)
                current_url = driver.current_url.lower()
                if "accounts.google.com" not in current_url and "signin" not in current_url:
                    print("\n✅ 檢測到 YouTube 登入成功！繼續執行上傳流程...\n")
                    logger.info("✅ 檢測到 YouTube 登入成功，繼續執行上傳流程。")
                    driver.get("https://studio.youtube.com")
                    time.sleep(3)
                    break
            else:
                raise RuntimeError("YouTube 登入等待逾時 (5分鐘)，請重新執行。")

        # Handle optional 'Continue' button if present
        continue_elem = self.smart_driver.find_smart_element("continue_button", custom_timeout=3)
        if continue_elem:
            try:
                continue_elem.click()
                logger.info("Clicked Studio Continue button.")
            except Exception:
                pass

    def _click_create_button(self, driver):
        logger.info("步驟 : 點擊建立按鈕...")
        self.smart_driver.check_and_dismiss_known_popups()
        if not self.smart_driver.click_step("upload_button", timeout=10):
            raise RuntimeError("無法定位或點擊建立/上傳按鈕 (Create Button)。")

    def _select_upload_option(self, driver):
        logger.info("步驟 : 選擇上傳影片選項...")
        # Check if file input is already present without clicking menu
        try:
            if driver.find_elements(By.XPATH, "//input[@type='file']"):
                return
        except Exception:
            pass

        self.smart_driver.click_step("select_upload_option", timeout=8)

    def _upload_file(self, driver, file_path: str):
        if not file_path:
            raise ValueError("File path cannot be null or empty")
        logger.info(f"步驟 : 上傳檔案 {file_path}...")
        file_input = self.smart_driver.find_smart_element("file_input", timeout=12)
        if file_input:
            file_input.send_keys(file_path)
            logger.info(f"Sent file path: {file_path}")
        else:
            raise RuntimeError("無法定位上傳檔案輸入框 (File input)。")

    def _enter_title_and_description(self, driver, title: str, description: str):
        if title:
            logger.info(f"步驟 : 設定標題: {title}")
            self.smart_driver.input_step("title_input", title)

        if description:
            logger.info("步驟 : 設定說明內容...")
            self.smart_driver.input_step("description_input", description)

    def _select_playlist(self, driver, playlist: str):
        if not playlist:
            return
        logger.info(f"步驟 : 選擇播放清單: {playlist}")
        try:
            self.smart_driver.click_step("playlist_trigger", timeout=8)
            time.sleep(1)

            item_selector = (
                f"//li[contains(@class, 'ytcp-checkbox-group') and "
                f".//span[contains(@class, 'label-text') and normalize-space(text())='{playlist}']]//div[@id='checkbox-container']"
            )
            item = WebDriverWait(driver, 6).until(EC.element_to_be_clickable((By.XPATH, item_selector)))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", item)
            item.click()
            logger.info(f"Selected playlist: {playlist}")

            self.smart_driver.click_step("playlist_done_button", timeout=6)
        except Exception as e:
            logger.warning(f"Could not select playlist '{playlist}': {e}")

    def _set_kids_restriction(self, driver):
        logger.info("步驟 : 設定兒童限制選項 (非兒童專屬)...")
        self.smart_driver.click_step("kids_restriction_not_for_kids", timeout=10)

    def _navigate_wizard_pages(self, driver):
        logger.info("步驟 : 推進嚮導頁面...")
        for i in range(3):
            logger.info(f"推進嚮導步驟 {i + 1}/3...")
            time.sleep(1)
            self.smart_driver.click_step("next_button", timeout=10)

    def _set_visibility(self, driver, visibility: str):
        vis = "PUBLIC"
        if visibility and visibility.upper() in ["PUBLIC", "UNLISTED", "PRIVATE"]:
            vis = visibility.upper()

        step_id = f"visibility_{vis.lower()}"
        logger.info(f"步驟 : 設定公開性為 {vis} (step_id: {step_id})...")
        self.smart_driver.click_step(step_id, timeout=8)

    def _save_and_close(self, driver):
        logger.info("步驟 : 點擊發布/完成按鈕...")
        self.smart_driver.check_and_dismiss_known_popups()
        self.smart_driver.click_step("done_button", timeout=15)
        logger.info("已點擊 Done/Publish 按鈕。")

        # Check for potential 'Publish anyway' popup
        time.sleep(2)
        self.smart_driver.check_and_dismiss_known_popups()

        # Dismiss final success dialog if present
        self.smart_driver.click_step("close_dialog_button", timeout=15)
        logger.info("YouTube 影片發布流程全部完成！")
