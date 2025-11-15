#!/usr/bin/env python3
"""
Helper script to create sample test images for testing the pipeline
when you don't have real videos available.
"""
import os
import cv2
import numpy as np
from pathlib import Path


def create_sample_frame(width=640, height=360, frame_num=0, scenario='base'):
    """
    Create a synthetic road scene image for testing.
    
    Args:
        width: Image width
        height: Image height
        frame_num: Frame number (for variation)
        scenario: 'base' or 'present'
    
    Returns:
        Synthetic image
    """
    # Create base image (road scene)
    img = np.ones((height, width, 3), dtype=np.uint8) * 128
    
    # Draw road
    road_y = int(height * 0.6)
    cv2.rectangle(img, (0, road_y), (width, height), (80, 80, 80), -1)
    
    # Draw lane markings
    for i in range(0, width, 100):
        cv2.rectangle(img, (i, road_y + 20), (i + 40, road_y + 30), (255, 255, 255), -1)
    
    # Draw sky
    img[0:road_y, :] = (135, 206, 235)  # Sky blue
    
    # Add some "buildings" or poles
    if frame_num % 3 == 0:
        cv2.rectangle(img, (100, road_y - 100), (150, road_y), (100, 100, 150), -1)
    
    if frame_num % 5 == 0:
        cv2.rectangle(img, (400, road_y - 80), (430, road_y), (150, 100, 100), -1)
    
    # Add some variation for 'present' scenario
    if scenario == 'present':
        # Simulate some changes
        if frame_num % 2 == 0:
            # Add a "new" object (like a cone or sign)
            cv2.circle(img, (250, road_y - 40), 20, (0, 100, 255), -1)
        
        # Remove some markings (simulate wear)
        if frame_num % 4 == 0:
            cv2.rectangle(img, (200, road_y + 20), (240, road_y + 30), (80, 80, 80), -1)
        
        # Add a "pothole"
        if frame_num % 3 == 1:
            cv2.ellipse(img, (350, road_y + 50), (30, 20), 0, 0, 360, (60, 60, 60), -1)
    
    # Add frame number
    cv2.putText(img, f"Frame {frame_num:03d} - {scenario.upper()}", 
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    return img


def create_sample_dataset(num_frames=10, output_dir='sample_data'):
    """
    Create a sample dataset with base and present frames.
    
    Args:
        num_frames: Number of frames to generate
        output_dir: Output directory
    """
    base_dir = os.path.join(output_dir, 'base_frames')
    present_dir = os.path.join(output_dir, 'present_frames')
    
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(present_dir, exist_ok=True)
    
    print(f"Creating {num_frames} sample frames...")
    
    for i in range(num_frames):
        # Create base frame
        base_frame = create_sample_frame(frame_num=i, scenario='base')
        base_path = os.path.join(base_dir, f'frame_{i+1:05d}.jpg')
        cv2.imwrite(base_path, base_frame)
        
        # Create present frame (with some changes)
        present_frame = create_sample_frame(frame_num=i, scenario='present')
        present_path = os.path.join(present_dir, f'frame_{i+1:05d}.jpg')
        cv2.imwrite(present_path, present_frame)
        
        print(f"  Generated frame {i+1}/{num_frames}")
    
    print(f"\n✓ Sample dataset created in {output_dir}/")
    print(f"  Base frames: {base_dir}/")
    print(f"  Present frames: {present_dir}/")
    print(f"\nYou can now test the alignment script:")
    print(f"  python align_frames.py {base_dir} {present_dir} {output_dir}/aligned")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create sample test images for pipeline testing"
    )
    parser.add_argument(
        '--num-frames',
        type=int,
        default=10,
        help='Number of frames to generate (default: 10)'
    )
    parser.add_argument(
        '--output-dir',
        default='sample_data',
        help='Output directory (default: sample_data)'
    )
    
    args = parser.parse_args()
    
    create_sample_dataset(args.num_frames, args.output_dir)


if __name__ == "__main__":
    main()
