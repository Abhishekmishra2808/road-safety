#!/usr/bin/env python3
"""
Match detections across before/after frames using IoU.
Associates detected elements between base and present images.
"""
import os
import sys
import json
import argparse
import numpy as np


def calculate_iou(box1, box2):
    """
    Calculate Intersection over Union (IoU) between two bounding boxes.
    
    Args:
        box1: [x1, y1, x2, y2]
        box2: [x1, y1, x2, y2]
    
    Returns:
        IoU score (0.0 to 1.0)
    """
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2
    
    # Calculate intersection area
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)
    
    if x2_i < x1_i or y2_i < y1_i:
        return 0.0
    
    intersection = (x2_i - x1_i) * (y2_i - y1_i)
    
    # Calculate union area
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union = area1 + area2 - intersection
    
    if union == 0:
        return 0.0
    
    return intersection / union


def calculate_center_distance(box1, box2):
    """
    Calculate Euclidean distance between box centers.
    
    Args:
        box1: [x1, y1, x2, y2]
        box2: [x1, y1, x2, y2]
    
    Returns:
        Distance in pixels
    """
    center1 = [(box1[0] + box1[2]) / 2, (box1[1] + box1[3]) / 2]
    center2 = [(box2[0] + box2[2]) / 2, (box2[1] + box2[3]) / 2]
    
    distance = np.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)
    return distance


def match_detections(base_detections, present_detections, iou_threshold=0.3, same_class_only=True):
    """
    Match detections between base and present frames.
    
    Args:
        base_detections: List of detections from base frame
        present_detections: List of detections from present frame
        iou_threshold: Minimum IoU for a valid match
        same_class_only: Only match detections of the same class
    
    Returns:
        Dictionary with matched, missing, and new detections
    """
    matches = []
    unmatched_base = list(range(len(base_detections)))
    unmatched_present = list(range(len(present_detections)))
    
    # Create IoU matrix
    iou_matrix = np.zeros((len(base_detections), len(present_detections)))
    
    for i, base_det in enumerate(base_detections):
        for j, present_det in enumerate(present_detections):
            # Check class match if required
            if same_class_only and base_det.get('class_name') != present_det.get('class_name'):
                continue
            
            # Calculate IoU
            iou = calculate_iou(base_det['bbox'], present_det['bbox'])
            iou_matrix[i, j] = iou
    
    # Greedy matching: find best matches iteratively
    while True:
        # Find maximum IoU
        if iou_matrix.size == 0:
            break
        
        max_iou = np.max(iou_matrix)
        
        if max_iou < iou_threshold:
            break
        
        # Find indices of maximum IoU
        i, j = np.unravel_index(np.argmax(iou_matrix), iou_matrix.shape)
        
        # Calculate additional metrics
        distance = calculate_center_distance(
            base_detections[i]['bbox'],
            present_detections[j]['bbox']
        )
        
        # Record match
        match = {
            "base_id": int(i),
            "present_id": int(j),
            "iou": float(max_iou),
            "distance": float(distance),
            "class_name": base_detections[i].get('class_name'),
            "base_bbox": base_detections[i]['bbox'],
            "present_bbox": present_detections[j]['bbox'],
            "base_confidence": base_detections[i].get('confidence', 1.0),
            "present_confidence": present_detections[j].get('confidence', 1.0)
        }
        matches.append(match)
        
        # Remove matched indices
        if i in unmatched_base:
            unmatched_base.remove(i)
        if j in unmatched_present:
            unmatched_present.remove(j)
        
        # Zero out row and column
        iou_matrix[i, :] = 0
        iou_matrix[:, j] = 0
    
    # Compile results
    results = {
        "matches": matches,
        "missing": [
            {
                "base_id": idx,
                "class_name": base_detections[idx].get('class_name'),
                "bbox": base_detections[idx]['bbox'],
                "confidence": base_detections[idx].get('confidence', 1.0)
            }
            for idx in unmatched_base
        ],
        "new": [
            {
                "present_id": idx,
                "class_name": present_detections[idx].get('class_name'),
                "bbox": present_detections[idx]['bbox'],
                "confidence": present_detections[idx].get('confidence', 1.0)
            }
            for idx in unmatched_present
        ]
    }
    
    return results


