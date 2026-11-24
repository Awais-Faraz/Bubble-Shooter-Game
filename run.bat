@echo off
cd /d "%~dp0"
echo Checking Python and pygame...
python -c "import pygame" >nul 2>&1
if errorlevel 1 (
    echo Installing requirements...
    python -m pip install -r requirements.txt
)
python main.py
if errorlevel 1 pause
