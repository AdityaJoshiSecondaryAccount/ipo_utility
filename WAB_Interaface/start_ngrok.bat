@echo off
title Launch Ngrok for ADwealth WhatsApp Webhook
echo ========================================================
echo   Stopping any old ngrok instances...
taskkill /f /im ngrok.exe >nul 2>&1
timeout /t 1 /nobreak >nul

echo   Starting Ngrok Tunnel -> Port 8001 (FastAPI Backend)
echo   Domain: tweet-collage-barman.ngrok-free.dev
echo ========================================================
echo.
"%~dp0ngrok.exe" http --url=tweet-collage-barman.ngrok-free.dev 8001
if %errorlevel% neq 0 (
    echo.
    echo Trying standard ngrok command...
    "%~dp0ngrok.exe" http 8001
)
pause
