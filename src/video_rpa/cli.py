"""Video RPA 統一命令列介面 (CLI Entry Point)."""

import argparse
import logging
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from natsort import natsorted

from video_rpa.core.trail_tracker import OperationTrailTracker
from video_rpa.services.bilibili_service import BilibiliService
from video_rpa.services.rednote_service import rednoteService
from video_rpa.services.tiktok_service import TikTokService
from video_rpa.services.youtube_service import YouTubeService
from video_rpa.utils.webdriver_util import WebDriverUtil

# Setup basic logging to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VideoRPA")


def get_filename_without_extension(file_path: str) -> str:
    if not file_path:
        return ""
    return os.path.splitext(os.path.basename(file_path))[0]


def process_multi_platform_upload(file_path: str, description: str, playlist: str, bilibili_category: str, hashtags: list, keep_open: bool):
    title = get_filename_without_extension(file_path)
    logger.info(f"Starting multi-platform tabbed upload for {title}...")

    driver = None
    try:
        driver = WebDriverUtil.initialize_driver()
        platforms = []

        # 1. YouTube
        logger.info("Starting YouTube form...")
        window_yt = driver.current_window_handle
        yt_service = YouTubeService()
        platforms.append({"name": "YouTube", "handle": window_yt, "service": yt_service})
        yt_service.start_upload_form(driver, file_path, title, description, playlist, "PUBLIC", hashtags)

        # 2. Bilibili
        logger.info("Starting Bilibili form...")
        driver.switch_to.new_window('tab')
        window_bili = driver.current_window_handle
        bili_service = BilibiliService()
        platforms.append({"name": "Bilibili", "handle": window_bili, "service": bili_service})
        bili_service.start_upload_form(driver, file_path, title, description, bilibili_category, hashtags)

        # 3. rednote
        logger.info("Starting rednote form...")
        driver.switch_to.new_window('tab')
        window_xhs = driver.current_window_handle
        xhs_service = rednoteService()
        platforms.append({"name": "rednote", "handle": window_xhs, "service": xhs_service})
        xhs_service.start_upload_form(driver, file_path, title, description, hashtags)

        # 4. TikTok
        logger.info("Starting TikTok form...")
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
        OperationTrailTracker.get_instance().save_to_file()

    except Exception as e:
        logger.error(f"Error during multi tab process: {e}", exc_info=True)
    finally:
        if driver is not None:
            if not keep_open:
                driver.quit()
            else:
                logger.warning("Browser left open for debugging due to --keep-open.")


def main():
    parser = argparse.ArgumentParser(description="Video RPA CLI - 多平台影音自動發佈工具")
    parser.add_argument("--show-trail", action="store_true", help="顯示當前待固化的操作軌跡報告並結束。")
    subparsers = parser.add_subparsers(dest="command", help="可用子命令 (Subcommands)")

    # Common arguments
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--file", type=str, help="影片檔案路徑。", required=False)
    common_parser.add_argument("--folder", type=str, help="影片資料夾路徑 (供多影片批次發佈)。", required=False)
    common_parser.add_argument("--title", type=str, help="影片標題 (預設為檔案名稱)。", default=None)
    common_parser.add_argument("--desc", type=str, help="影片說明或文案。", default="")
    common_parser.add_argument("--tags", type=str, help="以逗號分隔的主題標籤 (例如: tag1,tag2)。", default="")
    common_parser.add_argument("--keep-open", action="store_true", help="失敗或結束時保持瀏覽器開啟以供除錯。")
    common_parser.add_argument("--show-trail", action="store_true", help="顯示當前待固化的操作軌跡報告並結束。")

    # YouTube Specific
    parser_yt = subparsers.add_parser("youtube", parents=[common_parser], help="上傳至 YouTube")
    parser_yt.add_argument("--playlist", type=str, help="YouTube 播放清單", default="")
    parser_yt.add_argument("--visibility", type=str, choices=["PUBLIC", "UNLISTED", "PRIVATE"], default="PUBLIC")

    # TikTok Specific
    parser_tiktok = subparsers.add_parser("tiktok", parents=[common_parser], help="上傳至 TikTok")
    parser_tiktok.add_argument("--visibility", type=str, choices=["PUBLIC", "UNLISTED", "PRIVATE"], default="PUBLIC")

    # rednote Specific
    parser_xhs = subparsers.add_parser("rednote", parents=[common_parser], help="上傳至小紅書 (Rednote)")

    # Bilibili Specific
    parser_bili = subparsers.add_parser("bilibili", parents=[common_parser], help="上傳至 Bilibili")
    parser_bili.add_argument("--category", type=str, help="Bilibili 分區", default="游戏")

    # Multi-Platform Specific
    parser_multi = subparsers.add_parser("multi", parents=[common_parser], help="批次或同時上傳至所有平台")
    parser_multi.add_argument("--playlist", type=str, help="YouTube 播放清單", default="")
    parser_multi.add_argument("--category", type=str, help="Bilibili 分區", default="游戏")

    args = parser.parse_args()

    tracker = OperationTrailTracker.get_instance()

    if getattr(args, "show_trail", False):
        tracker.print_consolidation_log(logger)
        return

    if not args.command:
        parser.print_help()
        return

    hashtags = [t.strip() for t in args.tags.split(",")] if args.tags else []

    try:
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
            logger.error("--file 或 --folder 為必填參數。")
            sys.exit(1)

        file_path = args.file
        if not os.path.isfile(file_path):
            logger.error(f"找不到檔案: {file_path}")
            sys.exit(1)

        title = args.title if args.title is not None else get_filename_without_extension(file_path)

        if args.command == "youtube":
            service = YouTubeService()
            service.upload_video(file_path, title, args.desc, args.playlist, args.visibility, hashtags, args.keep_open)
        elif args.command == "tiktok":
            service = TikTokService()
            service.upload_video(file_path, title, args.desc, args.visibility, hashtags, args.keep_open)
        elif args.command == "rednote":
            service = rednoteService()
            service.upload_video(file_path, title, args.desc, hashtags, args.keep_open)
        elif args.command == "bilibili":
            service = BilibiliService()
            service.upload_video(file_path, title, args.desc, args.category, hashtags, args.keep_open)
        elif args.command == "multi":
            process_multi_platform_upload(file_path, args.desc, args.playlist, args.category, hashtags, args.keep_open)

    finally:
        # 任務結束後輸出 log 表示需要回寫 script 進行固化
        tracker.print_consolidation_log(logger)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n [系統] 接收到中斷指令 (Ctrl+C)，正在安全關閉並結束程式...")
        OperationTrailTracker.get_instance().print_consolidation_log(logger)
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
