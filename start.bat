@echo off
chcp 65001 >nul
title Save Mod
cd /d "%~dp0"

if not exist "data" mkdir data

if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

"%PY%" -m bot.panel 1>>"data\panel_stdout.log" 2>>"data\panel_crash.log"
set ERR=%ERRORLEVEL%
if %ERR% NEQ 0 (
    echo.
    echo Панель завершилась с кодом %ERR%.
    echo Смотри data\panel_crash.log
    echo.
    pause
)
