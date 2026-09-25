@echo off
title MedSecure - Secure Doctor Medical Record Management System
cls
echo ============================================================
echo   MedSecure - Doctor Medical Record Management System
echo ============================================================
echo.
echo   [+] Starting FastAPI Backend Server...
echo   [+] Dashboard URL: http://localhost:8000
echo   [+] API Docs URL:  http://localhost:8000/docs
echo.
echo ============================================================
echo.

:: Automatically open default browser after a brief delay
timeout /t 2 /nobreak >nul
start http://localhost:8000

:: Run the application
python run.py

pause
