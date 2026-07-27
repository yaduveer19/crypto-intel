@echo off
title Crypto Intel Services
echo ============================================
echo   Crypto Intel v3.0 — Starting Services
echo ============================================
echo.

echo [1/2] Starting Backend (mock server)...
start "CI-Backend" cmd /k "cd /d "%~dp0backend" && python mock_server.py"
timeout /t 4 /nobreak >nul

echo [2/2] Starting Frontend (Next.js)...
start "CI-Frontend" cmd /k "cd /d "%~dp0frontend" && npx next dev -p 3000"
timeout /t 8 /nobreak >nul

echo.
echo ============================================
echo   ALL SERVICES RUNNING
echo ============================================
echo.
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo.
echo   Press Ctrl+C in each window to stop.
echo ============================================
pause
