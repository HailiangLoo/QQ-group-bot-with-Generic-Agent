@echo off
setlocal

rem Copy this file to start-gateway-wsl.bat and adjust paths.
rem Do not commit real keys in this file.

set DISTRO=agentbox
set PROJECT=/mnt/d/wsl/agentbox/group-memory-agent

wsl.exe -d %DISTRO% -- bash -lc "cd %PROJECT% && source .venv/bin/activate && python scripts/run_onebot_gateway.py --config config.toml"

