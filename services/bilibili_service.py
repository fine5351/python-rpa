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

class BilibiliService:
    def __init__(self):
        self.converter = opencc.OpenCC('t2s')

    def upload_video(self, file_path: str, title: str, description: str, category: str,
                     hashtags: List[str], keep_open_on_failure: bool) -> bool:
        driver = None
        success = False
        try:
            driver = WebDriverUtil.initialize_driver()
            self.start_upload_form(driver, file_path, title, description, category, hashtags)
            self.wait_and_publish(driver)
            success = True
            return True
        except Exception as e:
            logger.error(f"Error during Bilibili upload: {e}", exc_info=True)
            return False
        finally:
            if driver is not None:
                if success or not keep_open_on_failure:
                    driver.quit()
                    logger.info("Browser closed successfully.")
                else:
                    logger.warning("Browser left open for debugging.")

    def start_upload_form(self, driver, file_path: str, title: str, description: str, category: str, hashtags: List[str]):
        simplified_title = self.converter.convert(title) if title else ""
        final_description = self._build_description(title, description, hashtags)
        
        self._navigate_to_upload(driver)
        self._upload_file(driver, file_path)
        # 移除前面的強制等待，讓讀條可以在背景進行
        self._set_title(driver, simplified_title)
        self._set_description(driver, final_description)
        self._select_category(driver, category)
        self._set_tags(driver, hashtags)

    def wait_and_publish(self, driver):
        self._wait_for_upload_complete(driver)
        self._click_submit(driver)
        self._wait_for_success(driver)

    def _build_description(self, title: str, description: str, hashtags: List[str]) -> str:
        desc = ""
        if description:
            desc += f"{description}\n"

        if title:
            for keyword in AutoAppendHashtag.AUTO_HASHTAG_KEYWORDS:
                if keyword in title:
                    desc += f" #{keyword}"
                    if hashtags is not None and keyword not in hashtags:
                        hashtags.append(keyword)

        if hashtags:
            for tag in hashtags:
                hashtag = f" #{tag}"
                if hashtag not in desc:
                    desc += hashtag

        return self.converter.convert(desc.strip())

    def _navigate_to_upload(self, driver):
        step_name = "前往上傳頁面"
        logger.info(f"步驟 : {step_name}, 持續尋找中 https://member.bilibili.com/platform/upload/video/frame...")
        driver.get("https://member.bilibili.com/platform/upload/video/frame")

    def _upload_file(self, driver, file_path: str):
        step_name = "上傳檔案"
        while True:
            try:
                time.sleep(3)
                global_input_selector = (By.XPATH, "//input[@type='file']")
                inputs = driver.find_elements(*global_input_selector)

                if not inputs:
                    logger.info("未直接找到檔案輸入框，嘗試等待...")
                    try:
                        WebDriverWait(driver, 5).until(EC.presence_of_element_located(global_input_selector))
                        inputs = driver.find_elements(*global_input_selector)
                    except Exception:
                        pass

                if not inputs:
                    logger.info("仍未找到檔案輸入框，嘗試點擊上傳區域以觸發...")
                    upload_area_selector = By.XPATH, "//div[contains(@class, 'upload-area')]"
                    upload_area = WebDriverUtil.find_clickable_element(driver, step_name, *upload_area_selector, "上傳區域")
                    upload_area.click()

                    file_input = WebDriverUtil.find_element(driver, step_name, *global_input_selector, "上傳按鈕 (觸發後)")
                    file_input.send_keys(file_path)
                else:
                    inputs[0].send_keys(file_path)

                logger.info("檔案路徑已送出，等待3秒確認上傳進度...")
                time.sleep(3)

                progress_elements = driver.find_elements(By.CLASS_NAME, "progress-text")
                complete_elements = driver.find_elements(By.XPATH, "//span[contains(@class, 'success') and contains(text(), '上传完成')]")

                if progress_elements:
                    logger.info("檢測到上傳進度，上傳成功啟動。")
                    break
                elif complete_elements:
                    logger.info("檢測到 '上传完成' 狀態，視為上傳成功。")
                    break
                else:
                    logger.warning("未檢測到上傳進度 (progress-text) 或 完成狀態，重新嘗試上傳...")

            except Exception as e:
                logger.error(f"上傳過程發生錯誤，準備重試: {e}")
                time.sleep(3)

    def _wait_for_upload_complete(self, driver):
        step_name = "等待上傳完成"
        while True:
            try:
                success_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '上传成功') or contains(text(), 'Upload success') or contains(text(), '上传完成')]")
                if success_elements:
                    logger.info("Upload complete (success message found).")
                    break

                progress_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '%')]")
                for el in progress_elements:
                    text = el.text
                    if re.match(r".*\d+%.*", text) and "100%" not in text:
                        logger.info(f"Upload progress: {text}")
                        break

                time.sleep(1)
            except Exception:
                time.sleep(1)

    def _set_title(self, driver, title: str):
        try:
            step_name = "設定標題"
            selector = "//input[contains(@placeholder, '标题') or contains(@placeholder, 'Title')]"
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
            selector = "div.ql-editor[contenteditable='true'][data-placeholder*='填写更全面的相关信息']"
            desc_input = WebDriverUtil.find_element(driver, step_name, By.CSS_SELECTOR, selector, "說明輸入框")

            try:
                desc_input.click()
            except Exception:
                pass

            html_desc = f"<p>{description}</p>"
            driver.execute_script("arguments[0].innerHTML = arguments[1];", desc_input, html_desc)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", desc_input)
            
            logger.info("Description set.")
        except Exception as e:
            logger.warning(f"Could not set description via JS: {e}")
            try:
                fallback_selector = "//div[contains(@class, 'ql-editor') and @contenteditable='true']"
                fallback_input = driver.find_element(By.XPATH, fallback_selector)
                fallback_input.send_keys(description)
            except Exception as ex:
                logger.error(f"Fallback description set failed: {ex}")

    def _select_category(self, driver, category: str):
        if not category:
            category = "游戏"
            
        try:
            step_name = "選擇分區"
            dropdown = WebDriverUtil.find_clickable_element(driver, step_name, By.CSS_SELECTOR, ".select-controller", "分區下拉選單")

            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", dropdown)
            time.sleep(0.5)

            dropdown.click()
            logger.info("Clicked category dropdown.")
            time.sleep(1)

            target_category = self.converter.convert(category)
            option_selector = f"//div[contains(@class, 'drop-list-v2-item') and @title='{target_category}'] | //div[contains(@class, 'drop-list-v2-item')]//p[contains(@class, 'item-cont-main') and contains(text(), '{target_category}')]"
            simple_option_selector = f"//*[text()='{target_category}']"

            target_option = None
            try:
                target_option = WebDriverUtil.find_clickable_element(driver, step_name, By.XPATH, option_selector, f"{target_category} 選項")
            except Exception:
                logger.warning(f"Refined selector for '{target_category}' not found, trying simple text search...")
                try:
                    target_option = WebDriverUtil.find_clickable_element(driver, step_name, By.XPATH, simple_option_selector, f"{target_category} 選項")
                except Exception:
                    logger.error(f"Could not find '{target_category}' option.")

            if target_option:
                target_option.click()
                logger.info(f"Category '{target_category}' selected.")

            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Could not select category: {e}")

    def _set_tags(self, driver, hashtags: List[str]):
        if not hashtags:
            return

        try:
            step_name = "設定標籤"
            selector = "//input[contains(@class, 'input-val') and contains(@placeholder, '创建标签')]"
            tag_input = WebDriverUtil.find_element(driver, step_name, By.XPATH, selector, "標籤輸入框")

            for tag in hashtags:
                simplified_tag = self.converter.convert(tag)
                tag_input.send_keys(simplified_tag)
                logger.info(f"標籤輸入: {simplified_tag}")
                tag_input.send_keys(Keys.ENTER)
                time.sleep(0.5)
                
            logger.info("Tags set.")
        except Exception as e:
            logger.warning(f"Could not set tags: {e}")

    def _click_submit(self, driver):
        try:
            step_name = "點擊發佈按鈕"
            selector = "//span[contains(text(), '立即投稿') or contains(text(), 'Submit')]"
            submit_btn = WebDriverUtil.find_clickable_element(driver, step_name, By.XPATH, selector, "發佈按鈕")

            driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
            submit_btn.click()
            logger.info("Clicked Submit.")
        except Exception as e:
            logger.warning(f"Could not click Submit: {e}")

    def _wait_for_success(self, driver):
        step_name = "等待發佈成功"
        success_selector = "//div[contains(@class, 'step-des') and contains(text(), '稿件投递成功')]"
        WebDriverUtil.find_element(driver, step_name, By.XPATH, success_selector, "成功訊息")
        logger.info("Success indicator found.")
        logger.info("Waiting 2 seconds before closing...")
        time.sleep(2)
