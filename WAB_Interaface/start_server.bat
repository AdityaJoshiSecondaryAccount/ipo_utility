@echo off
title ADwealth WhatsApp Business Inbox
echo =================================================================
echo   Starting ADwealth WhatsApp Inbox on http://localhost:8001
echo =================================================================
echo.
cd /d "%~dp0backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --reload-dir "%~dp0backend" --reload-dir "%~dp0..\whatsapp"
pause
