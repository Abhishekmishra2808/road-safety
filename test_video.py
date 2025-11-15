#!/usr/bin/env python3
"""
Diagnostic script to test video reading and identify issues.
"""
import os
import sys
import cv2


def test_video(video_path):
    """Test if a video can be opened and read."""
    print(f"\n{'='*60}")
    print(f"Testing video: {video_path}")
    print('='*60)
    
    # Check if file exists
    if not os.path.exists(video_path):
        print(f"[ERROR] File not found: {video_path}")
        return False
    
    print(f"[OK] File exists")
    print(f"File size: {os.path.getsize(video_path) / (1024*1024):.2f} MB")
    
    # Try to open with OpenCV
    print("\nAttempting to open with OpenCV...")
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print("[ERROR] OpenCV cannot open the video file")
        print("\nPossible reasons:")
        print("  1. Unsupported video codec")
        print("  2. Corrupted video file")
        print("  3. Missing codecs on your system")
        print("\nTry converting the video to a compatible format:")
        print(f"  ffmpeg -i {video_path} -c:v libx264 -c:a aac output.mp4")
        cap.release()
        return False
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = frame_count / fps if fps > 0 else 0
    
    print(f"[OK] Video opened successfully")
    print(f"\nVideo Properties:")
    print(f"  Resolution: {width}x{height}")
    print(f"  FPS: {fps:.2f}")
    print(f"  Total frames: {frame_count}")
    print(f"  Duration: {duration:.2f} seconds")
    
    # Try to read first frame
    print("\nAttempting to read first frame...")
    ret, frame = cap.read()
    
    if not ret or frame is None:
        print("[ERROR] Cannot read frames from video")
        cap.release()
        return False
    
    print(f"[OK] Successfully read frame")
    print(f"  Frame shape: {frame.shape}")
    
    cap.release()
    
    print("\n[SUCCESS] Video is valid and can be processed!")
    return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test if video files can be read by the analysis system"
    )
    parser.add_argument(
        "video_paths",
        nargs='+',
        help="Path(s) to video file(s) to test"
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("Video File Diagnostic Tool")
    print("="*60)
    
    all_ok = True
    for video_path in args.video_paths:
        if not test_video(video_path):
            all_ok = False
    
    print("\n" + "="*60)
    if all_ok:
        print("[SUCCESS] All videos are valid!")
        print("\nYou can now run the analysis:")
        if len(args.video_paths) == 2:
            print(f"  python run_pipeline_quick.py \"{args.video_paths[0]}\" \"{args.video_paths[1]}\" output")
    else:
        print("[ERROR] Some videos have issues")
        print("\nPlease fix the issues above before running analysis")
    print("="*60)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: python test_video.py <video_file> [video_file2 ...]")
        print("\nExample:")
        print("  python test_video.py base.mp4 present.mp4")
        sys.exit(1)
    
    main()
