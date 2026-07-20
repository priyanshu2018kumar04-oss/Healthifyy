@echo off
echo Starting Healthify AI Backend...
echo.
echo Make sure you have set your GROQ_API_KEY in the .env file!
echo.

REM Use python -m uvicorn to ensure the correct Python is used
python -m uvicorn main:app --reload --port 8000

pause
