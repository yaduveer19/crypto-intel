@echo off
title Crypto Intel Services
echo ============================================
echo   Crypto Intel v4.0 — Starting Services
echo ============================================
echo.

echo [1/3] Starting Backend (mock server)...
start "CI-Backend" cmd /k "cd /d "%~dp0backend" && python mock_server.py"
timeout /t 4 /nobreak >nul

echo [2/3] Starting Hyperliquid Bridge (optional, :8765)...
start "CI-HLBridge" cmd /k "cd /d "%~dp0backend" && python hl_bridge.py 8765"
timeout /t 2 /nobreak >nul

echo [3/3] Starting Frontend (Next.js)...
start "CI-Frontend" cmd /k "cd /d "%~dp0frontend" && npx next dev -p 3000"
timeout /t 8 /nobreak >nul

echo.
echo ============================================
echo   ALL SERVICES RUNNING
echo ============================================
echo.
echo   Frontend:    http://localhost:3000
echo   Backend:     http://localhost:8000
echo   API Docs:    http://localhost:8000/docs
echo   HL Bridge:   ws://localhost:8765
echo   Market WS:   ws://localhost:8000/ws/market
echo.
echo   Press Ctrl+C in each window to stop.
echo ============================================
pause
