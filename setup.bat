@echo off
REM Setup script for Road Safety Analysis System
REM Installs all dependencies including CUDA-enabled PyTorch

echo ========================================
echo Road Safety Analysis System - Setup
echo ========================================
echo.

REM Check Python version
python --version
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.10 or higher from https://www.python.org/
    pause
    exit /b 1
)

echo.
echo Step 1: Creating virtual environment...
if exist ".venv" (
    echo Virtual environment already exists.
    set /p recreate="Recreate it? (y/n): "
    if /i "%recreate%"=="y" (
        echo Removing old environment...
        rmdir /s /q .venv
    )
)

if not exist ".venv" (
    python -m venv .venv
    echo ✓ Virtual environment created
)

echo.
echo Step 2: Activating virtual environment...
call .venv\Scripts\activate.bat

echo.
echo Step 3: Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Step 4: Checking for CUDA/GPU...
echo.
set /p has_gpu="Do you have an NVIDIA GPU? (y/n): "

if /i "%has_gpu%"=="y" (
    echo.
    echo Installing CUDA-enabled PyTorch...
    echo This will download ~2GB of files...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
) else (
    echo.
    echo Installing CPU-only PyTorch...
    pip install torch torchvision torchaudio
)

echo.
echo Step 5: Installing other dependencies...
pip install opencv-python opencv-contrib-python
pip install ultralytics
pip install scikit-image
pip install fpdf
pip install streamlit
pip install numpy pandas pillow
pip install ffmpeg-python

echo.
echo Step 6: Testing installation...
python test_installation.py

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo.
echo 1. To launch the web interface:
echo    run.bat web
echo.
echo 2. To test the installation:
echo    run.bat test
echo.
echo 3. To run a quick analysis:
echo    python run_pipeline_quick.py base.mp4 present.mp4 output --max-pairs 5
echo.
pause
