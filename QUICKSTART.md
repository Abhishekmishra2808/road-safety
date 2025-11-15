# Quick Reference Guide

## 🚀 Getting Started (5 minutes)

### First Time Setup
```bash
# 1. Run setup script
setup.bat

# 2. Test installation
python test_installation.py

# 3. Launch web interface
streamlit run app.py
```

### Quick Analysis
```bash
python run_pipeline_quick.py base.mp4 present.mp4 output --max-pairs 5
```

---

## 📋 Command Cheat Sheet

### Frame Extraction
```bash
# Using Python script
python extract_frames.py video.mp4 output_dir --fps 1

# Using ffmpeg (faster)
ffmpeg -i video.mp4 -vf fps=1 output/frame_%05d.jpg
```

### Frame Alignment
```bash
# Basic alignment
python align_frames.py base_frames present_frames aligned

# With options
python align_frames.py base_frames present_frames aligned --method sift --max_pairs 20
```

### Detection
```bash
# Detect objects in image
python detect_elements.py image.jpg output --model yolov8n.pt

# Detect in directory
python detect_elements.py image_dir output --device 0
```

### Full Pipeline
```bash
# Minimal
python run_pipeline_quick.py base.mp4 present.mp4 out

# With all options
python run_pipeline_quick.py base.mp4 present.mp4 out \
  --fps 1 \
  --max-pairs 50 \
  --model yolov8s.pt \
  --device 0
```

### Web Interface
```bash
# Start server
streamlit run app.py

# On specific port
streamlit run app.py --server.port 8080

# Allow external connections
streamlit run app.py --server.address 0.0.0.0
```

---

## 🎯 Common Use Cases

### 1. Quick Test (2 minutes)
```bash
python run_pipeline_quick.py test_base.mp4 test_present.mp4 quick_test --max-pairs 5 --fps 0.5
```

### 2. Detailed Analysis (10-30 minutes)
```bash
python run_pipeline_quick.py base.mp4 present.mp4 detailed_out --fps 1 --model yolov8s.pt
```

### 3. Batch Processing
```bash
for i in 1 2 3 4 5; do
  python run_pipeline_quick.py \
    videos/base_${i}.mp4 \
    videos/present_${i}.mp4 \
    results/segment_${i}
done
```

### 4. High Quality Analysis
```bash
python run_pipeline_quick.py base.mp4 present.mp4 hq_output \
  --fps 2 \
  --model yolov8m.pt \
  --device 0
```

---

## ⚙️ Configuration Quick Reference

### Model Selection
| Model | Speed | Accuracy | Memory | Use Case |
|-------|-------|----------|--------|----------|
| yolov8n | ⚡⚡⚡ | ⭐⭐ | 2GB | Quick tests |
| yolov8s | ⚡⚡ | ⭐⭐⭐ | 3GB | **Recommended** |
| yolov8m | ⚡ | ⭐⭐⭐⭐ | 5GB | High accuracy |
| yolov8l | 🐌 | ⭐⭐⭐⭐⭐ | 8GB | Maximum quality |

### FPS Guidelines
- **0.5 FPS**: Very fast, minimal frames (testing)
- **1 FPS**: Balanced (recommended)
- **2 FPS**: Detailed analysis
- **5 FPS**: Maximum detail (slow)

### Device Options
- **0**: Use GPU (fast, recommended)
- **cpu**: Use CPU (slower, no GPU needed)

---

## 📊 Output Files

### Directory Structure
```
output/
├── base_frames/          # Extracted base frames
├── present_frames/       # Extracted present frames
├── aligned/              # Aligned frame pairs
└── results/              # Final outputs
    ├── evidence/         # Annotated images
    │   ├── evidence_001.jpg
    │   ├── evidence_002.jpg
    │   └── ...
    ├── changes.csv       # Detailed change log
    └── summary.pdf       # Executive summary
```

### CSV Columns
- `id`: Change ID
- `element_type`: Object class (sign, pole, etc.)
- `severity`: UNCHANGED/MINOR/MODERATE/SEVERE/NEW
- `score`: Severity score (0-1)
- `iou`: Intersection over Union
- `ssim`: Structural Similarity Index
- `evidence_path`: Path to annotated image

---

## 🔧 Troubleshooting

### Problem: Out of Memory
```bash
# Solution: Use smaller model and fewer pairs
python run_pipeline_quick.py base.mp4 present.mp4 out \
  --model yolov8n.pt \
  --max-pairs 10
```

### Problem: Slow Processing
```bash
# Solution: Reduce FPS and use GPU
python run_pipeline_quick.py base.mp4 present.mp4 out \
  --fps 0.5 \
  --device 0
```

### Problem: Poor Alignment
```bash
# Solution: Try SIFT instead of ORB
# Edit align_frames.py or run separately:
python align_frames.py base_frames present_frames aligned --method sift
```

### Problem: No Detections
```bash
# Solution: Lower confidence threshold
# Edit detect_elements.py line with conf=0.25 to conf=0.15
```

---

## 💡 Tips & Tricks

### 1. Faster Frame Extraction
Install ffmpeg for 3-5x faster extraction:
```bash
# Windows (with chocolatey)
choco install ffmpeg

# Check installation
ffmpeg -version
```

### 2. GPU Memory Management
```python
# In detect_elements.py, add after imports:
import torch
torch.cuda.empty_cache()
```

### 3. Process Subset of Video
```bash
# Extract only first 100 seconds
ffmpeg -i input.mp4 -t 100 -c copy subset.mp4
```

### 4. Custom Severity Thresholds
Edit `detect_and_compare.py`:
```python
def determine_severity(iou, ssim_score, is_missing=False, is_new=False):
    # Customize these thresholds
    if ssim_score > 0.95:  # More strict
        return "UNCHANGED", 0.0
    # ... etc
```

### 5. Filter Results by Severity
```bash
# In Python, after loading CSV
import pandas as pd
df = pd.read_csv('results/changes.csv')
severe_only = df[df['severity'].isin(['SEVERE', 'MODERATE'])]
severe_only.to_csv('severe_changes.csv', index=False)
```

---

## 🔍 Performance Benchmarks

### RTX 2050 (4GB VRAM)
| Config | FPS | Time (50 frames) |
|--------|-----|------------------|
| yolov8n + GPU | ~8 | 6 min |
| yolov8s + GPU | ~5 | 10 min |
| yolov8n + CPU | ~2 | 25 min |

### RTX 3060 (12GB VRAM)
| Config | FPS | Time (50 frames) |
|--------|-----|------------------|
| yolov8n + GPU | ~15 | 3 min |
| yolov8s + GPU | ~10 | 5 min |
| yolov8m + GPU | ~6 | 8 min |

---

## 📞 Getting Help

1. Check `README.md` for detailed documentation
2. Run `python test_installation.py` to verify setup
3. Check output logs for error messages
4. Ensure videos cover the same route/area

---

## 🎓 Example Workflow

```bash
# 1. Setup (first time only)
setup.bat

# 2. Quick test with sample videos
python run_pipeline_quick.py sample_base.mp4 sample_present.mp4 test --max-pairs 5

# 3. Review results
cd test/results
dir evidence
type changes.csv

# 4. Full analysis if satisfied
python run_pipeline_quick.py road_base.mp4 road_present.mp4 full_analysis --fps 1 --model yolov8s.pt

# 5. View in web interface
streamlit run app.py
# Upload videos and click "Run Analysis"
```

---

**Need more help? Check README.md for comprehensive documentation!**
