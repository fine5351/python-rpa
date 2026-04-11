import logging
import asyncio
import opencc
from typing import List

from constants.auto_append_hashtag import AutoAppendHashtag

logger = logging.getLogger(__name__)

class XiaohongshuService:
    def __init__(self):
        self.converter = opencc.OpenCC('t2s')

    async def start_upload_form(self, page, file_path: str, title: str, description: str, hashtags: List[str]):
        simplified_title = self.converter.convert(title) if title else ""
        final_description = self._build_description(title, description, hashtags)
        simplified_description = self.converter.convert(final_description)

        logger.info(f"Simplified Title: {simplified_title}")
        logger.info(f"Simplified Description: {simplified_description}")

        await self._navigate_to_creator_studio(page)
        await self._upload_file(page, file_path)
        await self._set_title(page, simplified_title)
        await self._set_description(page, simplified_description)

    async def wait_and_publish(self, page):
        await self._wait_for_upload_complete(page)
        await self._wait_for_publish_complete(page)
        await self._click_publish(page)

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
        return desc

    async def _navigate_to_creator_studio(self, page):
        logger.info("前往 小紅書上傳頁面 https://creator.xiaohongshu.com/publish/publish...")
        await page.goto("https://creator.xiaohongshu.com/publish/publish", wait_until="networkidle")
        # Ensure it's on video upload
        try:
            video_tab = page.locator("text='发布视频'")
            if await video_tab.is_visible(timeout=3000):
                await video_tab.click()
        except:
            pass

    async def _upload_file(self, page, file_path: str):
        logger.info("上傳檔案...")
        async with page.expect_file_chooser() as fc_info:
            await page.locator("input[type='file'][accept*='video']").first.evaluate("el => el.click()")
        file_chooser = await fc_info.value
        await file_chooser.set_files(file_path)

    async def _wait_for_upload_complete(self, page):
        logger.info("等待系統顯示上傳完成或允許發布...")
        while True:
            success = page.locator("text='上传完成', text='重新上传', text='视频分辨率较低'")
            if await success.count() > 0:
                for idx in range(await success.count()):
                    if await success.nth(idx).is_visible():
                        logger.info("Upload complete indicator found.")
                        return
            
            # Fallback if publish button is enabled
            publish_btn = page.locator("button:has-text('发布')")
            if await publish_btn.is_visible():
                is_disabled = await publish_btn.get_attribute("disabled")
                if is_disabled is None or is_disabled == "false":
                    logger.info("Publish button is enabled, assuming upload is done.")
                    return
            await asyncio.sleep(2)

    async def _set_title(self, page, title: str):
        if not title: return
        logger.info("設定標題...")
        title_box = page.locator("input[placeholder*='填写标题']").first
        await title_box.fill("")
        await title_box.fill(title)
        
    async def _set_description(self, page, description: str):
        if not description: return
        logger.info("設定說明...")
        desc_box = page.locator("div.tiptap.ProseMirror[contenteditable='true'], #post-textarea").first
        await desc_box.fill("")
        await desc_box.fill(description)
        # Handle hashtags popups
        await asyncio.sleep(2)
        try:
            hashtag_suggestions = page.locator("ul.publish-topic-options li")
            if await hashtag_suggestions.count() > 0:
                await hashtag_suggestions.first.click()
        except:
            pass
        # Click elsewhere to close suggestions
        await page.mouse.click(0, 0)

    async def _wait_for_publish_complete(self, page):
        while True:
            if await page.locator("text='上传中'").is_visible():
                await asyncio.sleep(2)
            else:
                break

    async def _click_publish(self, page):
        logger.info("點擊發佈...")
        btn = page.locator("button:has-text('发布'), button:has-text('Publish')").first
        await btn.scroll_into_view_if_needed()
        await btn.click()
        try:
            await page.locator("text='发布成功'").first.wait_for(state="visible", timeout=10000)
            logger.info("Success indicator found: 发布成功")
        except:
            pass
