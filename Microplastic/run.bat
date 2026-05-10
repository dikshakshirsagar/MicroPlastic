@echo off
REM ══════════════════════════════════════════════════════
REM  Microplastic Detection Dashboard — Launcher
REM  Uses the Conda 'microplastic' env directly.
REM  Double-click this file OR run it from any terminal.
REM ══════════════════════════════════════════════════════

SET PYTHON=D:\Miniconda3\envs\microplastic\python.exe
SET APP=%~dp0app.py

IF NOT EXIST "%PYTHON%" (
    echo.
    echo  ERROR: Cannot find Conda Python at:
    echo  %PYTHON%
    echo.
    echo  Make sure Miniconda is installed at D:\Miniconda3
    echo  and the 'microplastic' environment exists.
    pause
    exit /b 1
)

echo.
echo  =====================================================
echo    Microplastic Detection Dashboard
echo    Python : %PYTHON%
echo    App    : %APP%
echo  =====================================================
echo.
echo  Open in browser: http://localhost:5000
echo  Press Ctrl+C to stop.
echo.

"%PYTHON%" "%APP%"
pause
