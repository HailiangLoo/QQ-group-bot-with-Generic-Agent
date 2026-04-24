@echo off
setlocal

rem Template only. Adjust QCE/NapCat path for your own machine.
rem Keep QQ credentials out of this file.

set QCE_DIR=C:\path\to\qce
cd /d "%QCE_DIR%"
start "" "%QCE_DIR%\start.bat"

