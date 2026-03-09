@echo off
REM ProtocolScout Flask Application Startup Script for Windows

echo ==========================================
echo   ProtocolScout Web Application
echo ==========================================
echo.

REM Check if .env file exists
if not exist .env (
    echo Error: .env file not found!
    echo Please create .env file from .env.example and configure your AWS credentials
    echo.
    echo Run: copy .env.example .env
    echo Then edit .env with your AWS credentials
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt --quiet

REM Load environment variables from .env
for /f "tokens=*" %%a in ('type .env ^| findstr /v "^#"') do set %%a

echo.
echo Setup complete!
echo.
echo Starting Flask application...
echo Application will be available at: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo.

REM Run Flask app
python app.py

pause
