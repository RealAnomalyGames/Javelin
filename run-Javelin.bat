@echo off
setlocal
cd /d "%~dp0"

python -m compiler.run
set "RESULT=%ERRORLEVEL%"

if not "%RESULT%"=="0" (
    echo.
    echo Javelin program failed.
    exit /b %RESULT%
)

exit /b 0