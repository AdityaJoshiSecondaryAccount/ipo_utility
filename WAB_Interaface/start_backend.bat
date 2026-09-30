@echo off
title ADwealth WhatsApp Inbox - Backend
echo Starting WhatsApp Inbox Backend on http://localhost:8001 ...
cd /d "%~dp0backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --reload-dir "%~dp0backend" --reload-dir "%~dp0..\whatsapp"
pause

