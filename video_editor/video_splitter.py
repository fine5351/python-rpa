#!/usr/bin/env python3
import os
import sys
import argparse
import time
import subprocess
import re
import logging
from typing import List, Tuple, Optional
import cv2
import numpy as np
import imageio_ffmpeg

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("VideoSplitter")

def format_time(seconds: float) -> str:
    """Format seconds into HH:MM:SS.FFF"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

def has_audio_stream(ffmpeg_exe: str, video_path: str) -> bool:
    """Check if the video has an audio stream using ffmpeg."""
    try:
        cmd = [ffmpeg_exe, "-i", video_path]
        # We run it and inspect the stderr which contains format information
        result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, errors='ignore')
        if re.search(r"Stream #\d+:\d+.*Audio:", result.stderr, re.IGNORECASE):
            return True
    except Exception as e:
        logger.warning(f"Error checking for audio stream: {e}")
    return False

def scan_video(
    video_path: str,
    static_threshold: float,
    black_threshold: float,
    white_threshold: float,
    black_pixel_limit: int,
    white_pixel_limit: int,
    sample_fps: float
) -> Tuple[float, int, List[Tuple[float, float]], List[float], List[float]]:
    """
    Scan the video to detect:
    1. Consecutive static frames (where frame difference < static_threshold)
    2. Black frames (ratio of black pixels >= black_threshold)
    3. White frames (ratio of white pixels >= white_threshold)
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Failed to open video file: {video_path}")
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    if fps <= 0:
        logger.warning("Could not determine FPS from video metadata. Defaulting to 30.0")
        fps = 30.0
        
    duration = total_frames / fps
    logger.info(f"Video Loaded: {total_frames} frames, {fps:.2f} FPS, Duration: {format_time(duration)}")
    
    # Calculate skip step based on sample_fps
    step = max(1, int(fps / sample_fps))
    logger.info(f"Analysis sampling rate: every {step} frames (~{fps/step:.1f} FPS for detection)")
    
    # Resize target for faster processing
    target_width, target_height = 160, 120
    
    prev_gray = None
    static_start_time = None
    
    static_runs = []
    black_frames = []
    white_frames = []
    
    frame_idx = 0
    start_time = time.time()
    
    while True:
        if frame_idx % step == 0:
            ret, frame = cap.read()
            if not ret:
                break
        else:
            ret = cap.grab()
            if not ret:
                break
            frame_idx += 1
            continue
            
        timestamp = frame_idx / fps
        
        # Process frame
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_small = cv2.resize(gray, (target_width, target_height))
        
        # Check black/white frames by pixel ratio
        num_pixels = gray_small.size
        black_ratio = np.sum(gray_small < black_pixel_limit) / num_pixels
        white_ratio = np.sum(gray_small > white_pixel_limit) / num_pixels
        
        if black_ratio >= black_threshold:
            black_frames.append(timestamp)
        elif white_ratio >= white_threshold:
            white_frames.append(timestamp)
            
        # Check static frames
        is_static = False
        if prev_gray is not None:
            diff = cv2.absdiff(gray_small, prev_gray)
            mean_diff = float(np.mean(diff))
            if mean_diff < static_threshold:
                is_static = True
                
        if is_static:
            if static_start_time is None:
                # The static run started at the previous sampled frame
                static_start_time = (frame_idx - step) / fps
        else:
            if static_start_time is not None:
                end_static_time = (frame_idx - step) / fps
                static_duration = end_static_time - static_start_time
                if static_duration >= 2.0:
                    static_runs.append((static_start_time, end_static_time))
                static_start_time = None
                
        prev_gray = gray_small
        frame_idx += 1
        
        # Print progress
        if frame_idx % (step * 500) == 0 or frame_idx >= total_frames:
            pct = (frame_idx / total_frames) * 100
            elapsed = time.time() - start_time
            eta = (elapsed / frame_idx) * (total_frames - frame_idx) if frame_idx > 0 else 0
            logger.info(f"Scanning progress: {pct:.1f}% ({frame_idx}/{total_frames} frames) | Elapsed: {elapsed:.1f}s | ETA: {eta:.1f}s")
            
    # Handle end of video static run
    if static_start_time is not None:
        end_static_time = (frame_idx - 1) / fps
        static_duration = end_static_time - static_start_time
        if static_duration >= 2.0:
            static_runs.append((static_start_time, end_static_time))
            
    cap.release()
    return fps, total_frames, static_runs, black_frames, white_frames

