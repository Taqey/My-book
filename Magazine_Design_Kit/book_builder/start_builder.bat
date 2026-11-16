@echo off
chcp 65001 >nul
title Book Builder
cd /d "%~dp0"
echo Starting Book Builder on http://127.0.0.1:8765 ...
start "" http://127.0.0.1:8765
"C:\Users\Taqey\AppData\Local\Programs\Python\Python314\python.exe" server.py
pause
