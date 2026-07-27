@echo off
echo ============================================
echo  Starting Offline AI Tutor App
echo ============================================
echo.
cd /d "c:\Users\thesa\Downloads\ZIDON\Implementation"
echo Starting backend server on port 5000...
start "ZIDON Backend" /min .\.venv\Scripts\python.exe -m backend.server
timeout /t 2 >nul
echo Starting frontend Kivy app...
echo Window should appear momentarily!
echo.
.\.venv\Scripts\python.exe run_visible.py
echo.
echo App closed. Press any key to exit.
pause
