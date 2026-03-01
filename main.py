import argparse
import logging
import os
import sys

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
    
    # 1. YouTube
    logger.info(f"Starting YouTube upload for {title}...")
    yt_service = YouTubeService()
    yt_success = yt_service.upload_video(file_path, title, description, playlist, "PUBLIC", hashtags, keep_open)
    if not yt_success:
        logger.error(f"YouTube upload failed for {title}. Stopping sequence.")
        return

    # 2. Bilibili
    logger.info(f"Starting Bilibili upload for {title}...")
    bili_service = BilibiliService()
    bili_success = bili_service.upload_video(file_path, title, description, bilibili_category, hashtags, keep_open)
    if not bili_success:
        logger.error(f"Bilibili upload failed for {title}. Stopping sequence.")
        return

    # 3. Xiaohongshu
    logger.info(f"Starting Xiaohongshu upload for {title}...")
    xhs_service = XiaohongshuService()
    xhs_success = xhs_service.upload_video(file_path, title, description, hashtags, keep_open)
    if not xhs_success:
        logger.error(f"Xiaohongshu upload failed for {title}. Stopping sequence.")
        return

    # 4. TikTok
    logger.info(f"Starting TikTok upload for {title}...")
    tiktok_service = TikTokService()
    tiktok_success = tiktok_service.upload_video(file_path, title, description, "PUBLIC", hashtags, keep_open)
    if not tiktok_success:
        logger.error(f"TikTok upload failed for {title}.")
        return

    logger.info(f"All platforms uploaded successfully for {title}!")

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
