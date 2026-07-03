@echo off
cd /d %~dp0..
echo Starting Atlas...
py -m pip install -r requirements.txt
py app\main.py
pause
