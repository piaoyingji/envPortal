@echo off
title Environment Server Deployer
echo Starting independent PowerShell Web Server...
powershell -ExecutionPolicy Bypass -File "%~dp0server.ps1"
pause
