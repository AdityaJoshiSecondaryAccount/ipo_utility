@echo off
title Launch ADwealth WhatsApp Inbox
echo ========================================================
echo   Launching ADwealth WhatsApp Business Inbox System
echo ========================================================
echo.
echo 1. Starting Backend (Port 8001)...
start "ADwealth WA Backend" cmd /c "cd /d "%~dp0backend" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"

echo 2. Starting Frontend UI (Port 5173)...
start "ADwealth WA Frontend" cmd /c "cd /d "%~dp0frontend" && npm run dev"

echo.
echo WhatsApp Inbox UI will be accessible at: http://localhost:5173
echo Webhook URL for Meta/Ngrok: https://your-domain.ngrok-free.app/whatsapp/webhook/
echo.
echo Both servers started in background windows.
pause
