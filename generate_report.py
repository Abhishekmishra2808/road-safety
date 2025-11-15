#!/usr/bin/env python3
"""
Generate evidence images, CSV reports, and PDF summaries.
Creates annotated side-by-side images and structured reports.
"""
import os
import sys
import json
import csv
import argparse
import numpy as np
import cv2
from datetime import datetime
from fpdf import FPDF


def draw_bbox(img, bbox, label, color, thickness=2):
    """
    Draw bounding box with label on image.
    
    Args:
        img: Image to draw on
        bbox: Bounding box [x1, y1, x2, y2]
        label: Text label
        color: BGR color tuple
        thickness: Line thickness
    """
    x1, y1, x2, y2 = [int(coord) for coord in bbox]
    
    # Draw rectangle
    cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)
    
    # Draw label background
    label_size, baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    y1_label = max(y1, label_size[1] + 10)
    cv2.rectangle(img, (x1, y1_label - label_size[1] - 10), 
                  (x1 + label_size[0], y1_label), color, -1)
    
    # Draw label text
    cv2.putText(img, label, (x1, y1_label - 5), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)


def create_side_by_side_image(base_img, present_img, matches, missing, new, 
                               overall_ssim, pair_id):
    """
    Create side-by-side annotated comparison image.
    
    Args:
        base_img: Base frame image
        present_img: Present frame image
        matches: List of matched detections
        missing: List of missing detections
        new: List of new detections
        overall_ssim: Overall SSIM score
        pair_id: Frame pair identifier
    
    Returns:
        Side-by-side annotated image
    """
    # Ensure same height
    h1, w1 = base_img.shape[:2]
    h2, w2 = present_img.shape[:2]
    
    if h1 != h2:
        scale = h1 / h2
        present_img = cv2.resize(present_img, (int(w2 * scale), h1))
        h2, w2 = present_img.shape[:2]
    
    # Create side-by-side canvas
    canvas = np.zeros((h1, w1 + w2 + 20, 3), dtype=np.uint8)
    canvas[:] = (50, 50, 50)  # Gray background
    
    # Copy images
    canvas[:h1, :w1] = base_img
    canvas[:h2, w1+20:w1+20+w2] = present_img
    
    # Add labels
    cv2.putText(canvas, "BASE", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(canvas, "PRESENT", (w1 + 30, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Add SSIM score
    ssim_text = f"SSIM: {overall_ssim:.3f}"
    cv2.putText(canvas, ssim_text, (10, h1 - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Color coding
    COLOR_UNCHANGED = (0, 255, 0)      # Green
    COLOR_MINOR = (0, 255, 255)         # Yellow
    COLOR_MODERATE = (0, 165, 255)      # Orange
    COLOR_SEVERE = (0, 0, 255)          # Red
    COLOR_MISSING = (255, 0, 255)       # Magenta
    COLOR_NEW = (255, 255, 0)           # Cyan
    
    # Draw matched objects
    for match in matches:
        severity = match.get('severity', 'UNKNOWN')
        
        if severity == 'UNCHANGED':
            color = COLOR_UNCHANGED
        elif severity == 'MINOR':
            color = COLOR_MINOR
        elif severity == 'MODERATE':
            color = COLOR_MODERATE
        elif severity == 'SEVERE':
            color = COLOR_SEVERE
        else:
            color = (128, 128, 128)
        
        # Draw on base
        label_base = f"{match.get('class_name', 'Object')}"
        draw_bbox(canvas[:h1, :w1], match['base_bbox'], label_base, color)
        
        # Draw on present with metrics
        label_present = f"{match.get('class_name', 'Object')} IoU:{match['iou']:.2f}"
        present_bbox = [match['present_bbox'][0] + w1 + 20,
                       match['present_bbox'][1],
                       match['present_bbox'][2] + w1 + 20,
                       match['present_bbox'][3]]
        draw_bbox(canvas[:h2, w1+20:], match['present_bbox'], label_present, color)
    
    # Draw missing objects (only in base)
    for miss in missing:
        label = f"{miss.get('class_name', 'Missing')} - MISSING"
        draw_bbox(canvas[:h1, :w1], miss['bbox'], label, COLOR_MISSING, 3)
    
    # Draw new objects (only in present)
    for new_obj in new:
        label = f"{new_obj.get('class_name', 'New')} - NEW"
        draw_bbox(canvas[:h2, w1+20:], new_obj['bbox'], label, COLOR_NEW, 3)
    
    # Add legend
    legend_y = 70
    legend_items = [
        ("Unchanged", COLOR_UNCHANGED),
        ("Minor", COLOR_MINOR),
        ("Moderate", COLOR_MODERATE),
        ("Severe", COLOR_SEVERE),
        ("Missing", COLOR_MISSING),
        ("New", COLOR_NEW)
    ]
    
    for i, (label, color) in enumerate(legend_items):
        y_pos = legend_y + i * 25
        cv2.rectangle(canvas, (10, y_pos - 15), (30, y_pos), color, -1)
        cv2.putText(canvas, label, (35, y_pos), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    return canvas


def generate_evidence_images(results, output_dir):
    """
    Generate evidence images for all frame pairs.
    
    Args:
        results: Analysis results from detect_and_compare.py
        output_dir: Directory to save evidence images
    
    Returns:
        List of generated image paths
    """
    evidence_dir = os.path.join(output_dir, "evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    
    evidence_paths = []
    
    print("\nGenerating evidence images...")
    
    for result in results:
        if result['flagged_changes'] == 0:
            continue  # Skip unchanged frames
        
        pair_id = result.get('pair_id', 0)
        
        # Load images
        base_img = cv2.imread(result['base_frame'])
        present_img = cv2.imread(result['present_frame'])
        
        if base_img is None or present_img is None:
            print(f"  [ERROR] Failed to load images for pair {pair_id}")
            continue
        
        # Create side-by-side image
        evidence_img = create_side_by_side_image(
            base_img.copy(),
            present_img.copy(),
            result['matched_objects'],
            result['missing_objects'],
            result['new_objects'],
            result['overall_ssim'],
            pair_id
        )
        
        # Save evidence image
        evidence_path = os.path.join(evidence_dir, f"evidence_{pair_id:03d}.jpg")
        cv2.imwrite(evidence_path, evidence_img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        evidence_paths.append(evidence_path)
        
        print(f"  [OK] Generated evidence_{pair_id:03d}.jpg")
    
    return evidence_paths


def generate_csv_report(results, output_file, gps_data=None):
    """
    Generate CSV report with all detected changes.
    
    Args:
        results: Analysis results
        output_file: Path to output CSV file
        gps_data: Optional GPS coordinates for each frame
    """
    print(f"\nGenerating CSV report: {output_file}")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'id', 'element_type', 'base_frame', 'present_frame',
            'gps_lat', 'gps_lon', 'severity', 'score',
            'iou', 'ssim', 'evidence_path', 'notes'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        change_id = 1
        
        for result in results:
            pair_id = result.get('pair_id', 0)
            base_frame = os.path.basename(result['base_frame'])
            present_frame = os.path.basename(result['present_frame'])
            evidence_path = f"evidence/evidence_{pair_id:03d}.jpg"
            
            # Get GPS if available
            gps_lat = gps_lon = ""
            if gps_data and pair_id in gps_data:
                gps_lat = gps_data[pair_id].get('lat', '')
                gps_lon = gps_data[pair_id].get('lon', '')
            
            # Write missing objects
            for miss in result['missing_objects']:
                writer.writerow({
                    'id': change_id,
                    'element_type': miss.get('class_name', 'Unknown'),
                    'base_frame': base_frame,
                    'present_frame': present_frame,
                    'gps_lat': gps_lat,
                    'gps_lon': gps_lon,
                    'severity': 'SEVERE',
                    'score': miss.get('severity_score', 1.0),
                    'iou': 0.0,
                    'ssim': 0.0,
                    'evidence_path': evidence_path,
                    'notes': 'Element missing in present frame'
                })
                change_id += 1
            
            # Write new objects
            for new_obj in result['new_objects']:
                writer.writerow({
                    'id': change_id,
                    'element_type': new_obj.get('class_name', 'Unknown'),
                    'base_frame': base_frame,
                    'present_frame': present_frame,
                    'gps_lat': gps_lat,
                    'gps_lon': gps_lon,
                    'severity': 'NEW',
                    'score': new_obj.get('severity_score', 0.9),
                    'iou': 0.0,
                    'ssim': 0.0,
                    'evidence_path': evidence_path,
                    'notes': 'New element detected in present frame'
                })
                change_id += 1
            
            # Write changed objects (moderate/severe only)
            for match in result['matched_objects']:
                severity = match.get('severity', 'UNKNOWN')
                
                if severity in ['MODERATE', 'SEVERE']:
                    writer.writerow({
                        'id': change_id,
                        'element_type': match.get('class_name', 'Unknown'),
                        'base_frame': base_frame,
                        'present_frame': present_frame,
                        'gps_lat': gps_lat,
                        'gps_lon': gps_lon,
                        'severity': severity,
                        'score': match.get('severity_score', 0.5),
                        'iou': match.get('iou', 0.0),
                        'ssim': match.get('region_ssim', 0.0),
                        'evidence_path': evidence_path,
                        'notes': f"Element changed (IoU:{match['iou']:.2f}, SSIM:{match.get('region_ssim', 0):.2f})"
                    })
                    change_id += 1
    
    print(f"  [OK] CSV report saved with {change_id - 1} changes")


def generate_pdf_summary(results, evidence_paths, output_file):
    """
    Generate PDF summary report.
    
    Args:
        results: Analysis results
        evidence_paths: List of evidence image paths
        output_file: Path to output PDF file
    """
    print(f"\nGenerating PDF summary: {output_file}")
    
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Title page
    pdf.add_page()
    pdf.set_font("Arial", 'B', 24)
    pdf.cell(0, 20, "Road Safety Analysis Report", ln=True, align='C')
    
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
    pdf.ln(10)
    
    # Summary statistics
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Summary Statistics", ln=True)
    pdf.ln(5)
    
    total_frames = len(results)
    total_flagged = sum(r['flagged_changes'] for r in results)
    total_missing = sum(len(r['missing_objects']) for r in results)
    total_new = sum(len(r['new_objects']) for r in results)
    
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, f"Total frames analyzed: {total_frames}", ln=True)
    pdf.cell(0, 8, f"Total flagged changes: {total_flagged}", ln=True)
    pdf.cell(0, 8, f"Missing elements: {total_missing}", ln=True)
    pdf.cell(0, 8, f"New elements: {total_new}", ln=True)
    pdf.ln(10)
    
    # Top issues
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Top Issues", ln=True)
    pdf.ln(5)
    
    # Sort results by number of flagged changes
    top_issues = sorted(results, key=lambda x: x['flagged_changes'], reverse=True)[:5]
    
    pdf.set_font("Arial", '', 11)
    for i, issue in enumerate(top_issues, 1):
        if issue['flagged_changes'] == 0:
            continue
        
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, f"{i}. Frame {issue.get('pair_id', 0)}", ln=True)
        
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 6, f"   - Flagged changes: {issue['flagged_changes']}", ln=True)
        pdf.cell(0, 6, f"   - SSIM: {issue['overall_ssim']:.3f}", ln=True)
        pdf.cell(0, 6, f"   - Missing: {len(issue['missing_objects'])}, New: {len(issue['new_objects'])}", ln=True)
        pdf.ln(3)
    
    # Add evidence images (one per page for top 5 issues)
    for evidence_path in evidence_paths[:5]:
        if not os.path.exists(evidence_path):
            continue
        
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, f"Evidence: {os.path.basename(evidence_path)}", ln=True)
        pdf.ln(5)
        
        try:
            # Add image (scale to fit page width)
            pdf.image(evidence_path, x=10, w=190)
        except Exception as e:
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 8, f"Error loading image: {e}", ln=True)
    
    # Save PDF
    try:
        pdf.output(output_file)
        print(f"  [OK] PDF summary saved")
    except Exception as e:
        print(f"  [ERROR] Error saving PDF: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate evidence images, CSV, and PDF reports"
    )
    parser.add_argument(
        "results_json",
        help="JSON file from detect_and_compare.py"
    )
    parser.add_argument(
        "output_dir",
        help="Directory to save reports"
    )
    parser.add_argument(
        "--gps-data",
        help="Optional JSON file with GPS coordinates"
    )
    
    args = parser.parse_args()
    
    # Load results
    print(f"Loading results from {args.results_json}")
    with open(args.results_json, 'r') as f:
        results = json.load(f)
    
    # Load GPS data if provided
    gps_data = None
    if args.gps_data and os.path.exists(args.gps_data):
        with open(args.gps_data, 'r') as f:
            gps_data = json.load(f)
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generate evidence images
    evidence_paths = generate_evidence_images(results, args.output_dir)
    
    # Generate CSV report
    csv_path = os.path.join(args.output_dir, "changes.csv")
    generate_csv_report(results, csv_path, gps_data)
    
    # Generate PDF summary
    pdf_path = os.path.join(args.output_dir, "summary.pdf")
    generate_pdf_summary(results, evidence_paths, pdf_path)
    
    print(f"\n{'='*60}")
    print("[SUCCESS] Report generation complete!")
    print(f"  Evidence images: {args.output_dir}/evidence/")
    print(f"  CSV report: {csv_path}")
    print(f"  PDF summary: {pdf_path}")


if __name__ == "__main__":
    main()
