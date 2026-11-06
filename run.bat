@echo off
title Zyren - Next-Generation AI Assistant
cd /d "%~dp0"
echo ========================================================
echo        Starting Zyren AI Assistant...
echo ========================================================
echo.
if exist venv\Scripts\activate (
    call venv\Scripts\activate
)
streamlit run app.py --server.port 8502
pause