def get_keep_segments(total_duration: float, static_runs: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Get list of active (non-static) segments to keep."""
    # Sort and merge overlapping/adjacent static runs
    static_runs = sorted(static_runs, key=lambda x: x[0])
    merged_runs = []
    for start, end in static_runs:
        if not merged_runs:
            merged_runs.append((start, end))
        else:
            prev_start, prev_end = merged_runs[-1]
            if start <= prev_end + 0.1: # merge if overlapping or extremely close
                merged_runs[-1] = (prev_start, max(prev_end, end))
            else:
                merged_runs.append((start, end))
                
    keep = []
    curr = 0.0
    for start, end in merged_runs:
        # Avoid zero or extremely short segments
        if start > curr + 0.1:
            keep.append((curr, start))
        curr = end
        
    if curr + 0.1 < total_duration:
        keep.append((curr, total_duration))
        
    return keep

def map_original_to_clean(t_orig: float, keep_segments: List[Tuple[float, float]]) -> float:
    """Map original timeline timestamp to clean timeline timestamp."""
    t_clean = 0.0
    for start, end in keep_segments:
        if t_orig < start:
            return t_clean
        elif start <= t_orig <= end:
            return t_clean + (t_orig - start)
        else:
            t_clean += (end - start)
    return t_clean

def map_clean_interval_to_original(
    c_start: float,
    c_end: float,
    keep_segments: List[Tuple[float, float]]
) -> List[Tuple[float, float]]:
    """Map clean timeline interval back to a list of original timeline segments."""
    original_segments = []
    curr_clean = 0.0
    for o_start, o_end in keep_segments:
        seg_duration = o_end - o_start
        seg_clean_start = curr_clean
        seg_clean_end = curr_clean + seg_duration
        
        # Check overlap
        overlap_start = max(c_start, seg_clean_start)
        overlap_end = min(c_end, seg_clean_end)
        
        if overlap_start < overlap_end - 0.01: # ignore microscopic segments
            o_overlap_start = o_start + (overlap_start - seg_clean_start)
            o_overlap_end = o_start + (overlap_end - seg_clean_start)
            original_segments.append((o_overlap_start, o_overlap_end))
            
        curr_clean += seg_duration
        
    return original_segments

def find_split_points(
    clean_total_duration: float,
    clean_blacks: List[float],
    clean_whites: List[float],
    min_split: float,
    max_split: float
) -> List[float]:
    """Find the best split points on the clean timeline."""
    splits = []
    curr = 0.0
    
    # Combine candidate split points
    # Deduplicate and sort candidates
    all_candidates = sorted(list(set(clean_blacks + clean_whites)))
    
    mid_split = (min_split + max_split) / 2.0
    
    while clean_total_duration - curr > max_split:
        w_start = curr + min_split
        w_end = curr + max_split
        w_mid = curr + mid_split
        
        # Find candidates in current window
        win_candidates = [t for t in all_candidates if w_start <= t <= w_end]
        
        if win_candidates:
            # Pick candidate closest to midpoint
            best_split = min(win_candidates, key=lambda t: abs(t - w_mid))
            logger.info(f"Split point chosen at {format_time(best_split)} (Clean timeline) from black/white candidates.")
        else:
            # Fallback to midpoint
            best_split = w_mid
            logger.info(f"No black/white candidates found in window [{format_time(w_start)} - {format_time(w_end)}]. Splitting at midpoint: {format_time(best_split)}")
            
        splits.append(best_split)
        curr = best_split
        
    return splits

def run_ffmpeg_split(
    ffmpeg_exe: str,
    input_video: str,
    output_file: str,
    intervals: List[Tuple[float, float]],
    has_audio: bool
) -> bool:
    """Run FFmpeg to extract and concatenate the specified original video segments."""
    if not intervals:
        logger.error(f"No intervals to process for {output_file}")
        return False
        
    # If there is only one segment, we can do a simple trim
    if len(intervals) == 1:
        start, end = intervals[0]
        cmd = [
            ffmpeg_exe,
            "-ss", f"{start:.3f}",
            "-to", f"{end:.3f}",
            "-i", input_video,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23"
        ]
        if has_audio:
            cmd.extend(["-c:a", "aac"])
        else:
            cmd.append("-an")
        cmd.extend(["-y", output_file])
    else:
        # Build complex filter for multiple segments
        filter_parts = []
        concat_parts = []
        for i, (start, end) in enumerate(intervals):
            filter_parts.append(f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS[v{i}]")
            if has_audio:
                filter_parts.append(f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[a{i}]")
                concat_parts.append(f"[v{i}][a{i}]")
            else:
                concat_parts.append(f"[v{i}]")
                
        num_segments = len(intervals)
        if has_audio:
            concat_filter = f"{''.join(concat_parts)}concat=n={num_segments}:v=1:a=1[outv][outa]"
        else:
            concat_filter = f"{''.join(concat_parts)}concat=n={num_segments}:v=1:a=0[outv]"
            
        filter_complex_str = ";".join(filter_parts) + ";" + concat_filter
        
        cmd = [
            ffmpeg_exe,
            "-i", input_video,
            "-filter_complex", filter_complex_str,
            "-map", "[outv]"
        ]
        if has_audio:
            cmd.extend(["-map", "[outa]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac"])
        else:
            cmd.extend(["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"])
            
        cmd.extend(["-y", output_file])
        
    logger.info(f"Running FFmpeg to generate: {os.path.basename(output_file)}")
    logger.debug(f"FFmpeg command: {' '.join(cmd)}")
    
    # Run command and hide verbose output unless error occurs
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors='ignore')
    if result.returncode != 0:
        logger.error(f"FFmpeg failed with exit code {result.returncode}")
        logger.error(f"FFmpeg Stderr:\n{result.stderr}")
        return False
        
    logger.info(f"Successfully generated: {os.path.basename(output_file)}")
    return True

def main():
    parser = argparse.ArgumentParser(
        description="Automatic Video Editor: Remove static frames and split by black/white frames."
    )
    parser.add_argument("-i", "--input", required=True, help="Path to input video file")
    parser.add_argument("-o", "--output-dir", help="Path to output directory (defaults to input file's directory)")
    parser.add_argument("-m", "--min-split", type=float, default=30.0, help="Minimum split interval in minutes (default: 30)")
    parser.add_argument("-x", "--max-split", type=float, default=45.0, help="Maximum split interval in minutes (default: 45)")
    parser.add_argument("-s", "--static-threshold", type=float, default=0.8, help="Grayscale difference threshold for static frames (default: 0.8)")
    parser.add_argument("-b", "--black-threshold", type=float, default=0.90, help="Required ratio of black pixels in a frame (default: 0.90)")
    parser.add_argument("-w", "--white-threshold", type=float, default=0.90, help="Required ratio of white pixels in a frame (default: 0.90)")
    parser.add_argument("--black-pixel-limit", type=int, default=30, help="Max pixel value to be considered black (default: 30)")
    parser.add_argument("--white-pixel-limit", type=int, default=225, help="Min pixel value to be considered white (default: 225)")
    parser.add_argument("-f", "--sample-fps", type=float, default=10.0, help="FPS rate for scanning/sampling (default: 10.0)")
    
    args = parser.parse_args()
    
    # Input validation
    if not os.path.isfile(args.input):
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)
        
    if args.min_split >= args.max_split:
        logger.error("min-split must be strictly less than max-split")
        sys.exit(1)
        
    # Convert minutes to seconds
    min_split_sec = args.min_split * 60.0
    max_split_sec = args.max_split * 60.0
    
    input_video = os.path.abspath(args.input)
    input_dir, input_filename = os.path.split(input_video)
    name_part, ext_part = os.path.splitext(input_filename)
    
    output_dir = os.path.abspath(args.output_dir) if args.output_dir else input_dir
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Check for FFmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    if not ffmpeg_exe or not os.path.exists(ffmpeg_exe):
        logger.error("Could not find a valid FFmpeg executable.")
        sys.exit(1)
        
    has_audio = has_audio_stream(ffmpeg_exe, input_video)
    logger.info(f"Audio stream detected: {has_audio}")
    
    # 2. Scan video with OpenCV
    logger.info("Scanning video to analyze frames...")
    try:
        fps, total_frames, static_runs, black_frames, white_frames = scan_video(
            video_path=input_video,
            static_threshold=args.static_threshold,
            black_threshold=args.black_threshold,
            white_threshold=args.white_threshold,
            black_pixel_limit=args.black_pixel_limit,
            white_pixel_limit=args.white_pixel_limit,
            sample_fps=args.sample_fps
        )
    except Exception as e:
        logger.error(f"Failed to scan video: {e}")
        sys.exit(1)
        
    total_duration = total_frames / fps
    
    # Report scanning findings
    total_static_duration = sum(end - start for start, end in static_runs)
    logger.info(f"Scan complete. Found {len(static_runs)} static segments (total {total_static_duration:.2f}s).")
    logger.info(f"Found {len(black_frames)} blackframe frames, {len(white_frames)} whiteframe frames.")
    
    # 3. Calculate kept segments (remove static runs)
    keep_segments = get_keep_segments(total_duration, static_runs)
    clean_duration = sum(end - start for start, end in keep_segments)
    logger.info(f"Clean video duration (after removing static frames): {format_time(clean_duration)}")
    
    # 4. Map candidate transition points to clean timeline
    clean_blacks = [map_original_to_clean(t, keep_segments) for t in black_frames]
    clean_whites = [map_original_to_clean(t, keep_segments) for t in white_frames]
    
    # 5. Determine split points on clean timeline
    logger.info("Determining optimal split points...")
    clean_splits = find_split_points(
        clean_total_duration=clean_duration,
        clean_blacks=clean_blacks,
        clean_whites=clean_whites,
        min_split=min_split_sec,
        max_split=max_split_sec
    )
    
    clean_boundaries = [0.0] + clean_splits + [clean_duration]
    num_parts = len(clean_boundaries) - 1
    logger.info(f"Determined split boundaries: {len(clean_splits)} split points -> {num_parts} parts.")
    
    for idx in range(num_parts):
        c_start = clean_boundaries[idx]
        c_end = clean_boundaries[idx+1]
        part_dur = c_end - c_start
        logger.info(f"  Part {idx+1}: Clean range [{format_time(c_start)} - {format_time(c_end)}] (Duration: {format_time(part_dur)})")
        
    # 6. Render splits
    success_count = 0
    for idx in range(num_parts):
        c_start = clean_boundaries[idx]
        c_end = clean_boundaries[idx+1]
        
        # Map back to original timeline segments
        original_intervals = map_clean_interval_to_original(c_start, c_end, keep_segments)
        
        output_filename = f"{name_part}-{idx+1}{ext_part}"
        output_filepath = os.path.join(output_dir, output_filename)
        
        logger.info(f"Rendering Part {idx+1}/{num_parts} -> {output_filename}...")
        logger.info(f"  Consists of {len(original_intervals)} original clips.")
        
        success = run_ffmpeg_split(
            ffmpeg_exe=ffmpeg_exe,
            input_video=input_video,
            output_file=output_filepath,
            intervals=original_intervals,
            has_audio=has_audio
        )
        if success:
            success_count += 1
        else:
            logger.error(f"Failed to render Part {idx+1}")
            
    logger.info(f"Finished! Successfully generated {success_count} / {num_parts} files in '{output_dir}'.")
    
if __name__ == "__main__":
    main()
