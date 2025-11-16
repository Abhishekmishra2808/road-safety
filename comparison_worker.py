import os
import cv2
import time
import numpy as np
from collections import defaultdict
import torch
from ultralytics import YOLO
from detection_worker import load_model_for_worker, detect_potholes_simple, detect_road_markings_simple


def draw_changes(frame, changes, change_type):
    """Draw detected changes on frame"""
    annotated = frame.copy()
    for change in changes:
        x1, y1, x2, y2 = [int(v) for v in change['bbox']]
        label = change.get('class', 'change')
        
        # Color code based on change type
        if change_type == 'added':
            color = (0, 255, 0)  # Green for new elements
            prefix = "NEW: "
        elif change_type == 'removed':
            color = (0, 0, 255)  # Red for removed elements
            prefix = "REMOVED: "
        else:
            color = (255, 165, 0)  # Orange for modified
            prefix = "CHANGED: "
        
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
        label_text = f"{prefix}{label}"
        label_size, _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(annotated, (x1, y1 - label_size[1] - 10), (x1 + label_size[0], y1), color, -1)
        cv2.putText(annotated, label_text, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    return annotated


def detect_objects_in_frame(frame, model, device):
    """Detect all objects in a frame"""
    detections = []
    
    # YOLO detection
    try:
        results = model(frame, conf=0.3, device=device, verbose=False)
        for result in results:
            boxes = getattr(result, 'boxes', [])
            for box in boxes:
                cls = int(box.cls[0]) if hasattr(box, 'cls') else 0
                conf = float(box.conf[0]) if hasattr(box, 'conf') else 0.0
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy() if hasattr(box, 'xyxy') else [0,0,0,0]
                name = result.names.get(cls, str(cls))
                
                # Map class names and filter out vehicles/boats
                if name in ['car', 'truck', 'bus', 'motorcycle', 'bicycle', 'boat', 'person']:
                    continue  # Skip vehicle and person detection
                elif name in ['traffic light', 'stop sign']:
                    name = 'traffic_sign'
                
                detections.append({
                    'bbox': [x1, y1, x2, y2],
                    'confidence': conf,
                    'class': name,
                    'center': [(x1+x2)/2, (y1+y2)/2],
                    'area': (x2-x1)*(y2-y1)
                })
    except Exception as e:
        print(f"YOLO detection error: {e}")
    
    # Add pothole detection
    for pothole in detect_potholes_simple(frame):
        x1, y1, x2, y2 = pothole['bbox']
        detections.append({
            **pothole,
            'center': [(x1+x2)/2, (y1+y2)/2],
            'area': (x2-x1)*(y2-y1)
        })
    
    # Add road marking detection
    for marking in detect_road_markings_simple(frame):
        x1, y1, x2, y2 = marking['bbox']
        detections.append({
            **marking,
            'center': [(x1+x2)/2, (y1+y2)/2],
            'area': (x2-x1)*(y2-y1)
        })
    
    return detections


def compare_detections(base_dets, present_dets, threshold=50):
    """Compare two sets of detections and find changes"""
    added = []
    removed = []
    
    # Find added objects (in present but not in base)
    for present_det in present_dets:
        matched = False
        for base_det in base_dets:
            # Check if objects are similar (same class, close location)
            if present_det['class'] == base_det['class']:
                dist = np.sqrt(
                    (present_det['center'][0] - base_det['center'][0])**2 +
                    (present_det['center'][1] - base_det['center'][1])**2
                )
                if dist < threshold:
                    matched = True
                    break
        
        if not matched:
            added.append(present_det)
    
    # Find removed objects (in base but not in present)
    for base_det in base_dets:
        matched = False
        for present_det in present_dets:
            if base_det['class'] == present_det['class']:
                dist = np.sqrt(
                    (base_det['center'][0] - present_det['center'][0])**2 +
                    (base_det['center'][1] - present_det['center'][1])**2
                )
                if dist < threshold:
                    matched = True
                    break
        
        if not matched:
            removed.append(base_det)
    
    return added, removed


class ComparisonWorker:
    def __init__(self, job_id, base_video_path, present_video_path, output_dir, model_path='yolov8n.pt'):
        self.job_id = job_id
        self.base_video_path = base_video_path
        self.present_video_path = present_video_path
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.model_path = model_path
        self.status = {
            'job_id': job_id,
            'progress': 0.0,
            'total_frames': 0,
            'processed_frames': 0,
            'changes': {},
            'completed': False,
            'error': None
        }
        self.latest_frame_path = os.path.join(self.output_dir, 'latest.jpg')
        self.results_path = os.path.join(self.output_dir, 'results.json')

    def run(self):
        try:
            model, device = load_model_for_worker(self.model_path)
        except Exception as e:
            self.status['error'] = str(e)
            self.status['completed'] = True
            return

        # Open both videos
        base_cap = cv2.VideoCapture(self.base_video_path)
        present_cap = cv2.VideoCapture(self.present_video_path)
        
        if not base_cap.isOpened() or not present_cap.isOpened():
            self.status['error'] = 'Failed to open video files'
            self.status['completed'] = True
            return

        # Get video properties
        base_frames = int(base_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        present_frames = int(present_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        total_frames = min(base_frames, present_frames)
        self.status['total_frames'] = total_frames
        
        fps = base_cap.get(cv2.CAP_PROP_FPS) or 25
        skip_frames = max(1, int(fps / 2))  # Process 2 frames per second
        
        all_changes = defaultdict(int)
        frame_count = 0
        comparison_frames = []

        while base_cap.isOpened() and present_cap.isOpened():
            base_ret, base_frame = base_cap.read()
            present_ret, present_frame = present_cap.read()
            
            if not base_ret or not present_ret:
                break
            
            frame_count += 1
            
            if frame_count % skip_frames != 0:
                continue
            
            # Detect objects in both frames
            base_detections = detect_objects_in_frame(base_frame, model, device)
            present_detections = detect_objects_in_frame(present_frame, model, device)
            
            # Compare and find changes
            added, removed = compare_detections(base_detections, present_detections)
            
            # Count changes by type
            for obj in added:
                change_key = f"added_{obj['class']}"
                all_changes[change_key] += 1
            
            for obj in removed:
                change_key = f"removed_{obj['class']}"
                all_changes[change_key] += 1
            
            # Draw changes on present frame
            annotated = present_frame.copy()
            if added:
                annotated = draw_changes(annotated, added, 'added')
            if removed:
                annotated = draw_changes(annotated, removed, 'removed')
            
            # Save latest frame
            cv2.imwrite(self.latest_frame_path, annotated)
            
            comparison_frames.append({
                'frame_num': frame_count,
                'added_count': len(added),
                'removed_count': len(removed)
            })
            
            # Update status
            self.status['processed_frames'] = len(comparison_frames)
            self.status['changes'] = dict(all_changes)
            self.status['progress'] = min(1.0, frame_count / max(1, total_frames))
            
            time.sleep(0.01)

        base_cap.release()
        present_cap.release()
        
        # Save final results
        final = {
            'total_frames': total_frames,
            'processed_frames': len(comparison_frames),
            'changes': dict(all_changes),
            'comparison_frames': comparison_frames
        }
        
        try:
            import json
            with open(self.results_path, 'w') as f:
                json.dump(final, f, indent=2)
        except Exception:
            pass
        
        self.status.update(final)
        self.status['completed'] = True
        self.status['progress'] = 1.0
