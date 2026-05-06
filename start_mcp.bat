@echo off
title SpineDoc MCP Server

:: clean up FRP process
taskkill /f /im frpc.exe >nul 2>nul

echo Starting FRP tunnel...
start "FRP" cmd /c "cd /d %~dp0frp_0.61.2_windows_amd64 && frpc.exe -c frpc.toml"

echo Waiting 2s for FRP to initialize...
timeout /t 2 /nobreak >nul

echo Starting MCP server on port 7000...
cd /d %~dp0
set MCP_TRANSPORT=sse
set MCP_PORT=7000

.venv\Scripts\python.exe spine_interaction\aily\mcp_server.py

echo [MCP] Cleaning up FRP tunnel...
taskkill /f /im frpc.exe >nul 2>nul
echo [MCP] All processes stopped.
