# Troubleshooting Guide

## Issue: Streamlit Not Running

### Problem
When running `streamlit run app.py`, you get an error.

### Solution

**Method 1: Use the full path to Python (Recommended)**
```bash
.venv\Scripts\python.exe -m streamlit run app.py
```

**Method 2: Activate environment first (CMD)**
```bash
.venv\Scripts\activate.bat
streamlit run app.py
```

**Method 3: Activate environment first (PowerShell)**
```powershell
.venv\Scripts\Activate.ps1
streamlit run app.py
```

**Method 4: Use the batch file**
```bash
run.bat
# Then select option 1
```

---

## Issue: Unicode/Encoding Errors (FIXED)

### Problem
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2717'
```

### Solution
✅ **Already fixed!** All scripts now use ASCII-safe characters:
- `✓` → `[OK]`
- `✗` → `[ERROR]`
- Unicode symbols replaced with `[SUCCESS]`, `[INFO]`, `[WARNING]`

---

## Issue: Video Cannot Be Opened

### Problem
Pipeline fails at frame extraction with OpenCV error.

### Diagnosis
Run the video test script:
```bash
python test_video.py your_video.mp4
```

This will tell you:
- If the file exists
- If OpenCV can open it
- Video properties (resolution, FPS, duration)
- If frames can be read

### Common Causes & Solutions

#### 1. Unsupported Video Codec
**Symptoms:** OpenCV cannot open the video
**Solution:** Convert to H.264/AAC:
```bash
# If you have ffmpeg:
ffmpeg -i input.mp4 -c:v libx264 -c:a aac -strict experimental output.mp4

# Then use output.mp4 for analysis
```

#### 2. Corrupted Video File
**Symptoms:** File exists but cannot be read
**Solution:** Re-encode the video:
```bash
ffmpeg -i corrupted.mp4 -c copy fixed.mp4
```

#### 3. File Path Issues
**Symptoms:** File not found error
**Solution:** Use absolute paths or check file location:
```bash
python test_video.py "C:\full\path\to\video.mp4"
```

---

## Quick Test Workflow

### 1. Test Installation
```bash
python test_installation.py
```
Should show all packages installed.

### 2. Create Sample Data
```bash
python create_sample_data.py --num-frames 5
```
Creates synthetic test frames.

### 3. Test with Sample Data
```bash
python run_pipeline_quick.py sample_data/base_frames sample_data/present_frames test_output --max-pairs 5
```

### 4. If Successful, Test with Real Videos
```bash
# First, test videos
python test_video.py base.mp4 present.mp4

# If OK, run pipeline
python run_pipeline_quick.py base.mp4 present.mp4 output --max-pairs 5
```

---

## Streamlit Launch Commands (All Methods)

### Windows CMD
```bash
# Activate environment
.venv\Scripts\activate.bat

# Run Streamlit
streamlit run app.py
```

### Windows PowerShell
```powershell
# Activate environment
.venv\Scripts\Activate.ps1

# Run Streamlit
streamlit run app.py
```

### Direct Python (No Activation Needed)
```bash
.venv\Scripts\python.exe -m streamlit run app.py
```

### Using Batch File (Easiest)
```bash
run.bat
```
Then choose option 1.

---

## Port Already in Use

If you get "Address already in use" error:

### Solution 1: Kill existing Streamlit
```bash
# Find process
netstat -ano | findstr :8501

# Kill process (replace PID with actual number)
taskkill /PID <PID> /F
```

### Solution 2: Use different port
```bash
streamlit run app.py --server.port 8502
```

---

## Common Pipeline Errors

### Error: "No frames extracted"
**Cause:** Video file issue or OpenCV can't decode
**Fix:** 
```bash
python test_video.py your_video.mp4
```

### Error: "Homography estimation failed"
**Cause:** Videos too different or insufficient features
**Fix:** 
- Ensure videos show same area
- Try SIFT instead of ORB: Edit align_frames.py or run manually
- Reduce quality requirements

### Error: "Out of memory"
**Cause:** Model too large or too many frames
**Fix:**
```bash
python run_pipeline_quick.py base.mp4 present.mp4 output --model yolov8n.pt --max-pairs 10
```

### Error: Module not found
**Cause:** Package not installed
**Fix:**
```bash
.venv\Scripts\pip.exe install <missing_package>
```

---

## Environment Activation Issues

### PowerShell Execution Policy Error
```
cannot be loaded because running scripts is disabled
```

**Fix:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Wrong Python Version
```bash
# Check Python version
python --version

# Should be 3.10+
# If not, specify full path:
C:\Python311\python.exe -m venv .venv
```

---

## Quick Commands Reference

```bash
# Test installation
python test_installation.py

# Test video files
python test_video.py base.mp4 present.mp4

# Create sample data
python create_sample_data.py --num-frames 10

# Run web interface (3 ways)
run.bat                                           # Easiest
.venv\Scripts\python.exe -m streamlit run app.py # Direct
streamlit run app.py                              # If activated

# Run pipeline
python run_pipeline_quick.py base.mp4 present.mp4 output --max-pairs 5

# Quick test with sample data
python run_pipeline_quick.py sample_data/base_frames sample_data/present_frames test --max-pairs 5
```

---

## Getting More Help

1. **Check video first:** `python test_video.py your_video.mp4`
2. **Check installation:** `python test_installation.py`
3. **Check terminal output** for specific error messages
4. **Try sample data first** before real videos
5. **Use smaller test** (`--max-pairs 5`) to debug faster

---

## Success Checklist

Before running full analysis:
- [ ] `python test_installation.py` shows all OK
- [ ] `python test_video.py base.mp4 present.mp4` shows both OK
- [ ] Quick test works: `--max-pairs 5`
- [ ] Streamlit launches (any method above)
- [ ] You have enough disk space (1GB+ free)

---

**All fixed! Try running again with the corrected scripts.**
