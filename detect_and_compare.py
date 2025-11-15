#!/usr/bin/env python3
"""
Main pipeline script for detecting and comparing road elements.
Computes SSIM, IoU metrics, and severity scoring.
"""
import os
import sys
import json
import argparse
import numpy as np
import cv2
from pathlib import Path
from ultralytics import YOLO
from skimage.metrics import structural_similarity as ssim

# Import our modules
from detect_elements import detect_objects_yolo, detect_road_markings, detect_potholes
from match_detections import match_detections, categorize_changes


def compute_ssim(img1, img2):
    """
    Compute Structural Similarity Index (SSIM) between two images.
    
    Args:
        img1: First image (base)
        img2: Second image (present)
    
    Returns:
        SSIM score (0.0 to 1.0) and difference image
    """
    # Convert to grayscale if needed
    if len(img1.shape) == 3:
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    else:
        gray1 = img1
    
    if len(img2.shape) == 3:
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    else:
        gray2 = img2
    
    # Ensure same dimensions
    if gray1.shape != gray2.shape:
        gray2 = cv2.resize(gray2, (gray1.shape[1], gray1.shape[0]))
    
    # Compute SSIM
    score, diff = ssim(gray1, gray2, full=True)
    diff = (diff * 255).astype("uint8")
    
    return score, diff


def compute_region_ssim(img1, img2, bbox):
    """
    Compute SSIM for a specific region (bounding box).
    
    Args:
        img1: Base image
        img2: Present image
        bbox: Bounding box [x1, y1, x2, y2]
    
    Returns:
        SSIM score for the region
    """
    x1, y1, x2, y2 = [int(coord) for coord in bbox]
    
    # Ensure coordinates are within image bounds
    h1, w1 = img1.shape[:2]
    h2, w2 = img2.shape[:2]
    
    x1 = max(0, min(x1, min(w1, w2) - 1))
    y1 = max(0, min(y1, min(h1, h2) - 1))
    x2 = max(x1 + 1, min(x2, min(w1, w2)))
    y2 = max(y1 + 1, min(y2, min(h1, h2)))
    
    # Extract regions
    region1 = img1[y1:y2, x1:x2]
    region2 = img2[y1:y2, x1:x2]
    
    if region1.size == 0 or region2.size == 0:
        return 0.0
    
    # Compute SSIM for region
    score, _ = compute_ssim(region1, region2)
    return score


def determine_severity(iou, ssim_score, is_missing=False, is_new=False):
    """
    Determine severity level based on IoU and SSIM scores.
    
    Args:
        iou: Intersection over Union score
        ssim_score: Structural Similarity score
        is_missing: Whether element is missing in present
        is_new: Whether element is new in present
    
    Returns:
        Tuple of (severity_level, severity_score)
    """
    if is_missing:
        return "SEVERE", 1.0
    
    if is_new:
        return "NEW", 0.9
    
    # Combine IoU and SSIM for severity
    combined_score = (iou + ssim_score) / 2
    
    if combined_score >= 0.9:
        severity = "UNCHANGED"
        score = 0.0
    elif combined_score >= 0.75:
        severity = "MINOR"
        score = 0.3
    elif combined_score >= 0.5:
        severity = "MODERATE"
        score = 0.6
    else:
        severity = "SEVERE"
        score = 0.9
    
    return severity, score


