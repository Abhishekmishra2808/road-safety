#!/usr/bin/env python3
"""
End-to-end pipeline orchestrator for road safety analysis.
Runs the complete workflow from video input to final reports.
"""
import os
import sys
import argparse
import subprocess
import json
import shutil
from datetime import datetime
from pathlib import Path


def run_command(cmd, description):
    """
    Run a shell command and handle errors.
    
    Args:
        cmd: Command to run (list of strings)
        description: Description of the command for logging
    
    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Step: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        # Print with safe encoding handling for Windows console
        try:
            print(result.stdout)
        except UnicodeEncodeError:
            # Fallback: replace problematic characters
            safe_output = result.stdout.encode('ascii', 'replace').decode('ascii')
            print(safe_output)
        
        if result.stderr:
            try:
                print("Warnings:", result.stderr)
            except UnicodeEncodeError:
                safe_stderr = result.stderr.encode('ascii', 'replace').decode('ascii')
                print("Warnings:", safe_stderr)
        
        print(f"[OK] {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Error in {description}")
        print(f"Return code: {e.returncode}")
        
        try:
            print(f"Output: {e.stdout}")
        except UnicodeEncodeError:
            print(f"Output: {e.stdout.encode('ascii', 'replace').decode('ascii')}")
        
        try:
            print(f"Error: {e.stderr}")
        except UnicodeEncodeError:
            print(f"Error: {e.stderr.encode('ascii', 'replace').decode('ascii')}")
        
        return False
    except FileNotFoundError:
        print(f"[ERROR] Command not found. Please ensure all dependencies are installed.")
        return False


def setup_directories(base_output):
    """
    Create all necessary output directories.
    
    Args:
        base_output: Base output directory path
    
    Returns:
        Dictionary of directory paths
    """
    dirs = {
        'base_frames': os.path.join(base_output, 'base_frames'),
        'present_frames': os.path.join(base_output, 'present_frames'),
        'aligned': os.path.join(base_output, 'aligned'),
        'results': os.path.join(base_output, 'results'),
        'temp': os.path.join(base_output, 'temp')
    }
    
    for dir_path in dirs.values():
        os.makedirs(dir_path, exist_ok=True)
    
    return dirs


def run_pipeline(base_video, present_video, output_dir, 
                 fps=1, max_pairs=None, model='yolov8n.pt', device='0'):
    """
    Run the complete analysis pipeline.
    
    Args:
        base_video: Path to base video
        present_video: Path to present video
        output_dir: Output directory
        fps: Frames per second to extract
        max_pairs: Maximum frame pairs to process
        model: YOLO model to use
        device: Device for inference
    
    Returns:
        True if pipeline completed successfully
    """
    print("\n" + "="*60)
    print("ROAD SAFETY ANALYSIS PIPELINE")
    print("="*60)
    print(f"Base video: {base_video}")
    print(f"Present video: {present_video}")
    print(f"Output directory: {output_dir}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Setup directories
    dirs = setup_directories(output_dir)
    
    # Get Python executable path
    python_exe = sys.executable
    
    # Step 1: Extract frames from base video
    cmd = [
        python_exe, 'extract_frames.py',
        base_video,
        dirs['base_frames'],
        '--fps', str(fps)
    ]
    if not run_command(cmd, "Extract frames from base video"):
        return False
    
    # Step 2: Extract frames from present video
    cmd = [
        python_exe, 'extract_frames.py',
        present_video,
        dirs['present_frames'],
        '--fps', str(fps)
    ]
    if not run_command(cmd, "Extract frames from present video"):
        return False
    
    # Step 3: Align frames
    cmd = [
        python_exe, 'align_frames.py',
        dirs['base_frames'],
        dirs['present_frames'],
        dirs['aligned']
    ]
    if max_pairs:
        cmd.extend(['--max_pairs', str(max_pairs)])
    
    if not run_command(cmd, "Align frame pairs"):
        return False
    
    # Step 4: Detect and compare
    aligned_base = os.path.join(dirs['aligned'])
    aligned_present = os.path.join(dirs['aligned'])
    
    cmd = [
        python_exe, 'detect_and_compare.py',
        aligned_base,
        aligned_present,
        dirs['temp'],
        '--model', model,
        '--device', device
    ]
    if max_pairs:
        cmd.extend(['--max-pairs', str(max_pairs)])
    
    if not run_command(cmd, "Detect and compare elements"):
        return False
    
    # Step 5: Generate reports
    analysis_results = os.path.join(dirs['temp'], 'analysis_results.json')
    
    cmd = [
        python_exe, 'generate_report.py',
        analysis_results,
        dirs['results']
    ]
    
    if not run_command(cmd, "Generate reports"):
        return False
    
    # Cleanup temp files (optional)
    # shutil.rmtree(dirs['temp'])
    
    print("\n" + "="*60)
    print("[SUCCESS] PIPELINE COMPLETED SUCCESSFULLY!")
    print("="*60)
    print(f"Results location: {dirs['results']}")
    print(f"  - Evidence images: {os.path.join(dirs['results'], 'evidence')}")
    print(f"  - CSV report: {os.path.join(dirs['results'], 'changes.csv')}")
    print(f"  - PDF summary: {os.path.join(dirs['results'], 'summary.pdf')}")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="End-to-end road safety analysis pipeline"
    )
    parser.add_argument(
        "base_video",
        help="Path to base video file"
    )
    parser.add_argument(
        "present_video",
        help="Path to present video file"
    )
    parser.add_argument(
        "output_dir",
        help="Directory to save all outputs"
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=1.0,
        help="Frames per second to extract (default: 1)"
    )
    parser.add_argument(
        "--max-pairs",
        type=int,
        default=None,
        help="Maximum frame pairs to process (for quick testing)"
    )
    parser.add_argument(
        "--model",
        default="yolov8n.pt",
        help="YOLO model to use (default: yolov8n.pt)"
    )
    parser.add_argument(
        "--device",
        default="0",
        help="Device for inference (0 for GPU, cpu for CPU)"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.base_video):
        print(f"✗ Error: Base video not found: {args.base_video}")
        sys.exit(1)
    
    if not os.path.exists(args.present_video):
        print(f"✗ Error: Present video not found: {args.present_video}")
        sys.exit(1)
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Run pipeline
    success = run_pipeline(
        args.base_video,
        args.present_video,
        args.output_dir,
        args.fps,
        args.max_pairs,
        args.model,
        args.device
    )
    
    if not success:
        print("\n[ERROR] Pipeline failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