def categorize_changes(matches, iou_high=0.7, iou_medium=0.3):
    """
    Categorize matched detections by change severity based on IoU.
    
    Args:
        matches: List of matched detections
        iou_high: IoU threshold for unchanged/minor change
        iou_medium: IoU threshold for moderate change
    
    Returns:
        Dictionary with categorized matches
    """
    unchanged = []
    minor_changes = []
    moderate_changes = []
    severe_changes = []
    
    for match in matches:
        iou = match['iou']
        
        if iou >= iou_high:
            unchanged.append(match)
        elif iou >= iou_medium:
            minor_changes.append(match)
        elif iou >= iou_medium * 0.5:
            moderate_changes.append(match)
        else:
            severe_changes.append(match)
    
    return {
        "unchanged": unchanged,
        "minor": minor_changes,
        "moderate": moderate_changes,
        "severe": severe_changes
    }


def match_frame_pair(base_frame_detections, present_frame_detections, 
                     iou_threshold=0.3, categorize=True):
    """
    Match detections for a single frame pair.
    
    Args:
        base_frame_detections: Detections from base frame
        present_frame_detections: Detections from present frame
        iou_threshold: IoU threshold for matching
        categorize: Whether to categorize changes by severity
    
    Returns:
        Dictionary with matching results
    """
    # Match objects
    base_objects = base_frame_detections.get('objects', [])
    present_objects = present_frame_detections.get('objects', [])
    
    object_matches = match_detections(base_objects, present_objects, iou_threshold)
    
    results = {
        "object_matches": object_matches,
        "total_base_objects": len(base_objects),
        "total_present_objects": len(present_objects),
        "matched_objects": len(object_matches['matches']),
        "missing_objects": len(object_matches['missing']),
        "new_objects": len(object_matches['new'])
    }
    
    if categorize:
        categories = categorize_changes(object_matches['matches'])
        results["categories"] = categories
        results["unchanged_count"] = len(categories['unchanged'])
        results["minor_changes_count"] = len(categories['minor'])
        results["moderate_changes_count"] = len(categories['moderate'])
        results["severe_changes_count"] = len(categories['severe'])
    
    # Add pothole and marking info
    base_potholes = base_frame_detections.get('potholes', [])
    present_potholes = present_frame_detections.get('potholes', [])
    
    if base_potholes or present_potholes:
        pothole_matches = match_detections(base_potholes, present_potholes, iou_threshold, same_class_only=False)
        results["pothole_matches"] = pothole_matches
        results["new_potholes"] = len(pothole_matches['new'])
        results["filled_potholes"] = len(pothole_matches['missing'])
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Match detections across before/after frames using IoU"
    )
    parser.add_argument(
        "base_detections",
        help="JSON file with base frame detections"
    )
    parser.add_argument(
        "present_detections",
        help="JSON file with present frame detections"
    )
    parser.add_argument(
        "output_file",
        help="Output JSON file for matching results"
    )
    parser.add_argument(
        "--iou-threshold",
        type=float,
        default=0.3,
        help="IoU threshold for matching (default: 0.3)"
    )
    
    args = parser.parse_args()
    
    # Load detections
    print(f"Loading base detections from {args.base_detections}")
    with open(args.base_detections, 'r') as f:
        base_data = json.load(f)
    
    print(f"Loading present detections from {args.present_detections}")
    with open(args.present_detections, 'r') as f:
        present_data = json.load(f)
    
    # Match each frame pair
    if isinstance(base_data, list) and isinstance(present_data, list):
        # Multiple frames
        print(f"\nMatching {min(len(base_data), len(present_data))} frame pairs...")
        all_results = []
        
        for i, (base_frame, present_frame) in enumerate(zip(base_data, present_data)):
            print(f"  Matching frame pair {i+1}...")
            result = match_frame_pair(base_frame, present_frame, args.iou_threshold)
            result["frame_id"] = i + 1
            result["base_image"] = base_frame.get('image_path')
            result["present_image"] = present_frame.get('image_path')
            all_results.append(result)
        
        output = {
            "total_frames": len(all_results),
            "iou_threshold": args.iou_threshold,
            "frame_matches": all_results
        }
    else:
        # Single frame pair
        print("\nMatching single frame pair...")
        result = match_frame_pair(base_data, present_data, args.iou_threshold)
        output = result
    
    # Save results
    os.makedirs(os.path.dirname(args.output_file) or '.', exist_ok=True)
    with open(args.output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✓ Matching complete! Results saved to {args.output_file}")
    
    # Print summary
    if isinstance(output, dict) and 'frame_matches' in output:
        total_matched = sum(r['matched_objects'] for r in output['frame_matches'])
        total_missing = sum(r['missing_objects'] for r in output['frame_matches'])
        total_new = sum(r['new_objects'] for r in output['frame_matches'])
        
        print(f"\nSummary:")
        print(f"  Total matched objects: {total_matched}")
        print(f"  Total missing objects: {total_missing}")
        print(f"  Total new objects: {total_new}")


if __name__ == "__main__":
    main()
