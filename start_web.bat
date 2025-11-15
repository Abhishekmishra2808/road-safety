@echo off
REM Simple launcher for Streamlit web interface

echo ========================================
echo Road Safety Analysis - Web Interface
echo ========================================
echo.
echo Starting Streamlit server...
echo Open your browser to: http://localhost:8501
echo.
echo Press Ctrl+C to stop the server
echo.

REM Run streamlit using the virtual environment Python
.venv\Scripts\python.exe -m streamlit run app.py

pause
