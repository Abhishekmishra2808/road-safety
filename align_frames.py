#!/usr/bin/env python3
"""
Match and align frames between base and present videos using homography.
Uses ORB/SIFT feature detection + RANSAC for robust alignment.
"""
import os
import sys
import json
import argparse
import numpy as np
import cv2
from pathlib import Path


def load_image_pairs(base_dir, present_dir, max_pairs=None):
    """
    Load pairs of frames from base and present directories.
    Matches by frame number/index.
    
    Args:
        base_dir: Directory containing base frames
        present_dir: Directory containing present frames
        max_pairs: Maximum number of pairs to process (None for all)
    
    Returns:
        List of tuples (base_path, present_path)
    """
    base_frames = sorted([f for f in os.listdir(base_dir) if f.endswith(('.jpg', '.png'))])
    present_frames = sorted([f for f in os.listdir(present_dir) if f.endswith(('.jpg', '.png'))])
    
    # Match frames by index
    pairs = []
    for i, (base_frame, present_frame) in enumerate(zip(base_frames, present_frames)):
        if max_pairs and i >= max_pairs:
            break
        base_path = os.path.join(base_dir, base_frame)
        present_path = os.path.join(present_dir, present_frame)
        pairs.append((base_path, present_path))
    
    print(f"Found {len(pairs)} frame pairs to align")
    return pairs


