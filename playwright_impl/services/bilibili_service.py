import logging
import asyncio
import re
import opencc
from typing import List

from constants.auto_append_hashtag import AutoAppendHashtag

logger = logging.getLogger(__name__)

class BilibiliService:
    def __init__(self):
        self.converter = opencc.OpenCC('t2s')

    async def start_upload_form(self, page, file_path: str, title: str, description: str, category: str, hashtags: List[str]):
        simplified_title = self.converter.convert(title) if title else ""
        final_description = self._build_description(title, description, hashtags)
        
        await self._navigate_to_upload(page)
        await self._upload_file(page, file_path)
        
        await self._set_title(page, simplified_title)
        await self._set_description(page, final_description)
        await self._select_category(page, category)
        await self._set_tags(page, hashtags)

    async def wait_and_publish(self, page):
        await self._wait_for_upload_complete(page)
        await self._click_submit(page)
        await self._wait_for_success(page)

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

    async def _navigate_to_upload(self, page):
        logger.info("前往上傳頁面 https://member.bilibili.com/platform/upload/video/frame...")
        await page.goto("https://member.bilibili.com/platform/upload/video/frame", wait_until="networkidle")

    async def _upload_file(self, page, file_path: str):
        logger.info(f"上傳檔案: {file_path}")
        try:
            # Sometime input file is hidden
            async with page.expect_file_chooser(timeout=5000) as fc_info:
                await page.locator("input[type='file']").first.evaluate("el => el.click()")
            file_chooser = await fc_info.value
            await file_chooser.set_files(file_path)
            logger.info("檔案路徑已送出")
            
            # ensure start
            try:
                await page.locator(".progress-text").first.wait_for(state="visible", timeout=10000)
            except:
                pass
        except Exception as e:
            logger.error(f"上傳過程發生錯誤: {e}")

    async def _wait_for_upload_complete(self, page):
        logger.info("等待上傳完成...")
        while True:
            try:
                success_el = page.locator("text='上传成功', text='Upload success', text='上传完成'").first
                if await success_el.is_visible(timeout=1000):
                    logger.info("Upload complete (success message found).")
                    break

                progress = page.locator("text=/%/").first
                if await progress.is_visible(timeout=1000):
                    text = await progress.inner_text()
                    if "100%" not in text:
                        logger.info(f"Upload progress: {text}")
                        break
            except Exception:
                pass
            await asyncio.sleep(2)

    async def _set_title(self, page, title: str):
        logger.info("設定標題...")
        try:
            title_input = page.locator("input[placeholder*='标题'], input[placeholder*='Title']").first
            await title_input.fill(title)
        except Exception as e:
            logger.warning(f"Could not set title: {e}")

    async def _set_description(self, page, description: str):
        logger.info("設定說明...")
        try:
            desc_input = page.locator("div.ql-editor[contenteditable='true']").first
            html_desc = f"<p>{description}</p>"
            await desc_input.evaluate(f"(el) => {{ el.innerHTML = '{html_desc}'; el.dispatchEvent(new Event('input', {{ bubbles: true }})); }}")
        except Exception as ex:
            logger.error(f"Fallback description set failed: {ex}")

    async def _select_category(self, page, category: str):
        if not category:
            category = "游戏"
            
        target_category = self.converter.convert(category)
        logger.info(f"選擇分區: {target_category}...")
        try:
            dropdown = page.locator(".select-controller").first
            await dropdown.scroll_into_view_if_needed()
            await dropdown.click()
            await asyncio.sleep(1)

            option = page.locator(f".drop-list-v2-item[title='{target_category}'], .drop-list-v2-item p:has-text('{target_category}')").first
            if not await option.is_visible(timeout=2000):
                option = page.locator(f"text='{target_category}'").first
            
            await option.click()
            logger.info(f"Category '{target_category}' selected.")
        except Exception as e:
            logger.warning(f"Could not select category: {e}")

    async def _set_tags(self, page, hashtags: List[str]):
        if not hashtags:
            return

        logger.info("設定標籤...")
        try:
            tag_input = page.locator("input.input-val[placeholder*='创建标签']").first
            for tag in hashtags:
                simplified_tag = self.converter.convert(tag)
                await tag_input.fill(simplified_tag)
                await page.keyboard.press("Enter")
                logger.info(f"標籤輸入: {simplified_tag}")
                await asyncio.sleep(0.5)
        except Exception as e:
            logger.warning(f"Could not set tags: {e}")

    async def _click_submit(self, page):
        logger.info("點擊發佈按鈕...")
        try:
            submit_btn = page.locator("text='立即投稿', text='Submit'").first
            await submit_btn.scroll_into_view_if_needed()
            await submit_btn.click()
        except Exception as e:
            logger.warning(f"Could not click Submit: {e}")

    async def _wait_for_success(self, page):
        logger.info("等待發佈成功...")
        await page.locator("text='稿件投递成功'").first.wait_for(state="visible", timeout=20000)
        logger.info("Success indicator found.")
