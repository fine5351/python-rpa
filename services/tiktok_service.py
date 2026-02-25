import logging
import time
import re
from typing import List, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from constants.auto_append_hashtag import AutoAppendHashtag
from utils.webdriver_util import WebDriverUtil

logger = logging.getLogger(__name__)

class TikTokService:

    def upload_video(self, file_path: str, title: str, description: str, visibility: str,
                     hashtags: List[str], keep_open_on_failure: bool) -> bool:
        final_caption = self._build_caption(title, description, hashtags)
        logger.info(f"Processed Caption: {final_caption}")

        driver = None
        success = False
        try:
            driver = WebDriverUtil.initialize_driver()
            self._navigate_to_upload(driver)
            self._upload_file(driver, file_path)
            self._wait_for_upload_complete(driver)
            self._set_caption(driver, final_caption)
            self._post_video(driver)
            success = True
            return True
        except Exception as e:
            logger.error(f"Error during TikTok upload: {e}", exc_info=True)
            return False
        finally:
            if driver is not None:
                if success or not keep_open_on_failure:
                    driver.quit()
                    logger.info("Browser closed successfully.")
                else:
                    logger.warning("Browser left open for debugging.")

    def _build_caption(self, title: str, description: str, hashtags: List[str]) -> str:
        caption = ""
        if title:
            caption += f"{title}\n"
        if description:
            caption += f"{description}\n"

        if title:
            for keyword in AutoAppendHashtag.AUTO_HASHTAG_KEYWORDS:
                if keyword in title:
                    hashtag = f" #{keyword}"
                    if hashtag not in caption:
                        caption += hashtag

        if hashtags:
            for tag in hashtags:
                hashtag = f" #{tag}"
                if hashtag not in caption:
                    caption += hashtag

        return caption.strip()

    def _navigate_to_upload(self, driver):
        step_name = "前往上傳頁面"
        logger.info(f"步驟 : {step_name}, 持續尋找中 https://www.tiktok.com/tiktokstudio/upload...")
        driver.get("https://www.tiktok.com/tiktokstudio/upload")

    def _upload_file(self, driver, file_path: str):
        step_name = "上傳檔案"
        file_input = WebDriverUtil.find_element(driver, step_name, By.XPATH, "//input[@type='file']", "上傳按鈕")
        file_input.send_keys(file_path)

    def _wait_for_upload_complete(self, driver):
        step_name = "等待上傳完成"
        upload_complete = False

        while not upload_complete:
            try:
                is_uploading = False
                progress_elements = driver.find_elements(By.XPATH, "//div[contains(text(), '%')]")
                for el in progress_elements:
                    text = el.text
                    if re.match(r".*\d+%.*", text) and "100%" not in text:
                        is_uploading = True
                        logger.info(f"Upload progress: {text}")
                        break
                
                if not is_uploading:
                    success_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Uploaded') or contains(text(), '上傳完畢') or contains(text(), '已上傳')]")
                    if success_elements:
                        logger.info(f"Upload complete indicator found: {success_elements[0].text}")
                        upload_complete = True
                        break
                
                time.sleep(1)
            except Exception:
                logger.info(f"步驟 : {step_name}, 持續尋找中 上傳完成標誌...")
                time.sleep(1)
        
        if upload_complete:
            logger.info("Upload complete, waiting 3 seconds for UI to stabilize...")
            time.sleep(3)

    def _set_caption(self, driver, caption: str):
        try:
            step_name = "設定標題"
            editor = WebDriverUtil.find_clickable_element(driver, step_name, By.XPATH, "//div[@contenteditable='true']", "標題輸入框")
            editor.click()
            editor.send_keys(Keys.CONTROL + "a")
            editor.send_keys(Keys.BACK_SPACE)

            parts = caption.split(" ")
            for part in parts:
                editor.send_keys(part)
                time.sleep(2)
                if part.startswith("#"):
                    try:
                        logger.info("尋找 標籤建議 位置中")
                        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'mention-list')]")))
                        logger.info("已找到 標籤建議列表，開始尋找最佳匹配...")
                        
                        suggestions = driver.find_elements(By.XPATH, "//div[contains(@class, 'hashtag-suggestion-item')]")
                        logger.info(f"Found {len(suggestions)} suggestions")

                        target_tag = part.replace("#", "")
                        best_match = None
                        max_count = -1

                        for suggestion in suggestions:
                            try:
                                topic_el = suggestion.find_element(By.XPATH, ".//span[contains(@class, 'hash-tag-topic')]")
                                count_el = suggestion.find_element(By.XPATH, ".//span[contains(@class, 'hash-tag-view-count')]")

                                tag_name = topic_el.text.strip()
                                count_text = count_el.text.strip()

                                count = 0
                                s = re.sub(r'[^0-9.KMB]', '', count_text.upper())
                                if s:
                                    multiplier = 1
                                    if s.endswith("K"):
                                        multiplier = 1_000
                                        s = s[:-1]
                                    elif s.endswith("M"):
                                        multiplier = 1_000_000
                                        s = s[:-1]
                                    elif s.endswith("B"):
                                        multiplier = 1_000_000_000
                                        s = s[:-1]
                                    try:
                                        count = int(float(s) * multiplier)
                                    except Exception:
                                        pass

                                current_tag_clean = tag_name.replace("#", "")
                                if current_tag_clean.lower() == target_tag.lower():
                                    if count > max_count:
                                        max_count = count
                                        best_match = suggestion
                                        logger.info(f"New Best Match Found: {tag_name} with {count} views")
                            except Exception as e:
                                logger.warning(f"Error parsing suggestion item: {e}")

                        if best_match:
                            topic = best_match.find_element(By.XPATH, ".//span[contains(@class, 'hash-tag-topic')]").text
                            logger.info(f"執行 點擊最佳匹配建議 操作 (Tag: {topic}, Views: {max_count})")
                            best_match.click()
                        else:
                            logger.info("未找到精確匹配，嘗試點擊第一個建議")
                            if suggestions:
                                suggestions[0].click()
                            else:
                                driver.find_element(By.XPATH, "//div[contains(@class, 'mention-list')]//div[1]").click()
                    except Exception:
                        pass
                
                editor.send_keys(" ")
            
            logger.info("Caption set.")
        except Exception as e:
            logger.warning(f"Could not set caption: {e}")

    def _post_video(self, driver):
        step_name = "點擊發佈"
        post_selector = "//button[@data-e2e='post_video_button' and .//div[contains(@class, 'Button__content') and (contains(text(), '發佈') or contains(text(), 'Post'))]]"
        post_button = WebDriverUtil.find_clickable_element(driver, step_name, By.XPATH, post_selector, "發佈按鈕")
        post_button.click()
        logger.info("Clicked Post.")

        try:
            confirm_selector = "//button[contains(@class, 'TUXButton') and .//div[contains(@class, 'TUXButton-label') and (contains(text(), '立即發佈') or contains(text(), 'Post'))]]"
            confirm_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, confirm_selector)))
            confirm_button.click()
            logger.info("Clicked Post Immediately.")
        except Exception:
            pass

        logger.info("Waiting for post success...")
        try:
            success_selector = "//div[contains(text(), 'Manage your posts') or contains(text(), 'View profile') or contains(text(), 'Upload another video') or contains(text(), '上傳另一支影片')]"
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, success_selector)))
            logger.info("Post success indicator found.")
        except Exception:
            logger.warning("Explicit success message not found, checking URL...")

        time.sleep(3)
