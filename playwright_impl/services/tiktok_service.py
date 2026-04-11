import logging
import asyncio
from typing import List

from constants.auto_append_hashtag import AutoAppendHashtag

logger = logging.getLogger(__name__)

class TikTokService:

    async def start_upload_form(self, page, file_path: str, title: str, description: str, hashtags: List[str]):
        final_caption = self._build_caption(title, description, hashtags)
        logger.info(f"Processed Caption: {final_caption}")

        await self._navigate_to_upload(page)
        await self._upload_file(page, file_path)
        await self._set_caption(page, final_caption)

    async def wait_and_publish(self, page):
        await self._wait_for_upload_complete(page)
        await self._post_video(page)

    def _build_caption(self, title: str, description: str, hashtags: List[str]) -> str:
        caption = ""
        if title:
            caption += f"{title}\n"
        if description:
            caption += f"{description}\n\n"
        
        for keyword in AutoAppendHashtag.AUTO_HASHTAG_KEYWORDS:
            if keyword in title and keyword not in (hashtags or []):
                if hashtags is None:
                    hashtags = []
                hashtags.append(keyword)

        if hashtags:
            for tag in hashtags:
                if tag not in caption:
                    caption += f"#{tag} "

        return caption.strip()

    async def _navigate_to_upload(self, page):
        logger.info("前往 TikTok 上傳頁面 https://www.tiktok.com/tiktokstudio/upload...")
        await page.goto("https://www.tiktok.com/tiktokstudio/upload", wait_until="networkidle")

    async def _upload_file(self, page, file_path: str):
        logger.info(f"上傳檔案 (TikTok): {file_path}")
        try:
            # Playwright file chooser works gracefully even in deeply nested iframes
            # TikTok often puts upload inside an iframe
            frame = page.frame_locator("iframe[src*='tiktokstudio/upload']")
            if await frame.locator("input[type='file'][accept*='video']").count() > 0:
                context = frame
            else:
                context = page

            async with page.expect_file_chooser() as fc_info:
                await context.locator("input[type='file'][accept*='video']").first.evaluate("el => el.click()")
            file_chooser = await fc_info.value
            await file_chooser.set_files(file_path)
            
            logger.info("檔案路徑已送出")
        except Exception as e:
            logger.error(f"上傳過程發生錯誤: {e}")

    async def _wait_for_upload_complete(self, page):
        logger.info("等待上傳完成...")
        while True:
            # Wait for Uploaded indicator
            uploaded = page.locator("text='已上傳', text='Uploaded'")
            if await uploaded.count() > 0:
                for i in range(await uploaded.count()):
                    if await uploaded.nth(i).is_visible():
                        logger.info("Upload complete indicator found.")
                        await asyncio.sleep(2)
                        return
                        
            # checking switch to change video which means uploaded
            change_video = page.locator("text='更換影片', text='Change video'")
            if await change_video.count() > 0:
                for i in range(await change_video.count()):
                    if await change_video.nth(i).is_visible():
                        logger.info("Upload complete indicator found (change video).")
                        await asyncio.sleep(2)
                        return
                        
            await asyncio.sleep(2)

    async def _set_caption(self, page, caption: str):
        logger.info("設定發佈標題 (Caption)...")
        try:
            # Locate Draft.js editor
            editor = page.locator(".public-DraftEditor-content, div[contenteditable='true']").first
            await editor.click()
            await editor.fill("")

            parts = caption.split("#")
            for i, part in enumerate(parts):
                if i == 0:
                    await editor.type(part)
                else:
                    tag_part = part.split(' ')[0]
                    rest = ' '.join(part.split(' ')[1:])
                    
                    await editor.type(f"#{tag_part}")
                    logger.info(f"等待標籤建議: #{tag_part}")
                    await asyncio.sleep(1.5)
                    try:
                        suggestion = page.locator("div[role='option'], .mentionSuggestions").first
                        if await suggestion.is_visible(timeout=2000):
                            await suggestion.click()
                        else:
                            await page.keyboard.press("Space")
                    except:
                        await page.keyboard.press("Space")
                    
                    if rest:
                        await editor.type(f" {rest}")
            logger.info("Caption set.")
        except Exception as e:
            logger.warning(f"Failed to set caption: {e}")

    async def _post_video(self, page):
        logger.info("點擊Post...")
        btn = page.locator("button:has-text('發布'), button:has-text('Post')").first
        await btn.scroll_into_view_if_needed()
        # Fallback click via js to bypass overlaps
        await btn.evaluate("el => el.click()")

        logger.info("Waiting for post success...")
        while True:
            if "upload" not in page.url:
                logger.info("URL changed from upload, video posted!")
                break
            success_msg = page.locator("text='你的影片已發佈', text='Your video has been uploaded'")
            if await success_msg.count() > 0 and await success_msg.first.is_visible():
                logger.info("Explicit success message found.")
                break
            await asyncio.sleep(2)
