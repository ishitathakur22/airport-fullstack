@echo off
echo ========================================================
echo Starting SkyRoute Ops...
echo ========================================================

echo Starting Backend Server...
start "SkyRoute Backend" cmd /k "call venv\Scripts\activate.bat && cd backend && uvicorn main:app --reload --port 8000"

echo Starting Frontend Server...
start "SkyRoute Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Both servers are starting in separate windows.
echo The frontend should automatically open in your browser shortly.
echo If it doesn't, navigate to http://localhost:5173
echo.
echo To stop the servers, close the newly opened command prompt windows.
echo ========================================================
pause
