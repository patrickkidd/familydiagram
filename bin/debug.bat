@echo off
setlocal

set LOG_FILE=%~dp0debug_output.log

echo Starting Family Diagram with debug console...
echo.
echo All output will be saved to:
echo %LOG_FILE%
echo.
echo The application will start in a new window.
echo When you close the application, you can email the log file to support.
echo.
echo ========================================
echo.

set FD_LOG_LEVEL=DEBUG
set QT_DEBUG_PLUGINS=1

REM Run without --windows-console to use this console's output
"Family Diagram.exe" > "%LOG_FILE%" 2>&1

echo.
echo ========================================
echo Family Diagram has closed.
echo.
echo Debug output saved to:
echo %LOG_FILE%
echo.
echo You can email this file to support.
echo.
pause