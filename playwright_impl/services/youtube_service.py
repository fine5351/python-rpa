import logging
import asyncio
from typing import List

from constants.auto_append_hashtag import AutoAppendHashtag

logger = logging.getLogger(__name__)

class YouTubeService:

    async def start_upload_form(self, page, file_path: str, title: str, description: str, playlist: str, visibility: str, hashtags: List[str]):
        final_description = self._build_description(title, description, hashtags)
        await self._navigate_to_studio(page)
        await self._click_create_button(page)
        await self._select_upload_option(page)
        await self._upload_file(page, file_path)
        await self._enter_title_and_description(page, title, final_description)
        await self._select_playlist(page, playlist)
        await self._set_kids_restriction(page)
        await self._navigate_wizard_pages(page)
        await self._set_visibility(page, visibility)

    async def wait_and_publish(self, page):
        await self._save_and_close(page)

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

    async def _navigate_to_studio(self, page):
        logger.info("前往 YouTube Studio https://studio.youtube.com...")
        await page.goto("https://studio.youtube.com", wait_until="domcontentloaded")
        try:
            # Handle possible "Continue" popup in studio
            continue_btn = page.locator("tp-yt-paper-button#button:has-text('Continue')")
            if await continue_btn.is_visible(timeout=2000):
                await continue_btn.click()
        except Exception:
            pass

    async def _handle_trust_tiers_popup(self, page):
        try:
            # Check for trust tiers popup
            popup = page.locator("yt-trust-tiers-wizard-dialog")
            if await popup.is_visible(timeout=3000):
                logger.info("'Trust Tiers' popup detected.")
                await popup.locator("ytcp-button").locator(".yt-spec-touch-feedback-shape__fill").focus()
                await popup.locator("ytcp-button").locator(".yt-spec-touch-feedback-shape__fill").click()
                logger.info("Popup dismissed.")
        except Exception as e:
            pass

    async def _click_create_button(self, page):
        logger.info("點擊建立按鈕 (Create button)...")
        # Playwright automatically waits for visibility and navigates shadow DOMs natively!
        btn = page.locator("ytcp-quick-actions").locator("ytcp-icon-button").first
        if not await btn.is_visible(timeout=3000):
            # Fallback
            btn = page.locator("#create-icon").first
            
        await btn.click()
        await self._handle_trust_tiers_popup(page)

    async def _select_upload_option(self, page):
        logger.info("點擊上傳影片選項 (Upload Option)...")
        try:
            upload_opt = page.locator("tp-yt-paper-item:has-text('Upload videos'), tp-yt-paper-item:has-text('上傳影片')").first
            await upload_opt.click()
        except Exception:
            pass

    async def _upload_file(self, page, file_path: str):
        logger.info(f"上傳檔案: {file_path}")
        async with page.expect_file_chooser() as fc_info:
            # Sometime input file is hidden, clicking the container triggers it
            await page.locator("input[type='file']").evaluate("el => el.click()")
        file_chooser = await fc_info.value
        await file_chooser.set_files(file_path)

    async def _enter_title_and_description(self, page, title: str, description: str):
        if title:
            logger.info(f"Set title: {title}")
            title_box = page.locator("#title-textarea").locator("#textbox").first
            await title_box.fill("")
            await title_box.fill(title)
            
        if description:
            logger.info("Set description.")
            desc_box = page.locator("#description-textarea").locator("#textbox").first
            await desc_box.fill("")
            await desc_box.fill(description)

    async def _select_playlist(self, page, playlist: str):
        if not playlist:
            return
        try:
            logger.info("開發播放清單...")
            trigger = page.locator("ytcp-text-dropdown-trigger").locator(".right-container").first
            await trigger.click()
            
            # Select specific playlist checkbox
            checkbox_container = page.locator(f"li.ytcp-checkbox-group:has(span.label-text:has-text('{playlist}'))").locator("#checkbox-container").first
            await checkbox_container.click()
            logger.info(f"Selected playlist: {playlist}")
            
            # Click done
            done_btn = page.locator("ytcp-button:has-text('Done'), ytcp-button:has-text('完成')").first
            await done_btn.click()
        except Exception as e:
            logger.warning(f"Could not select playlist '{playlist}': {e}")

    async def _set_kids_restriction(self, page):
        await page.locator("tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK']").first.click()

    async def _navigate_wizard_pages(self, page):
        for _ in range(3):
            btn = page.locator("#next-button").first
            await btn.click()
            await asyncio.sleep(0.5)

    async def _set_visibility(self, page, visibility: str):
        vis = "PRIVATE"
        if visibility and visibility.upper() == "PUBLIC":
            vis = "PUBLIC"
        elif visibility and visibility.upper() == "UNLISTED":
            vis = "UNLISTED"
            
        await page.locator(f"tp-yt-paper-radio-button[name='{vis}']").first.click()

    async def _save_and_close(self, page):
        logger.info("Attempting to publish directly without waiting for checks...")
        
        # Click Done/Publish
        done_btn = page.locator("#done-button:has-text('發布'), #done-button:has-text('Publish'), #done-button:has-text('儲存'), #done-button:has-text('Save')").first
        if not await done_btn.is_visible(timeout=2000):
            done_btn = page.locator("#done-button").first
            
        await done_btn.click()
        logger.info("Clicked Done/Publish button.")
        
        # Check for 'Publish anyway' popup
        try:
            popup_btn = page.locator("text='仍要發布', text='Publish anyway'").first
            if await popup_btn.is_visible(timeout=5000):
                await popup_btn.click()
                logger.info("Clicked 'Publish anyway' / '仍要發布' button.")
        except Exception:
            pass

        # Wait for the completion close button
        try:
            close_btn = page.locator("#close-button").first
            await close_btn.wait_for(state="visible", timeout=30000)
            await close_btn.click()
        except Exception:
            pass
            
        logger.info("YouTube Video uploaded successfully!")
