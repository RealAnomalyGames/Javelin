@echo off
setlocal

title Javelin DOS Compiler

REM Always switch to the Javelin project directory.
cd /d "%~dp0"

echo.
echo ======================================
echo       JAVELIN DOS BUILD
echo ======================================
echo.

REM Verify that PowerShell is available.
where powershell.exe >nul 2>&1
if errorlevel 1 (
    echo ERROR: Windows PowerShell was not found.
    pause
    exit /b 1
)

REM Run the PowerShell build workflow.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-Javelin.ps1"

if errorlevel 1 (
    echo.
    echo Javelin build FAILED.
    pause
    exit /b 1
)

echo.
echo Javelin build completed successfully.
echo Output: "%~dp0output\main.exe"
echo.
pause

endlocal