def detect_and_match_features(img1, img2, method='orb', max_features=2000):
    """
    Detect features and match them between two images.
    
    Args:
        img1: Base image (grayscale)
        img2: Present image (grayscale)
        method: Feature detection method ('orb' or 'sift')
        max_features: Maximum number of features to detect
    
    Returns:
        Tuple of (matches, keypoints1, keypoints2, descriptors1, descriptors2)
    """
    # Initialize detector
    if method.lower() == 'sift':
        try:
            detector = cv2.SIFT_create(nfeatures=max_features)
        except AttributeError:
            print("SIFT not available, falling back to ORB")
            detector = cv2.ORB_create(nfeatures=max_features)
    else:
        detector = cv2.ORB_create(nfeatures=max_features)
    
    # Detect keypoints and compute descriptors
    kp1, desc1 = detector.detectAndCompute(img1, None)
    kp2, desc2 = detector.detectAndCompute(img2, None)
    
    if desc1 is None or desc2 is None:
        return [], kp1, kp2, desc1, desc2
    
    # Match features
    if method.lower() == 'sift':
        # FLANN matcher for SIFT
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        matcher = cv2.FlannBasedMatcher(index_params, search_params)
        matches = matcher.knnMatch(desc1, desc2, k=2)
        
        # Lowe's ratio test
        good_matches = []
        for m_n in matches:
            if len(m_n) == 2:
                m, n = m_n
                if m.distance < 0.7 * n.distance:
                    good_matches.append(m)
    else:
        # Brute force matcher for ORB
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = matcher.match(desc1, desc2)
        good_matches = sorted(matches, key=lambda x: x.distance)[:max_features//2]
    
    return good_matches, kp1, kp2, desc1, desc2


def estimate_homography(matches, kp1, kp2, min_matches=10):
    """
    Estimate homography matrix using RANSAC.
    
    Args:
        matches: List of matched features
        kp1: Keypoints from base image
        kp2: Keypoints from present image
        min_matches: Minimum number of matches required
    
    Returns:
        Homography matrix (3x3) or None if estimation fails
    """
    if len(matches) < min_matches:
        print(f"  [ERROR] Insufficient matches: {len(matches)} < {min_matches}")
        return None
    
    # Extract matched keypoint locations
    pts1 = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    pts2 = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
    
    # Estimate homography with RANSAC
    H, mask = cv2.findHomography(pts2, pts1, cv2.RANSAC, 5.0)
    
    if H is None:
        print(f"  [ERROR] Homography estimation failed")
        return None
    
    inliers = np.sum(mask)
    print(f"  [OK] Homography estimated: {len(matches)} matches, {inliers} inliers")
    
    return H


def warp_image(img, H, reference_shape):
    """
    Warp image using homography matrix.
    
    Args:
        img: Image to warp
        H: Homography matrix
        reference_shape: Shape of reference image (height, width)
    
    Returns:
        Warped image
    """
    h, w = reference_shape[:2]
    warped = cv2.warpPerspective(img, H, (w, h))
    return warped


def align_frame_pair(base_path, present_path, output_dir, idx, method='orb'):
    """
    Align a single frame pair and save results.
    
    Args:
        base_path: Path to base frame
        present_path: Path to present frame
        output_dir: Directory to save aligned frames
        idx: Frame pair index
        method: Feature detection method
    
    Returns:
        Dictionary with alignment results
    """
    # Load images
    base_img = cv2.imread(base_path)
    present_img = cv2.imread(present_path)
    
    if base_img is None or present_img is None:
        print(f"[ERROR] Failed to load images: {base_path}, {present_path}")
        return None
    
    # Convert to grayscale for feature detection
    base_gray = cv2.cvtColor(base_img, cv2.COLOR_BGR2GRAY)
    present_gray = cv2.cvtColor(present_img, cv2.COLOR_BGR2GRAY)
    
    # Detect and match features
    matches, kp1, kp2, _, _ = detect_and_match_features(
        base_gray, present_gray, method=method
    )
    
    if not matches:
        print(f"[ERROR] No matches found for pair {idx}")
        return None
    
    # Estimate homography
    H = estimate_homography(matches, kp1, kp2)
    
    if H is None:
        return None
    
    # Warp present image to align with base
    aligned_present = warp_image(present_img, H, base_img.shape)
    
    # Save aligned images
    base_filename = f"base_{idx:05d}.jpg"
    present_filename = f"present_{idx:05d}_aligned.jpg"
    
    base_output = os.path.join(output_dir, base_filename)
    present_output = os.path.join(output_dir, present_filename)
    
    cv2.imwrite(base_output, base_img)
    cv2.imwrite(present_output, aligned_present)
    
    # Return alignment info
    return {
        "pair_id": idx,
        "base_frame": base_filename,
        "present_frame": present_filename,
        "num_matches": len(matches),
        "homography": H.tolist(),
        "base_path": base_output,
        "present_path": present_output
    }


def main():
    parser = argparse.ArgumentParser(
        description="Align frames from base and present videos using homography"
    )
    parser.add_argument(
        "base_dir",
        help="Directory containing base frames"
    )
    parser.add_argument(
        "present_dir",
        help="Directory containing present frames"
    )
    parser.add_argument(
        "output_dir",
        help="Directory to save aligned frames"
    )
    parser.add_argument(
        "--max_pairs",
        type=int,
        default=None,
        help="Maximum number of frame pairs to process"
    )
    parser.add_argument(
        "--method",
        choices=['orb', 'sift'],
        default='orb',
        help="Feature detection method (default: orb)"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.base_dir):
        print(f"[ERROR] Base directory not found: {args.base_dir}")
        sys.exit(1)
    
    if not os.path.exists(args.present_dir):
        print(f"[ERROR] Present directory not found: {args.present_dir}")
        sys.exit(1)
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load frame pairs
    pairs = load_image_pairs(args.base_dir, args.present_dir, args.max_pairs)
    
    if not pairs:
        print("[ERROR] No frame pairs found")
        sys.exit(1)
    
    # Align each pair
    print(f"\nAligning {len(pairs)} frame pairs using {args.method.upper()}...")
    results = []
    
    for idx, (base_path, present_path) in enumerate(pairs, 1):
        print(f"\nProcessing pair {idx}/{len(pairs)}...")
        result = align_frame_pair(
            base_path, present_path, args.output_dir, idx, args.method
        )
        if result:
            results.append(result)
    
    # Save alignment metadata
    metadata = {
        "base_dir": os.path.abspath(args.base_dir),
        "present_dir": os.path.abspath(args.present_dir),
        "output_dir": os.path.abspath(args.output_dir),
        "method": args.method,
        "total_pairs": len(pairs),
        "successful_alignments": len(results),
        "alignments": results
    }
    
    meta_path = os.path.join(args.output_dir, "alignment_meta.json")
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n[SUCCESS] Aligned {len(results)}/{len(pairs)} frame pairs")
    print(f"[OK] Results saved to {args.output_dir}")
    print(f"[OK] Metadata saved to {meta_path}")


if __name__ == "__main__":
    main()
