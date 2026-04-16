@echo off
title EnvPortal Server
echo Starting independent PowerShell Web Server...
powershell -ExecutionPolicy Bypass -File "%~dp0server.ps1"
pause
