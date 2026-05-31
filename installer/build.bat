@echo off
chcp 65001 >nul 2>&1
title Hermes Pulse Build
echo.
echo  ✦ 打包 Hermes Pulse 发布包...
echo.

set VERSION=1.0.0
set DIST=..\dist
set BUILD=%DIST%\HermesPulse-%VERSION%

:: 清理旧构建
if exist "%DIST%" rmdir /s /q "%DIST%"
mkdir "%DIST%"

:: 创建发布包目录
mkdir "%BUILD%"

:: 复制文件
copy /Y "..\hermes_gui.py" "%BUILD%\" >nul
copy /Y "..\config_server.py" "%BUILD%\" >nul
copy /Y "..\app.js" "%BUILD%\" >nul
copy /Y "..\styles.css" "%BUILD%\" >nul
copy /Y "..\index.html" "%BUILD%\" >nul
copy /Y "..\hermes-logo.png" "%BUILD%\" >nul
copy /Y "..\hermes.ico" "%BUILD%\" >nul
copy /Y "..\hermes-titlebar.ico" "%BUILD%\" >nul
copy /Y "..\start_config_server.vbs" "%BUILD%\" >nul
copy /Y "..\LICENSE" "%BUILD%\" >nul
copy /Y "install.bat" "%BUILD%\" >nul

:: 创建 zip
powershell -Command "Compress-Archive -Path '%BUILD%\*' -DestinationPath '%DIST%\HermesPulse-%VERSION%.zip' -Force"

echo  ✓ 发布包已生成: %DIST%\HermesPulse-%VERSION%.zip
echo.
pause
