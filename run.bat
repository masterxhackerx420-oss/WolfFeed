@echo off
echo Starting WolfFeed portable app...
echo.
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Please install Python 3.8+ from python.org
    pause
    exit /b 1
)
pip install -r requirements.txt
python app.py
pause
