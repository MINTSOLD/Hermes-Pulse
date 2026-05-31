@echo off
chcp 65001 >nul 2>&1
title Hermes Pulse Installer
color 0F

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║       ✦  Hermes Pulse  Installer  ✦      ║
echo  ║       轻于形 · 智于心                      ║
echo  ╚══════════════════════════════════════════╝
echo.

:: 检查 Python
echo  [1/4] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo  ❌ 未检测到 Python，请先安装 Python 3.11+
    echo     下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%a in ('python --version 2^>^&1') do set PYVER=%%a
echo  ✓ Python %PYVER%

:: 检查 pywebview
echo.
echo  [2/4] 检查 pywebview...
python -c "import webview" >nul 2>&1
if errorlevel 1 (
    echo  ↓ 正在安装 pywebview...
    pip install pywebview >nul 2>&1
    if errorlevel 1 (
        echo  ❌ pywebview 安装失败
        pause
        exit /b 1
    )
)
echo  ✓ pywebview 已就绪

:: 复制文件
echo.
echo  [3/4] 安装到程序目录...
set INSTALL_DIR=%ProgramFiles%\Hermes Agent
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

copy /Y "%~dp0hermes_gui.py" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%~dp0config_server.py" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%~dp0app.js" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%~dp0styles.css" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%~dp0index.html" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%~dp0hermes-logo.png" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%~dp0hermes.ico" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%~dp0hermes-titlebar.ico" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%~dp0start_config_server.vbs" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%~dp0LICENSE" "%INSTALL_DIR%\" >nul 2>&1

echo  ✓ 已安装到 %INSTALL_DIR%

:: 创建桌面快捷方式
echo.
echo  [4/4] 创建桌面快捷方式...
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%USERPROFILE%\Desktop\Hermes Pulse.lnk');$s.TargetPath='pythonw.exe';$s.Arguments='hermes_gui.py';$s.WorkingDirectory='%INSTALL_DIR%';$s.IconLocation='%INSTALL_DIR%\hermes.ico';$s.Save()" >nul 2>&1
echo  ✓ 桌面快捷方式已创建

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║         ✦  安装完成！  ✦                  ║
echo  ╠══════════════════════════════════════════╣
echo  ║  双击桌面的 "Hermes Pulse" 即可启动       ║
echo  ║  或在开始菜单中找到 Hermes Pulse          ║
echo  ╚══════════════════════════════════════════╝
echo.

set /p LAUNCH="是否立即启动？(Y/N): "
if /i "%LAUNCH%"=="Y" (
    echo  启动中...
    start "" pythonw.exe "%INSTALL_DIR%\hermes_gui.py"
)

pause
