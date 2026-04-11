import logging
import time
import re
from typing import List, Optional

import opencc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from constants.auto_append_hashtag import AutoAppendHashtag
from utils.webdriver_util import WebDriverUtil

logger = logging.getLogger(__name__)

class XiaohongshuService:
    def __init__(self):
        self.converter = opencc.OpenCC('t2s')

    def upload_video(self, file_path: str, title: str, description: str,
                     hashtags: List[str], keep_open_on_failure: bool) -> bool:
        driver = None
        success = False
        try:
            driver = WebDriverUtil.initialize_driver()
            self.start_upload_form(driver, file_path, title, description, hashtags)
            self.wait_and_publish(driver)
            success = True
            return True
        except Exception as e:
            logger.error(f"Error during Xiaohongshu upload: {e}", exc_info=True)
            return False
        finally:
            if driver is not None:
                if success or not keep_open_on_failure:
                    driver.quit()
                    logger.info("Browser closed successfully.")
                else:
                    logger.warning("Browser left open for debugging.")

    def start_upload_form(self, driver, file_path: str, title: str, description: str, hashtags: List[str]):
        simplified_title = self.converter.convert(title) if title else ""
        final_description = self._build_description(title, description, hashtags)
        simplified_description = self.converter.convert(final_description)

        logger.info(f"Simplified Title: {simplified_title}")
        logger.info(f"Simplified Description: {simplified_description}")

        self._navigate_to_creator_studio(driver)
        self._upload_file(driver, file_path)
        self._set_title(driver, simplified_title)
        self._set_description(driver, simplified_description)

    def wait_and_publish(self, driver):
        self._wait_for_upload_complete(driver)
        self._wait_for_publish_complete(driver)
        self._click_publish(driver)

    def _build_description(self, title: str, description: str, hashtags: List[str]) -> str:
        desc = ""
        if description:
            desc += f"{description}\n"

        if title:
            for keyword in AutoAppendHashtag.AUTO_HASHTAG_KEYWORDS:
                if keyword in title:
                    desc += f" #{keyword}"

        if hashtags:
            for tag in hashtags:
                hashtag = f" #{tag}"
                if hashtag not in desc:
                    desc += hashtag

        return desc.strip()

    def _navigate_to_creator_studio(self, driver):
        step_name = "前往上傳頁面"
        logger.info(f"步驟 : {step_name}, 持續尋找中 https://creator.xiaohongshu.com/publish/publish...")
        driver.get("https://creator.xiaohongshu.com/publish/publish")

    def _upload_file(self, driver, file_path: str):
        step_name = "上傳檔案"
        file_input = WebDriverUtil.find_element(driver, step_name, By.XPATH, "//input[@type='file']", "上傳按鈕")
        file_input.send_keys(file_path)

    def _wait_for_upload_complete(self, driver):
        step_name = "等待上傳完成"
        while True:
            try:
                is_uploading = False
                progress_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '%')]")
                for el in progress_elements:
                    text = el.text
                    if re.match(r".*\d+%.*", text) and "100%" not in text:
                        is_uploading = True
                        logger.info(f"Upload progress: {text}")
                        break

                if not is_uploading:
                    success_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '上传成功') or contains(text(), 'Upload success') or contains(text(), '检测为高清视频') or contains(text(), '视频分辨率较低')]")
                    if success_elements:
                        logger.info("Upload complete.")
                        break

                time.sleep(1)
            except Exception:
                logger.info(f"步驟 : {step_name}, 持續尋找中 上傳完成標誌...")
                time.sleep(1)

    def _set_title(self, driver, title: str):
        try:
            step_name = "設定標題"
            selector = "//input[contains(@placeholder, '填写标题') or contains(@placeholder, '標題')]"
            title_input = WebDriverUtil.find_element(driver, step_name, By.XPATH, selector, "標題輸入框")
            title_input.click()
            title_input.send_keys(Keys.CONTROL + "a")
            title_input.send_keys(Keys.BACK_SPACE)
            title_input.send_keys(title)
            logger.info("Title set.")
        except Exception as e:
            logger.warning(f"Could not set title: {e}")

    def _set_description(self, driver, description: str):
        try:
            step_name = "設定說明"
            selector = "//div[contains(@class, 'tiptap') and contains(@class, 'ProseMirror') and @contenteditable='true']"
            desc_input = WebDriverUtil.find_element(driver, step_name, By.XPATH, selector, "說明輸入框")
            desc_input.click()

            parts = description.split(" ")
            for part in parts:
                desc_input.send_keys(part)
                time.sleep(2)
                if part.startswith("#"):
                    try:
                        suggestion_selector = "//div[contains(@class, 'item') and .//span[contains(@class, 'name')] and .//span[contains(@class, 'num')]]"
                        suggestions = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.XPATH, suggestion_selector)))

                        best_match = None
                        max_views = -1

                        for item in suggestions:
                            try:
                                name = item.find_element(By.CLASS_NAME, "name").text
                                num_text = item.find_element(By.CLASS_NAME, "num").text

                                if name == part.replace("#", ""):
                                    views = self._parse_views(num_text)
                                    logger.info(f"瀏覽人數: {views}")
                                    if views > max_views:
                                        max_views = views
                                        best_match = item
                            except Exception as ex:
                                logger.warning(f"Could not parse views: {ex}")

                        if best_match:
                            best_match.click()
                        elif suggestions:
                            suggestions[0].click()

                        desc_input.send_keys(" ")

                    except Exception:
                        pass
            
            logger.info("Description set.")
        except Exception as e:
            logger.warning(f"Could not set description: {e}")

    def _parse_views(self, num_text: str) -> int:
        if not num_text:
            return 0
        num_text = num_text.replace("人浏览", "").strip()
        multiplier = 1
        if num_text.endswith("亿"):
            multiplier = 100000000
            num_text = num_text.replace("亿", "")
        elif num_text.endswith("万"):
            multiplier = 10000
            num_text = num_text.replace("万", "")
        
        try:
            return int(float(num_text) * multiplier)
        except ValueError:
            return 0

    def _wait_for_publish_complete(self, driver):
        step_name = "等待發佈完成"
        while True:
            try:
                progress_elements = driver.find_elements(By.XPATH, "//div[contains(text(), '上传中')]")
                if progress_elements:
                    progress_text = progress_elements[0].text.strip()
                    logger.info(f"Xiaohongshu publish progress: {progress_text}")
                    time.sleep(2)
                    continue
                break
            except Exception:
                pass
            time.sleep(2)

    def _click_publish(self, driver):
        step_name = "點擊發佈按鈕"
        selector = "//button[contains(@class, 'bg-red') and contains(., '发布')]"

        while True:
            try:
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, selector)))
                elements = driver.find_elements(By.XPATH, selector)
                
                publish_btn = None
                for el in elements:
                    if el.is_displayed():
                        publish_btn = el
                        break

                if publish_btn:
                    driver.execute_script("arguments[0].scrollIntoView(true);", publish_btn)
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable(publish_btn))

                    publish_btn.click()
                    logger.info("Clicked Publish.")

                    try:
                        success_selector = "//*[contains(text(), '发布成功') or contains(text(), 'Publish success')]"
                        success_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, success_selector)))
                        logger.info(f"Success indicator found: {success_element.text}")
                        break
                    except Exception:
                        try:
                            # Re-find element to avoid stale reference
                            new_elements = driver.find_elements(By.XPATH, selector)
                            if not new_elements or not new_elements[0].is_displayed():
                                logger.info("Publish button is gone. Assuming success.")
                                break
                        except Exception:
                            logger.info("Publish button is gone. Assuming success.")
                            break
            except Exception:
                pass

            logger.info(f"步驟 : {step_name}, 持續尋找中 發佈按鈕...")
            time.sleep(2)

        time.sleep(3)
