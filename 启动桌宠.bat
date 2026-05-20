@echo off
cd /d "%~dp0"

echo 正在启动后端服务...
start /B /MIN "" cmd /c "cd /d "%~dp0backend" && python app.py"

echo 正在启动桌宠...
timeout /t 3 /nobreak >nul
start "" "%CD%\node_modules\electron\dist\electron.exe" "%CD%"

exit
