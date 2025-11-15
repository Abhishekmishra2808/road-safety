#!/usr/bin/env python3
"""
Test script to verify installation and GPU availability.
"""
import sys
import importlib


def check_import(module_name, display_name=None):
    """Check if a module can be imported."""
    if display_name is None:
        display_name = module_name
    
    try:
        mod = importlib.import_module(module_name)
        version = getattr(mod, '__version__', 'unknown')
        print(f"✓ {display_name}: {version}")
        return True
    except ImportError as e:
        print(f"✗ {display_name}: NOT INSTALLED ({e})")
        return False


def check_gpu():
    """Check GPU availability."""
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        
        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"✓ GPU: {gpu_name}")
            print(f"  Memory: {gpu_memory:.2f} GB")
            print(f"  CUDA Version: {torch.version.cuda}")
            return True
        else:
            print("✗ GPU: CUDA not available")
            print("  Will use CPU (slower performance)")
            return False
    except ImportError:
        print("✗ GPU: Cannot check (PyTorch not installed)")
        return False


def check_opencv_extras():
    """Check OpenCV optional features."""
    try:
        import cv2
        
        # Check for SIFT
        try:
            sift = cv2.SIFT_create()
            print("✓ OpenCV SIFT: Available")
        except:
            print("✗ OpenCV SIFT: Not available (use ORB instead)")
        
        # Check for CUDA support
        cuda_enabled = cv2.cuda.getCudaEnabledDeviceCount() > 0
        if cuda_enabled:
            print("✓ OpenCV CUDA: Enabled")
        else:
            print("  OpenCV CUDA: Not enabled (optional)")
        
        return True
    except ImportError:
        return False


def check_ffmpeg():
    """Check if ffmpeg is available."""
    import subprocess
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✓ FFmpeg: {version_line}")
            return True
        else:
            print("✗ FFmpeg: Not working properly")
            return False
    except FileNotFoundError:
        print("✗ FFmpeg: Not found (will use OpenCV fallback)")
        return False
    except subprocess.TimeoutExpired:
        print("✗ FFmpeg: Timeout")
        return False


def main():
    print("="*60)
    print("Road Safety Analysis System - Installation Check")
    print("="*60)
    
    print(f"\nPython Version: {sys.version}")
    print(f"Python Executable: {sys.executable}")
    
    print("\n" + "="*60)
    print("Checking Required Packages")
    print("="*60)
    
    required_packages = [
        ('cv2', 'OpenCV'),
        ('numpy', 'NumPy'),
        ('torch', 'PyTorch'),
        ('torchvision', 'TorchVision'),
        ('ultralytics', 'Ultralytics'),
        ('skimage', 'scikit-image'),
        ('PIL', 'Pillow'),
        ('pandas', 'Pandas'),
        ('streamlit', 'Streamlit'),
        ('fpdf', 'FPDF')
    ]
    
    all_installed = True
    for module, display in required_packages:
        if not check_import(module, display):
            all_installed = False
    
    print("\n" + "="*60)
    print("Checking GPU & Hardware Acceleration")
    print("="*60)
    gpu_available = check_gpu()
    
    print("\n" + "="*60)
    print("Checking Optional Features")
    print("="*60)
    check_opencv_extras()
    ffmpeg_available = check_ffmpeg()
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    if all_installed:
        print("✓ All required packages are installed")
    else:
        print("✗ Some packages are missing - install with:")
        print("  pip install -r requirements.txt")
    
    if gpu_available:
        print("✓ GPU acceleration available (recommended)")
    else:
        print("⚠ GPU not available - will use CPU (slower)")
    
    if ffmpeg_available:
        print("✓ FFmpeg available (faster frame extraction)")
    else:
        print("⚠ FFmpeg not found - will use OpenCV (slower)")
    
    print("\n" + "="*60)
    print("Quick Start Commands")
    print("="*60)
    print("\n1. Run Web Interface:")
    print("   streamlit run app.py")
    print("\n2. Run Pipeline:")
    print("   python run_pipeline_quick.py base.mp4 present.mp4 output")
    print("\n3. Test with Sample:")
    print("   # Place base.mp4 and present.mp4 in current directory, then:")
    print("   python run_pipeline_quick.py base.mp4 present.mp4 test_output --max-pairs 5")
    
    print("\n" + "="*60)
    
    if all_installed and gpu_available:
        print("✅ System ready for analysis!")
        return 0
    elif all_installed:
        print("⚠️  System ready but GPU not available (will be slower)")
        return 0
    else:
        print("❌ Please install missing packages first")
        return 1


if __name__ == "__main__":
    sys.exit(main())
