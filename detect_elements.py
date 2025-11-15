#!/usr/bin/env python3
"""
Detect road elements using YOLOv8 with GPU acceleration.
Detects objects like signs, poles, vehicles, and road markings.
"""
import os
import sys
import json
import argparse
import numpy as np
import cv2
from pathlib import Path
from ultralytics import YOLO


def detect_objects_yolo(image_path, model, device=0, imgsz=640, conf_thresh=0.25):
    """
    Detect objects in an image using YOLOv8.
    
    Args:
        image_path: Path to input image
        model: YOLO model instance
        device: Device to use (0 for GPU, 'cpu' for CPU)
        imgsz: Input image size
        conf_thresh: Confidence threshold
    
    Returns:
        List of detection dictionaries
    """
    # Ensure model is on correct device
    if device != 'cpu' and device != model.device:
        model.to(device)
    
    # Run inference
    use_half = (device != 'cpu')  # Use FP16 only on GPU
    results = model.predict(
        source=image_path,
        device=device,
        imgsz=imgsz,
        conf=conf_thresh,
        half=use_half,  # Use FP16 for faster inference on GPU
        verbose=False
    )
    
    detections = []
    
    # Parse results
    for result in results:
        boxes = result.boxes
        
        for i in range(len(boxes)):
            box = boxes[i]
            
            # Extract box coordinates
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            class_name = model.names[cls]
            
            detection = {
                "bbox": [float(x1), float(y1), float(x2), float(y2)],
                "confidence": conf,
                "class_id": cls,
                "class_name": class_name,
                "center": [float((x1 + x2) / 2), float((y1 + y2) / 2)],
                "area": float((x2 - x1) * (y2 - y1))
            }
            
            detections.append(detection)
    
    return detections


def detect_road_markings(image_path, method='edge'):
    """
    Detect road markings using CV heuristics.
    
    Args:
        image_path: Path to input image
        method: Detection method ('edge' or 'color')
    
    Returns:
        Binary mask of detected markings and contours
    """
    img = cv2.imread(image_path)
    if img is None:
        return None, []
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    if method == 'edge':
        # Edge detection for markings
        edges = cv2.Canny(gray, 50, 150)
        
        # Morphological operations to connect edges
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    
    else:  # color-based
        # HSV color thresholding for white/yellow markings
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # White markings
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 30, 255])
        white_mask = cv2.inRange(hsv, lower_white, upper_white)
        
        # Yellow markings
        lower_yellow = np.array([20, 100, 100])
        upper_yellow = np.array([30, 255, 255])
        yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        
        # Combine masks
        mask = cv2.bitwise_or(white_mask, yellow_mask)
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours by area
    min_area = 100
    filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
    
    return mask, filtered_contours


def detect_potholes(image_path, sensitivity='medium'):
    """
    Detect potential potholes using texture and edge analysis.
    
    Args:
        image_path: Path to input image
        sensitivity: Detection sensitivity ('low', 'medium', 'high')
    
    Returns:
        Binary mask and list of pothole regions
    """
    img = cv2.imread(image_path)
    if img is None:
        return None, []
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Edge detection
    edges = cv2.Canny(blurred, 30, 100)
    
    # Morphological closing to fill gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    # Find contours
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours by circularity and area
    potholes = []
    thresholds = {
        'low': (500, 0.3),
        'medium': (300, 0.4),
        'high': (150, 0.5)
    }
    min_area, min_circularity = thresholds.get(sensitivity, thresholds['medium'])
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        
        perimeter = cv2.arcLength(cnt, True)
        if perimeter == 0:
            continue
        
        circularity = 4 * np.pi * area / (perimeter ** 2)
        
        if circularity > min_circularity:
            x, y, w, h = cv2.boundingRect(cnt)
            potholes.append({
                "bbox": [int(x), int(y), int(x+w), int(y+h)],
                "area": float(area),
                "circularity": float(circularity),
                "center": [int(x + w/2), int(y + h/2)]
            })
    
    # Create mask
    mask = np.zeros(gray.shape, dtype=np.uint8)
    for pothole in potholes:
        x1, y1, x2, y2 = pothole["bbox"]
        cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
    
    return mask, potholes


def process_image(image_path, model, device=0, detect_markings=True, detect_potholes_flag=True):
    """
    Process a single image with all detection methods.
    
    Args:
        image_path: Path to input image
        model: YOLO model
        device: Device for inference
        detect_markings: Whether to detect road markings
        detect_potholes_flag: Whether to detect potholes
    
    Returns:
        Dictionary containing all detections
    """
    results = {
        "image_path": image_path,
        "objects": [],
        "markings": [],
        "potholes": []
    }
    
    # YOLO object detection
    print(f"  Detecting objects with YOLO...")
    results["objects"] = detect_objects_yolo(image_path, model, device)
    print(f"    Found {len(results['objects'])} objects")
    
    # Road markings detection
    if detect_markings:
        print(f"  Detecting road markings...")
        mask, contours = detect_road_markings(image_path)
        if mask is not None:
            results["markings"] = [
                {
                    "contour_id": i,
                    "area": float(cv2.contourArea(cnt)),
                    "center": [float(x) for x in cv2.moments(cnt)] if cv2.contourArea(cnt) > 0 else [0, 0]
                }
                for i, cnt in enumerate(contours)
            ]
            print(f"    Found {len(contours)} marking regions")
    
    # Pothole detection
    if detect_potholes_flag:
        print(f"  Detecting potholes...")
        mask, potholes = detect_potholes(image_path)
        if mask is not None:
            results["potholes"] = potholes
            print(f"    Found {len(potholes)} potential potholes")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Detect road elements using YOLOv8 and CV methods"
    )
    parser.add_argument(
        "image_path",
        help="Path to input image or directory of images"
    )
    parser.add_argument(
        "output_dir",
        help="Directory to save detection results"
    )
    parser.add_argument(
        "--model",
        default="yolov8n.pt",
        help="YOLOv8 model to use (default: yolov8n.pt)"
    )
    parser.add_argument(
        "--device",
        default="0",
        help="Device to use (0 for GPU, cpu for CPU)"
    )
    parser.add_argument(
        "--no-markings",
        action="store_true",
        help="Skip road markings detection"
    )
    parser.add_argument(
        "--no-potholes",
        action="store_true",
        help="Skip pothole detection"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load YOLO model
    print(f"Loading YOLO model: {args.model}")
    try:
        model = YOLO(args.model)
        device = 0 if args.device != 'cpu' and args.device.isdigit() else 'cpu'
        print(f"✓ Model loaded, using device: {device}")
    except Exception as e:
        print(f"✗ Error loading model: {e}")
        sys.exit(1)
    
    # Process image(s)
    if os.path.isdir(args.image_path):
        # Process directory
        images = [os.path.join(args.image_path, f) 
                 for f in os.listdir(args.image_path) 
                 if f.endswith(('.jpg', '.png', '.jpeg'))]
        print(f"\nProcessing {len(images)} images...")
    else:
        # Single image
        images = [args.image_path]
        print(f"\nProcessing single image...")
    
    all_results = []
    
    for img_path in images:
        print(f"\nProcessing: {os.path.basename(img_path)}")
        result = process_image(
            img_path, 
            model, 
            device,
            not args.no_markings,
            not args.no_potholes
        )
        all_results.append(result)
    
    # Save results
    output_file = os.path.join(args.output_dir, "detections.json")
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n✓ Detection complete! Results saved to {output_file}")


if __name__ == "__main__":
    main()