def process_frame_pair(base_path, present_path, model, device=0):
    """
    Process a single frame pair with all detection and comparison methods.
    
    Args:
        base_path: Path to base frame
        present_path: Path to present frame
        model: YOLO model
        device: Device for inference
    
    Returns:
        Dictionary with all analysis results
    """
    print(f"\n{'='*60}")
    print(f"Processing frame pair:")
    print(f"  Base: {os.path.basename(base_path)}")
    print(f"  Present: {os.path.basename(present_path)}")
    print(f"  Device: {'GPU' if device != 'cpu' else 'CPU'}")
    print('='*60)
    
    # Load images
    base_img = cv2.imread(base_path)
    present_img = cv2.imread(present_path)
    
    if base_img is None or present_img is None:
        print("[ERROR] Error loading images")
        return None
    
    print(f"Images loaded: {base_img.shape}")
    
    # Compute overall SSIM
    print("  Computing SSIM...")
    overall_ssim, diff_img = compute_ssim(base_img, present_img)
    print(f"  [OK] Overall SSIM: {overall_ssim:.4f}")
    
    # Detect elements in both frames
    print("\n  Detecting elements in base frame...")
    base_objects = detect_objects_yolo(base_path, model, device)
    base_markings_mask, base_markings = detect_road_markings(base_path)
    base_potholes_mask, base_potholes = detect_potholes(base_path)
    
    print(f"  [OK] Base: {len(base_objects)} objects, {len(base_potholes)} potholes")
    
    print("\n  Detecting elements in present frame...")
    present_objects = detect_objects_yolo(present_path, model, device)
    present_markings_mask, present_markings = detect_road_markings(present_path)
    present_potholes_mask, present_potholes = detect_potholes(present_path)
    
    print(f"  [OK] Present: {len(present_objects)} objects, {len(present_potholes)} potholes")
    
    # Match detections
    print("\n  Matching detections...")
    object_matches = match_detections(base_objects, present_objects, iou_threshold=0.3)
    pothole_matches = match_detections(base_potholes, present_potholes, 
                                       iou_threshold=0.3, same_class_only=False)
    
    print(f"  [OK] Matched: {len(object_matches['matches'])} | Missing: {len(object_matches['missing'])} | New: {len(object_matches['new'])}")
    
    # Compute detailed metrics for matched objects
    detailed_matches = []
    for match in object_matches['matches']:
        # Compute region SSIM
        region_ssim = compute_region_ssim(base_img, present_img, match['base_bbox'])
        
        # Determine severity
        severity, severity_score = determine_severity(match['iou'], region_ssim)
        
        detailed_match = {
            **match,
            "region_ssim": float(region_ssim),
            "severity": severity,
            "severity_score": float(severity_score),
            "combined_score": float((match['iou'] + region_ssim) / 2)
        }
        detailed_matches.append(detailed_match)
    
    # Handle missing elements
    missing_elements = []
    for missing in object_matches['missing']:
        severity, severity_score = determine_severity(0, 0, is_missing=True)
        missing_elements.append({
            **missing,
            "severity": severity,
            "severity_score": float(severity_score)
        })
    
    # Handle new elements
    new_elements = []
    for new in object_matches['new']:
        severity, severity_score = determine_severity(0, 0, is_new=True)
        new_elements.append({
            **new,
            "severity": severity,
            "severity_score": float(severity_score)
        })
    
    # Compile results
    results = {
        "base_frame": base_path,
        "present_frame": present_path,
        "overall_ssim": float(overall_ssim),
        "total_base_objects": len(base_objects),
        "total_present_objects": len(present_objects),
        "matched_objects": detailed_matches,
        "missing_objects": missing_elements,
        "new_objects": new_elements,
        "potholes": {
            "base_count": len(base_potholes),
            "present_count": len(present_potholes),
            "new_potholes": len(pothole_matches['new']),
            "filled_potholes": len(pothole_matches['missing']),
            "matches": pothole_matches['matches']
        },
        "flagged_changes": len(missing_elements) + len(new_elements) + 
                          sum(1 for m in detailed_matches if m['severity'] in ['MODERATE', 'SEVERE'])
    }
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Detect and compare road elements between base and present frames"
    )
    parser.add_argument(
        "base_dir",
        help="Directory with base (aligned) frames"
    )
    parser.add_argument(
        "present_dir",
        help="Directory with present (aligned) frames"
    )
    parser.add_argument(
        "output_dir",
        help="Directory to save results"
    )
    parser.add_argument(
        "--model",
        default="yolov8n.pt",
        help="YOLOv8 model (default: yolov8n.pt)"
    )
    parser.add_argument(
        "--device",
        default="0",
        help="Device (0 for GPU, cpu for CPU)"
    )
    parser.add_argument(
        "--max-pairs",
        type=int,
        default=None,
        help="Maximum number of frame pairs to process"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load YOLO model
    print(f"Loading YOLO model: {args.model}")
    try:
        model = YOLO(args.model)
        device = 0 if args.device != 'cpu' and args.device.isdigit() else 'cpu'
        
        # Move model to device
        if device != 'cpu':
            model.to(device)
            print(f"[OK] Model loaded on GPU device: {device}")
        else:
            print(f"[OK] Model loaded on CPU")
    except Exception as e:
        print(f"[ERROR] Error loading model: {e}")
        print("[INFO] Downloading YOLO model...")
        try:
            # Force download by using a specific path
            from ultralytics import download
            model = YOLO(args.model)
            device = 0 if args.device != 'cpu' and args.device.isdigit() else 'cpu'
            if device != 'cpu':
                model.to(device)
            print("[OK] Model downloaded and loaded")
        except Exception as e2:
            print(f"[ERROR] Failed to download model: {e2}")
            sys.exit(1)
    
    # Get frame pairs
    base_frames = sorted([f for f in os.listdir(args.base_dir) 
                         if f.endswith(('.jpg', '.png'))])
    present_frames = sorted([f for f in os.listdir(args.present_dir) 
                            if f.endswith(('.jpg', '.png'))])
    
    pairs = list(zip(base_frames, present_frames))
    if args.max_pairs:
        pairs = pairs[:args.max_pairs]
    
    print(f"\nProcessing {len(pairs)} frame pairs...")
    
    # Process each pair
    all_results = []
    for i, (base_frame, present_frame) in enumerate(pairs, 1):
        base_path = os.path.join(args.base_dir, base_frame)
        present_path = os.path.join(args.present_dir, present_frame)
        
        print(f"\n{'='*60}")
        print(f"Frame pair {i}/{len(pairs)}")
        
        result = process_frame_pair(base_path, present_path, model, device)
        if result:
            result['pair_id'] = i
            all_results.append(result)
    
    # Save detailed results
    results_file = os.path.join(args.output_dir, "analysis_results.json")
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"[SUCCESS] Analysis complete! Results saved to {results_file}")
    
    # Print summary
    total_flagged = sum(r['flagged_changes'] for r in all_results)
    total_missing = sum(len(r['missing_objects']) for r in all_results)
    total_new = sum(len(r['new_objects']) for r in all_results)
    
    print(f"\nSummary:")
    print(f"  Processed frames: {len(all_results)}")
    print(f"  Total flagged changes: {total_flagged}")
    print(f"  Missing objects: {total_missing}")
    print(f"  New objects: {total_new}")


if __name__ == "__main__":
    main()
