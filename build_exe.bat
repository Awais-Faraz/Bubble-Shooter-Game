@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconsole --onefile --name BubbleShooter --add-data "assets;assets" main.py
echo.
echo Done! Your game is in dist\BubbleShooter.exe  (progress is saved in dist\data\progress.json)
pause
