@echo off
echo ========================================================
echo SkyRoute Ops - Setup Script
echo ========================================================

echo.
echo [1/4] Creating Python Virtual Environment (venv)...
if not exist venv (
    python -m venv venv
) else (
    echo venv already exists, skipping creation.
)
call venv\Scripts\activate.bat

echo.
echo [2/4] Installing Backend Dependencies...
cd backend
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo [3/4] Downloading Local LLM Model (This may take a minute)...
python -c "from llm_manager import download_model; download_model()"

echo.
echo [4/4] Installing Frontend Dependencies...
cd ..\frontend
call npm install

echo.
cd ..
echo ========================================================
echo Setup Complete! 
echo You can now run the system using run.bat
echo ========================================================
pause
