#!/usr/bin/env python3
"""
Extract frames from videos using ffmpeg and OpenCV.
Generates frame images and metadata JSON with timestamps.
"""
import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
import cv2


def extract_frames_ffmpeg(video_path, output_dir, fps=1):
    """
    Extract frames using ffmpeg at specified FPS.
    
    Args:
        video_path: Path to input video file
        output_dir: Directory to save extracted frames
        fps: Frames per second to extract (default: 1)
    
    Returns:
        List of extracted frame paths
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Build ffmpeg command
    output_pattern = os.path.join(output_dir, "frame_%05d.jpg")
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vf", f"fps={fps}",
        "-q:v", "2",  # High quality JPEG
        output_pattern
    ]
    
    print(f"Extracting frames from {video_path} at {fps} FPS...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
        print(f"[OK] Frames extracted to {output_dir}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] FFmpeg error: {e.stderr}")
        return []
    except FileNotFoundError:
        print("[INFO] FFmpeg not found. Falling back to OpenCV method...")
        return extract_frames_opencv(video_path, output_dir, fps)
    
    # Get list of extracted frames
    frames = sorted([f for f in os.listdir(output_dir) if f.endswith('.jpg')])
    frame_paths = [os.path.join(output_dir, f) for f in frames]
    
    return frame_paths


def extract_frames_opencv(video_path, output_dir, fps=1):
    """
    Extract frames using OpenCV as fallback method.
    
    Args:
        video_path: Path to input video file
        output_dir: Directory to save extracted frames
        fps: Frames per second to extract (default: 1)
    
    Returns:
        List of extracted frame paths
    """
    os.makedirs(output_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video {video_path}")
        return []
    
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(video_fps / fps) if fps > 0 else 1
    
    frame_count = 0
    saved_count = 0
    frame_paths = []
    
    print(f"Extracting frames from {video_path} at {fps} FPS (video FPS: {video_fps})...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % frame_interval == 0:
            frame_filename = f"frame_{saved_count+1:05d}.jpg"
            frame_path = os.path.join(output_dir, frame_filename)
            cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            frame_paths.append(frame_path)
            saved_count += 1
        
        frame_count += 1
    
    cap.release()
    print(f"[OK] Extracted {saved_count} frames to {output_dir}")
    
    return frame_paths


def generate_metadata(video_path, frame_paths, output_dir):
    """
    Generate metadata JSON with frame timestamps and video info.
    
    Args:
        video_path: Path to source video
        frame_paths: List of extracted frame paths
        output_dir: Directory to save metadata
    
    Returns:
        Path to metadata JSON file
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[WARNING] Cannot open video for metadata")
        return None
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    
    # Generate frame metadata
    frames_meta = []
    for idx, frame_path in enumerate(frame_paths):
        timestamp = idx / (len(frame_paths) / duration) if duration > 0 else idx
        frames_meta.append({
            "frame_id": idx + 1,
            "filename": os.path.basename(frame_path),
            "timestamp": round(timestamp, 3),
            "path": frame_path
        })
    
    metadata = {
        "video_path": os.path.abspath(video_path),
        "video_fps": fps,
        "video_duration": duration,
        "video_resolution": {"width": width, "height": height},
        "total_video_frames": total_frames,
        "extracted_frames": len(frame_paths),
        "frames": frames_meta
    }
    
    # Save metadata
    meta_path = os.path.join(output_dir, "frames_meta.json")
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"[OK] Metadata saved to {meta_path}")
    return meta_path


def main():
    parser = argparse.ArgumentParser(
        description="Extract frames from video files for road safety analysis"
    )
    parser.add_argument(
        "video_path",
        help="Path to input video file"
    )
    parser.add_argument(
        "output_dir",
        help="Directory to save extracted frames"
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=1.0,
        help="Frames per second to extract (default: 1)"
    )
    parser.add_argument(
        "--method",
        choices=["ffmpeg", "opencv"],
        default="ffmpeg",
        help="Extraction method (default: ffmpeg)"
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.video_path):
        print(f"[ERROR] Video file not found: {args.video_path}")
        sys.exit(1)
    
    # Extract frames
    if args.method == "ffmpeg":
        frame_paths = extract_frames_ffmpeg(args.video_path, args.output_dir, args.fps)
    else:
        frame_paths = extract_frames_opencv(args.video_path, args.output_dir, args.fps)
    
    if not frame_paths:
        print("[ERROR] No frames extracted. Exiting.")
        sys.exit(1)
    
    # Generate metadata
    generate_metadata(args.video_path, frame_paths, args.output_dir)
    
    print(f"\n[SUCCESS] Complete! Extracted {len(frame_paths)} frames.")


if __name__ == "__main__":
    main()
