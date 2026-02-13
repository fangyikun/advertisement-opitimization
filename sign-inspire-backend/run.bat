@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
