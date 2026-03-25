@echo off

REM Install dependencies
pip install -r requirements.txt

REM Build the executable with PyInstaller
pyinstaller --onefile your_script.py

REM Create the installer with NSIS
"C:\Program Files (x86)\NSIS\makensis.exe" your_installer_script.nsi

echo Build process completed.