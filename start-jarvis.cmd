@echo off
rem Jarvis launcher for Windows — double-click to start. Needs Node.js only, no Python.
rem   start-jarvis.cmd          web chat in the browser (+ Telegram bot if configured)
rem   start-jarvis.cmd --cli    chat in this terminal window instead
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js was not found. Install it from https://nodejs.org and try again.
  pause
  exit /b 1
)
node node\start.mjs %*
if errorlevel 1 pause
