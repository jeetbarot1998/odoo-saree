@echo off
title Odoo Server Launcher
color 0A

REM Set your Odoo paths here
set PYTHON_PATH=C:\Users\priya\Downloads\odoo\.venv\Scripts\python.exe
set ODOO_PATH=C:\Users\priya\Downloads\odoo\odoo-bin
set ODOO_CONF=C:\Users\priya\Downloads\odoo\odoo.conf
set ODOO_PORT=8069

cls
echo ===================================
echo         Odoo Server Launcher
echo ===================================
echo.

REM Check if Python exists
if not exist "%PYTHON_PATH%" (
    echo Error: Python not found at %PYTHON_PATH%
    echo Please update PYTHON_PATH in the script.
    pause
    exit /b 1
)

REM Check if Odoo exists
if not exist "%ODOO_PATH%" (
    echo Error: Odoo not found at %ODOO_PATH%
    echo Please update ODOO_PATH in the script.
    pause
    exit /b 1
)

REM Check if Config exists
if not exist "%ODOO_CONF%" (
    echo Warning: Configuration file not found at %ODOO_CONF%
    echo Using default configuration...
    set ODOO_CONF=
)

echo Starting Odoo Server...
echo Port: %ODOO_PORT%
echo.
echo Once started, access Odoo at: http://localhost:%ODOO_PORT%
echo.
echo Press Ctrl+C to stop the server
echo ===================================
echo.

REM Start Odoo with the specified configuration
if "%ODOO_CONF%"=="" (
    "%PYTHON_PATH%" "%ODOO_PATH%" --http-port=%ODOO_PORT%
) else (
    "%PYTHON_PATH%" "%ODOO_PATH%" -c "%ODOO_CONF%" --http-port=%ODOO_PORT%
)

REM If Odoo exits with an error
if errorlevel 1 (
    echo.
    echo ===================================
    echo Error: Odoo server stopped unexpectedly
    echo Check the error message above
    echo ===================================
    pause
    exit /b 1
)

pause