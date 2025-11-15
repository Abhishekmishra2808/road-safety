@echo off
REM Road Safety Analysis System - Quick Start Script for Windows
REM This script helps you run the analysis easily

echo ========================================
echo Road Safety Analysis System
echo ========================================
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo Virtual environment not found!
    echo Please run setup first:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Check command line arguments
if "%1"=="" goto menu
if "%1"=="web" goto web
if "%1"=="test" goto test
if "%1"=="pipeline" goto pipeline

:menu
echo Choose an option:
echo.
echo 1. Launch Web Interface
echo 2. Test Installation
echo 3. Run Pipeline (manual)
echo 4. Exit
echo.
set /p choice="Enter choice (1-4): "

if "%choice%"=="1" goto web
if "%choice%"=="2" goto test
if "%choice%"=="3" goto pipeline
if "%choice%"=="4" goto end

echo Invalid choice!
goto menu

:web
echo.
echo ========================================
echo Starting Web Interface...
echo ========================================
echo Open your browser to: http://localhost:8501
echo Press Ctrl+C to stop
echo.
streamlit run app.py
goto end

:test
echo.
echo ========================================
echo Testing Installation...
echo ========================================
python test_installation.py
pause
goto end

:pipeline
echo.
echo ========================================
echo Running Analysis Pipeline
echo ========================================
echo.
set /p base="Enter base video path: "
set /p present="Enter present video path: "
set /p output="Enter output directory: "
echo.
echo Starting analysis...
python run_pipeline_quick.py "%base%" "%present%" "%output%" --fps 1 --max-pairs 20
echo.
echo Analysis complete!
pause
goto end

:end
echo.
echo Goodbye!
