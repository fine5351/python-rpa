import argparse
import logging
import os
import sys

# Ensure parent directory is in sys.path so 'constants' block can be imported from root
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from natsort import natsorted

from services.youtube_service import YouTubeService
from services.bilibili_service import BilibiliService
from services.tiktok_service import TikTokService
from services.xiaohongshu_service import XiaohongshuService

# Setup basic logging to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RPA_Main")

def get_filename_without_extension(file_path: str) -> str:
    if not file_path:
        return ""
    return os.path.splitext(os.path.basename(file_path))[0]

def process_multi_platform_upload(file_path: str, description: str, playlist: str, bilibili_category: str, hashtags: list, keep_open: bool):
    title = get_filename_without_extension(file_path)
    logger.info(f"Starting multi-platform tabbed upload for {title}...")
    
    driver = None
    try:
        from utils.webdriver_util import WebDriverUtil
        driver = WebDriverUtil.initialize_driver()
        platforms = []

        # 1. YouTube
        logger.info(f"Starting YouTube form...")
        window_yt = driver.current_window_handle
        yt_service = YouTubeService()
        platforms.append({"name": "YouTube", "handle": window_yt, "service": yt_service})
        yt_service.start_upload_form(driver, file_path, title, description, playlist, "PUBLIC", hashtags)

        # 2. Bilibili
        logger.info(f"Starting Bilibili form...")
        driver.switch_to.new_window('tab')
        window_bili = driver.current_window_handle
        bili_service = BilibiliService()
        platforms.append({"name": "Bilibili", "handle": window_bili, "service": bili_service})
        bili_service.start_upload_form(driver, file_path, title, description, bilibili_category, hashtags)

        # 3. Xiaohongshu
        logger.info(f"Starting Xiaohongshu form...")
        driver.switch_to.new_window('tab')
        window_xhs = driver.current_window_handle
        xhs_service = XiaohongshuService()
        platforms.append({"name": "Xiaohongshu", "handle": window_xhs, "service": xhs_service})
        xhs_service.start_upload_form(driver, file_path, title, description, hashtags)

        # 4. TikTok
        logger.info(f"Starting TikTok form...")
        driver.switch_to.new_window('tab')
        window_tiktok = driver.current_window_handle
        tiktok_service = TikTokService()
        platforms.append({"name": "TikTok", "handle": window_tiktok, "service": tiktok_service})
        tiktok_service.start_upload_form(driver, file_path, title, description, hashtags)

        # Phase 2: Wait and publish
        logger.info("All forms submitting. Now waiting for uploads to complete and publishing...")
        for p in platforms:
            try:
                driver.switch_to.window(p["handle"])
                logger.info(f"Switching to {p['name']} tab to finish publish...")
                p["service"].wait_and_publish(driver)
                logger.info(f"{p['name']} upload completed successfully!")
            except Exception as e:
                logger.error(f"Failed to publish for {p['name']}: {e}", exc_info=True)
                
        logger.info(f"All platforms processing finished for {title}!")
    
    except Exception as e:
        logger.error(f"Error during multi tab process: {e}", exc_info=True)
    finally:
        if driver is not None:
            if not keep_open:
                driver.quit()
            else:
                logger.warning("Browser left open for debugging due to --keep-open.")

def main():
    parser = argparse.ArgumentParser(description="Video RPA CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Common arguments
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--file", type=str, help="Path to the video file.", required=False)
    common_parser.add_argument("--folder", type=str, help="Path to a folder of videos (for multi-upload).", required=False)
    common_parser.add_argument("--title", type=str, help="Target title (Defaults to file name if omit).", default=None)
    common_parser.add_argument("--desc", type=str, help="Video description.", default="")
    common_parser.add_argument("--tags", type=str, help="Comma-separated hashtags (e.g. tag1,tag2).", default="")
    common_parser.add_argument("--keep-open", action="store_true", help="Keep browser open on failure.")

    # YouTube Specific
    parser_yt = subparsers.add_parser("youtube", parents=[common_parser], help="Upload to YouTube")
    parser_yt.add_argument("--playlist", type=str, help="Target Playlist", default="")
    parser_yt.add_argument("--visibility", type=str, choices=["PUBLIC", "UNLISTED", "PRIVATE"], default="PUBLIC")

    # TikTok Specific
    parser_tiktok = subparsers.add_parser("tiktok", parents=[common_parser], help="Upload to TikTok")
    parser_tiktok.add_argument("--visibility", type=str, choices=["PUBLIC", "UNLISTED", "PRIVATE"], default="PUBLIC")

    # Xiaohongshu Specific
    parser_xhs = subparsers.add_parser("xiaohongshu", parents=[common_parser], help="Upload to Xiaohongshu")

    # Bilibili Specific
    parser_bili = subparsers.add_parser("bilibili", parents=[common_parser], help="Upload to Bilibili")
    parser_bili.add_argument("--category", type=str, help="Bilibili Category", default="游戏")

    # Multi-Platform Specific
    parser_multi = subparsers.add_parser("multi", parents=[common_parser], help="Upload to all platforms sequentially")
    parser_multi.add_argument("--playlist", type=str, help="YouTube Playlist", default="")
    parser_multi.add_argument("--category", type=str, help="Bilibili Category", default="游戏")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    hashtags = [t.strip() for t in args.tags.split(",")] if args.tags else []

    if args.command == "multi" and args.folder:
        folder = args.folder
        if not os.path.isdir(folder):
            logger.error(f"Invalid folder path: {folder}")
            sys.exit(1)
            
        files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
        files = natsorted(files)
        
        for f in files:
            logger.info(f"Processing file in batch: {os.path.basename(f)}")
            process_multi_platform_upload(f, args.desc, args.playlist, args.category, hashtags, args.keep_open)
        return

    if not args.file:
        logger.error("--file or --folder is required.")
        sys.exit(1)

    file_path = args.file
    if not os.path.isfile(file_path):
        logger.error(f"File not found: {file_path}")
        sys.exit(1)

    title = args.title if args.title is not None else get_filename_without_extension(file_path)

    if args.command == "youtube":
        service = YouTubeService()
        service.upload_video(file_path, title, args.desc, args.playlist, args.visibility, hashtags, args.keep_open)
    elif args.command == "tiktok":
        service = TikTokService()
        service.upload_video(file_path, title, args.desc, args.visibility, hashtags, args.keep_open)
    elif args.command == "xiaohongshu":
        service = XiaohongshuService()
        service.upload_video(file_path, title, args.desc, hashtags, args.keep_open)
    elif args.command == "bilibili":
        service = BilibiliService()
        service.upload_video(file_path, title, args.desc, args.category, hashtags, args.keep_open)
    elif args.command == "multi":
        process_multi_platform_upload(file_path, args.desc, args.playlist, args.category, hashtags, args.keep_open)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n [系統] 接收到中斷指令 (Ctrl+C)，正在安全關閉瀏覽器並結束程式...")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
