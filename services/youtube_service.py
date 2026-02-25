import logging
import time
from typing import List, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from constants.auto_append_hashtag import AutoAppendHashtag
from utils.webdriver_util import WebDriverUtil

logger = logging.getLogger(__name__)

class YouTubeService:
    FIND_ELEMENT_RECURSIVE_SCRIPT = """
            function findElementRecursive(root, id, text, className, tagName) {
              if (!root) return null;
              if (id && root.id === id) return root;
              if (tagName && root.tagName === tagName.toUpperCase()) return root;
              if (className && root.classList && root.classList.contains(className)) return root;
              if (text && root.innerText && root.innerText.includes(text)) return root;
              if (root.shadowRoot) {
                var child = findElementRecursive(root.shadowRoot, id, text, className, tagName);
                if (child) return child;
              }
              if (root.children) {
                for (var i = 0; i < root.children.length; i++) {
                  var child = findElementRecursive(root.children[i], id, text, className, tagName);
                  if (child) return child;
                }
              }
              return null;
            }
            var app = document.querySelector('ytcp-app');
            var startNode = app ? app : document.body;
    """

    def upload_video(self, file_path: str, title: str, description: str, playlist: str, visibility: str,
                     hashtags: List[str], keep_open_on_failure: bool) -> bool:
        final_description = self._build_description(title, description, hashtags)
        driver = None
        success = False
        try:
            driver = WebDriverUtil.initialize_driver()
            self._navigate_to_studio(driver)
            self._click_create_button(driver)
            self._select_upload_option(driver)
            self._upload_file(driver, file_path)
            self._enter_title_and_description(driver, title, final_description)
            self._select_playlist(driver, playlist)
            self._set_kids_restriction(driver)
            self._navigate_wizard_pages(driver)
            self._set_visibility(driver, visibility)
            self._save_and_close(driver)
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
        step_name = "前往 YouTube Studio"
        logger.info(f"步驟 : {step_name}, 持續尋找中 https://studio.youtube.com...")
        driver.get("https://studio.youtube.com")
        try:
            continue_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//tp-yt-paper-button[@id='button' and .//div[contains(text(),'Continue')]]")
                )
            )
            continue_button.click()
        except Exception:
            pass

    def _handle_trust_tiers_popup(self, driver):
        logger.info("Checking for potential 'Trust Tiers' popup...")
        try:
            popup_selector = (By.XPATH, "//yt-trust-tiers-wizard-dialog")
            try:
                WebDriverWait(driver, 5).until(EC.presence_of_element_located(popup_selector))
                logger.info("'Trust Tiers' popup detected.")

                confirm_btn_selector = (By.XPATH, "//yt-trust-tiers-wizard-dialog//ytcp-button[.//div[contains(@class, 'yt-spec-touch-feedback-shape__fill')]]")
                confirm_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable(confirm_btn_selector))

                logger.info("Found confirmation button, clicking...")
                confirm_btn.click()
                logger.info("Popup dismissed.")
                time.sleep(1)
            except Exception as e:
                logger.info(f"Popup did not appear or button not found: {e}")
        except Exception as e:
            logger.warning(f"Error handling popup: {e}")

    def _click_create_button(self, driver):
        step_name = "點擊建立按鈕"
        upload_button = self._find_upload_button(driver, step_name)
        if upload_button:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", upload_button)
            upload_button = self._adjust_button_target(upload_button)
            WebDriverUtil.dispatch_click_events(driver, upload_button)
            logger.info("Dispatched click events to Upload button.")
            self._handle_trust_tiers_popup(driver)
        else:
            raise RuntimeError("Could not find any Upload/Create button.")

    def _find_upload_button(self, driver, step_name):
        element_name = "建立按鈕"
        while True:
            try:
                quick_action = self.FIND_ELEMENT_RECURSIVE_SCRIPT + """
                        var qa = findElementRecursive(startNode, null, null, null, 'YTCP-QUICK-ACTIONS');
                        return qa ? qa.querySelector('ytcp-icon-button') : null;
                        """
                btn = driver.execute_script(quick_action)
                if btn: return btn

                create_icon = self.FIND_ELEMENT_RECURSIVE_SCRIPT + """
                        return findElementRecursive(startNode, 'create-icon', null, null, null);
                        """
                btn = driver.execute_script(create_icon)
                if btn: return btn

                class_search = self.FIND_ELEMENT_RECURSIVE_SCRIPT + """
                        return findElementRecursive(startNode, null, null, 'yt-spec-touch-feedback-shape__fill', null);
                        """
                btn = driver.execute_script(class_search)
                if btn: return btn
            except Exception:
                pass

            logger.info(f"步驟 : {step_name}, 持續尋找中 {element_name}...")
            time.sleep(2)

    def _adjust_button_target(self, button):
        tag_name = button.tag_name.upper()
        if tag_name not in ["YTCP-BUTTON", "TP-YT-PAPER-ICON-BUTTON", "YTCP-ICON-BUTTON"]:
            try:
                parent = button.find_element(By.XPATH, "./..")
                if parent:
                    return parent
            except Exception:
                pass
        return button

    def _select_upload_option(self, driver):
        step_name = "點擊上傳影片選項"
        element_name = "上傳影片選項"

        try:
            WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
            return
        except Exception:
            pass

        while True:
            try:
                selector = (By.XPATH, "//tp-yt-paper-item[.//div[contains(text(),'Upload videos') or contains(text(),'上傳影片')]]")
                upload_option = WebDriverWait(driver, 5).until(EC.presence_of_element_located(selector))
                WebDriverUtil.dispatch_click_events(driver, upload_option)
                return
            except Exception:
                script = self.FIND_ELEMENT_RECURSIVE_SCRIPT + """
                        var opt = findElementRecursive(startNode, null, 'Upload videos', null, null);
                        if (!opt) opt = findElementRecursive(startNode, null, '上傳影片', null, null);
                        return opt;
                        """
                upload_option = driver.execute_script(script)
                if upload_option:
                    WebDriverUtil.dispatch_click_events(driver, upload_option)
                    return

            logger.info(f"步驟 : {step_name}, 持續尋找中 {element_name}...")
            time.sleep(2)

    def _upload_file(self, driver, file_path: str):
        if not file_path:
            raise ValueError("File path cannot be null or empty")
        step_name = "上傳檔案"
        file_input = WebDriverUtil.find_element(driver, step_name, By.XPATH, "//input[@type='file']", "上傳檔案輸入框")
        file_input.send_keys(file_path)
        logger.info(f"Sent file path: {file_path}")

    def _enter_title_and_description(self, driver, title: str, description: str):
        try:
            if title:
                step_name = "設定標題"
                title_box = WebDriverUtil.find_element(driver, step_name, By.XPATH, "//ytcp-social-suggestions-textbox[@id='title-textarea']//div[@id='textbox']", "標題輸入框")
                self._set_text(title_box, title)
                logger.info(f"Set title: {title}")
            
            if description:
                step_name = "設定說明"
                desc_box = WebDriverUtil.find_element(driver, step_name, By.XPATH, "//ytcp-social-suggestions-textbox[@id='description-textarea']//div[@id='textbox']", "說明輸入框")
                self._set_text(desc_box, description)
                logger.info("Set description.")
        except Exception as e:
            logger.error(f"Error setting metadata: {e}")

    def _set_text(self, element, text: str):
        element.send_keys(Keys.CONTROL + "a")
        element.send_keys(Keys.BACK_SPACE)
        element.send_keys(text)

    def _select_playlist(self, driver, playlist: str):
        if not playlist:
            return
        try:
            open_step = "開啟播放清單選單"
            trigger = WebDriverUtil.find_clickable_element(driver, open_step, By.XPATH, "//ytcp-text-dropdown-trigger//div[contains(@class, 'right-container')]", "播放清單選單")

            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", trigger)
            driver.execute_script("arguments[0].click();", trigger)
            logger.info("Clicked playlist dropdown trigger.")

            select_step = "選擇播放清單"
            item_selector = f"//li[contains(@class, 'ytcp-checkbox-group') and .//span[contains(@class, 'label-text') and normalize-space(text())='{playlist}']]//div[@id='checkbox-container']"
            item = WebDriverUtil.find_clickable_element(driver, select_step, By.XPATH, item_selector, "播放清單項目")

            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", item)
            item.click()
            logger.info(f"Selected playlist: {playlist}")

            done_step = "點擊完成按鈕"
            done_btn = WebDriverUtil.find_clickable_element(driver, done_step, By.XPATH, "//ytcp-button[.//div[contains(text(), 'Done') or contains(text(), '完成')]]", "完成按鈕")
            done_btn.click()
            logger.info("Clicked Done.")
        except Exception as e:
            logger.warning(f"Could not select playlist '{playlist}': {e}")

    def _set_kids_restriction(self, driver):
        step_name = "設定兒童選項"
        WebDriverUtil.find_clickable_element(driver, step_name, By.XPATH, "//tp-yt-paper-radio-button[@name='VIDEO_MADE_FOR_KIDS_NOT_MFK']", "兒童選項").click()

    def _navigate_wizard_pages(self, driver):
        step_name = "點擊下一步按鈕"
        for _ in range(3):
            WebDriverUtil.find_clickable_element(driver, step_name, By.ID, "next-button", "下一步按鈕").click()

    def _set_visibility(self, driver, visibility: str):
        vis = "PRIVATE"
        if visibility and visibility.upper() == "PUBLIC":
            vis = "PUBLIC"
        elif visibility and visibility.upper() == "UNLISTED":
            vis = "UNLISTED"

        step_name = "設定公開性"
        WebDriverUtil.find_clickable_element(driver, step_name, By.XPATH, f"//tp-yt-paper-radio-button[@name='{vis}']", "公開性選項").click()

    def _save_and_close(self, driver):
        logger.info("Waiting for video processing to complete...")
        while True:
            try:
                status_elements = driver.find_elements(By.XPATH, "//ytcp-video-upload-progress")
                is_complete = False
                for status in status_elements:
                    text = status.text
                    logger.info(f"Current status: {text}")
                    if any(c in text for c in ["Checks complete", "No issues found", "檢查完畢", "處理完畢", "無任何問題", "Upload complete", "上傳完畢"]) and "%" not in text:
                        is_complete = True
                        break

                if is_complete:
                    logger.info("Processing complete.")
                    break
            except Exception:
                pass
            time.sleep(2)

        done_btn = WebDriverUtil.find_clickable_element(driver, "點擊完成按鈕", By.ID, "done-button", "完成按鈕")
        done_btn.click()
        logger.info("Clicked Done button.")
        try:
            WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "close-button"))).click()
        except Exception:
            pass
        logger.info("Video uploaded successfully!")
