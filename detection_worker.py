import os
import cv2
import time
import uuid
import numpy as np
from collections import defaultdict
import torch
from ultralytics import YOLO


def load_model_for_worker(model_path='yolov8n.pt'):
    device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")
    model = YOLO(model_path)
    model.to(device)
    return model, device


def detect_potholes_simple(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    edges = cv2.Canny(blurred, 50, 150)
    kernel = np.ones((5, 5), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=2)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    potholes = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if 500 < area < 5000:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = float(w) / h if h > 0 else 0
            if 0.5 < aspect_ratio < 3.0:
                potholes.append({'bbox': [x, y, x+w, y+h], 'confidence': min(0.5 + (area / 10000), 0.95), 'class': 'pothole'})
    return potholes


def detect_road_markings_simple(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    kernel = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    markings = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if 100 < area < 3000:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = float(w) / h if h > 0 else 0
            if aspect_ratio > 1.5:
                markings.append({'bbox': [x, y, x+w, y+h], 'confidence': 0.7, 'class': 'road_marking'})
    return markings


def draw_detections(frame, detections):
    annotated = frame.copy()
    for det in detections:
        x1, y1, x2, y2 = [int(v) for v in det['bbox']]
        conf = det.get('confidence', 0)
        label = det.get('class', 'obj')
        # choose green for detections, red for potholes
        if 'pothole' in label.lower():
            color = (0, 0, 255)
        elif 'marking' in label.lower():
            color = (255, 255, 255)
        else:
            color = (0, 255, 0)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        label_text = f"{label} {conf:.2f}"
        label_size, _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(annotated, (x1, y1 - label_size[1] - 6), (x1 + label_size[0], y1), color, -1)
        cv2.putText(annotated, label_text, (x1, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    return annotated


class VideoWorker:
    def __init__(self, job_id, video_path, output_dir, model_path='yolov8n.pt'):
        self.job_id = job_id
        self.video_path = video_path
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.model_path = model_path
        self.status = {
            'job_id': job_id,
            'progress': 0.0,
            'total_frames': 0,
            'processed_frames': 0,
            'detections': {},
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

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self.status['error'] = 'Failed to open video file'
            self.status['completed'] = True
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        self.status['total_frames'] = total_frames
        skip_frames = max(1, int(fps / 2))

        all_detections = defaultdict(int)
        detected_frames = []
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame_count += 1
            if frame_count % skip_frames != 0:
                continue
            detections = []
            # YOLO detection
            try:
                results = model(frame, conf=0.3)
                for result in results:
                    boxes = getattr(result, 'boxes', [])
                    for box in boxes:
                        cls = int(box.cls[0]) if hasattr(box, 'cls') else 0
                        conf = float(box.conf[0]) if hasattr(box, 'conf') else 0.0
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy() if hasattr(box, 'xyxy') else [0,0,0,0]
                        name = result.names.get(cls, str(cls))
                        # Filter out vehicles, boats, and persons - only track infrastructure
                        if name in ['car', 'truck', 'bus', 'motorcycle', 'bicycle', 'boat', 'person']:
                            continue  # Skip vehicle and person detection
                        # map some names
                        if name in ['traffic light', 'stop sign']:
                            name = 'traffic_sign'
                        detections.append({'bbox':[x1,y1,x2,y2], 'confidence': conf, 'class': name})
                        all_detections[name] += 1
            except Exception:
                pass
            # potholes & markings
            for p in detect_potholes_simple(frame):
                detections.append(p); all_detections['pothole'] += 1
            for m in detect_road_markings_simple(frame):
                detections.append(m); all_detections['road_marking'] += 1
            # draw and save latest
            annotated = draw_detections(frame, detections) if detections else frame
            cv2.imwrite(self.latest_frame_path, annotated)
            detected_frames.append({'frame_num': frame_count, 'detections': len(detections)})
            self.status['processed_frames'] = len(detected_frames)
            self.status['detections'] = dict(all_detections)
            self.status['progress'] = min(1.0, frame_count / max(1, total_frames))
            # small sleep to yield
            time.sleep(0.01)

        cap.release()
        # write results
        final = {
            'total_frames': total_frames,
            'processed_frames': len(detected_frames),
            'detections': dict(all_detections),
            'detected_frames': detected_frames
        }
        try:
            import json
            with open(self.results_path, 'w') as f:
                json.dump(final, f)
        except Exception:
            pass
        self.status.update(final)
        self.status['completed'] = True
        self.status['progress'] = 1.0
