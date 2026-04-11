import argparse
import logging
import os
import sys
import asyncio
from typing import List

# Ensure constants works
current_dir = os.path.dirname(os.path.abspath(__file__))
rpa_root = os.path.dirname(current_dir)
if rpa_root not in sys.path:
    sys.path.insert(0, rpa_root)

from natsort import natsorted
from playwright.async_api import async_playwright

from services.youtube_service import YouTubeService
from services.bilibili_service import BilibiliService
from services.xiaohongshu_service import XiaohongshuService
from services.tiktok_service import TikTokService
from utils.playwright_util import PlaywrightUtil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RPA_Playwright_Main")

def get_filename_without_extension(file_path: str) -> str:
    base_name = os.path.basename(file_path)
    return os.path.splitext(base_name)[0]

async def upload_to_youtube(context, file_path, title, description, playlist, visibility, hashtags):
    try:
        page = await context.new_page()
        service = YouTubeService()
        logger.info(f"[YouTube] Starting form...")
        await service.start_upload_form(page, file_path, title, description, playlist, visibility, hashtags)
        logger.info(f"[YouTube] Form done, waiting to publish...")
        await service.wait_and_publish(page)
        logger.info(f"[YouTube] SUCCESS")
    except Exception as e:
        logger.error(f"[YouTube] ERROR: {e}")

async def upload_to_bilibili(context, file_path, title, description, category, hashtags):
    try:
        page = await context.new_page()
        service = BilibiliService()
        logger.info(f"[Bilibili] Starting form...")
        await service.start_upload_form(page, file_path, title, description, category, hashtags)
        logger.info(f"[Bilibili] Form done, waiting to publish...")
        await service.wait_and_publish(page)
        logger.info(f"[Bilibili] SUCCESS")
    except Exception as e:
        logger.error(f"[Bilibili] ERROR: {e}")

async def upload_to_xiaohongshu(context, file_path, title, description, hashtags):
    try:
        page = await context.new_page()
        service = XiaohongshuService()
        logger.info(f"[Xiaohongshu] Starting form...")
        await service.start_upload_form(page, file_path, title, description, hashtags)
        logger.info(f"[Xiaohongshu] Form done, waiting to publish...")
        await service.wait_and_publish(page)
        logger.info(f"[Xiaohongshu] SUCCESS")
    except Exception as e:
        logger.error(f"[Xiaohongshu] ERROR: {e}")

async def upload_to_tiktok(context, file_path, title, description, hashtags):
    try:
        page = await context.new_page()
        service = TikTokService()
        logger.info(f"[TikTok] Starting form...")
        await service.start_upload_form(page, file_path, title, description, hashtags)
        logger.info(f"[TikTok] Form done, waiting to publish...")
        await service.wait_and_publish(page)
        logger.info(f"[TikTok] SUCCESS")
    except Exception as e:
        logger.error(f"[TikTok] ERROR: {e}")

async def process_multi_platform_upload(file_path: str, description: str, playlist: str, bilibili_category: str, hashtags: List[str], keep_open: bool):
    title = get_filename_without_extension(file_path)
    logger.info(f"Starting Playwright concurrent upload for {title}...")

    async with async_playwright() as p:
        context = await PlaywrightUtil.get_browser_context(p)
        
        # Gather all tasks to run purely asynchronously
        tasks = [
            upload_to_youtube(context, file_path, title, description, playlist, "PUBLIC", hashtags),
            upload_to_bilibili(context, file_path, title, description, bilibili_category, hashtags),
            upload_to_xiaohongshu(context, file_path, title, description, hashtags),
            upload_to_tiktok(context, file_path, title, description, hashtags)
        ]
        
        await asyncio.gather(*tasks)
        
        logger.info(f"All platforms processing finished for {title}!")
        if not keep_open:
            await context.close()
        else:
            logger.info("Keep open requested, waiting indefinitely...")
            while True:
                await asyncio.sleep(1000)

async def main_async():
    parser = argparse.ArgumentParser(description="Playwright Video RPA CLI Tool")
    subparsers = parser.add_subparsers(dest="action", help="Action to perform", required=True)

    multi_parser = subparsers.add_parser("multi", help="Upload a video to multiple platforms concurrently")
    multi_parser.add_argument("--file", type=str, help="Path to the video file (e.g., F:\\啟諭鳥之章\\啟喻鳥之章-6.mp4)")
    multi_parser.add_argument("--folder", type=str, help="Path to the folder containing video files")
    multi_parser.add_argument("--desc", type=str, default="", help="Description")
    multi_parser.add_argument("--tags", type=str, default="", help="Comma separated hashtags")
    multi_parser.add_argument("--playlist", type=str, default="", help="YouTube playlist")
    multi_parser.add_argument("--keep-open", action="store_true", help="Keep browser open after completion")

    args = parser.parse_args()

    hashtags = [tag.strip() for tag in args.tags.split(",")] if args.tags else []

    if args.action == "multi":
        if args.file:
            await process_multi_platform_upload(args.file, args.desc, args.playlist, "游戏", hashtags, args.keep_open)
        elif args.folder:
            video_extensions = {".mp4", ".mov", ".mkv"}
            files = []
            for root_dir, _, filenames in os.walk(args.folder):
                for f in filenames:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in video_extensions:
                        files.append(os.path.join(root_dir, f))
            files = natsorted(files)

            if not files:
                logger.warning(f"No video files found in {args.folder}")
                return

            for f in files:
                logger.info(f"\n================ Processing next file: {f} ================\n")
                await process_multi_platform_upload(f, args.desc, args.playlist, "游戏", hashtags, False)
                await asyncio.sleep(5) 
        else:
            logger.error("Either --file or --folder is required for multi.")

if __name__ == "__main__":
    asyncio.run(main_async())
