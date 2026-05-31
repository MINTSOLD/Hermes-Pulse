@echo off
chcp 65001 >nul
title Hermes Pulse Installer

echo.
echo  ╔══════════════════════════════════════╗
echo  ║     ✦ Hermes Pulse 安装程序 ✦       ║
echo  ║        轻于形 · 智于心              ║
echo  ╚══════════════════════════════════════╝
echo.

:: ── 检测 Python ──
echo [1/5] 检测 Python ...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo   ✗ 未检测到 Python，请先安装 Python 3.11+
    echo   下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo   ✓ Python %PYVER%

:: ── 检测 pip ──
echo [2/5] 检测 pip ...
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   ✗ pip 未安装，正在安装...
    python -m ensurepip --upgrade
)
echo   ✓ pip 就绪

:: ── 安装依赖 ──
echo [3/5] 安装依赖 ...
python -m pip install pywebview pystray Pillow --quiet 2>nul
echo   ✓ 依赖安装完成

:: ── 检测 Hermes Agent ──
echo [4/5] 检测 Hermes Agent ...
where hermes >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✓ Hermes Agent 已安装
    goto :deploy
)

echo   ◌ Hermes Agent 未检测到，正在安装...
python -m pip install hermes-agent --quiet 2>nul
if %errorlevel% neq 0 (
    echo   ✗ 安装失败，请手动安装: pip install hermes-agent
    pause
    exit /b 1
)
echo   ✓ Hermes Agent 安装完成

:deploy
:: ── 部署文件 ──
echo [5/5] 部署 Hermes Pulse ...
set INSTALL_DIR=%ProgramFiles%\Hermes Agent

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: 复制文件
copy /Y "%~dp0hermes_gui.py" "%INSTALL_DIR%\" >nul
copy /Y "%~dp0config_server.py" "%INSTALL_DIR%\" >nul
copy /Y "%~dp0index.html" "%INSTALL_DIR%\" >nul
copy /Y "%~dp0styles.css" "%INSTALL_DIR%\" >nul
copy /Y "%~dp0app.js" "%INSTALL_DIR%\" >nul
copy /Y "%~dp0hermes-logo.png" "%INSTALL_DIR%\" >nul 2>nul
copy /Y "%~dp0hermes.ico" "%INSTALL_DIR%\" >nul 2>nul
copy /Y "%~dp0hermes-titlebar.ico" "%INSTALL_DIR%\" >nul 2>nul

:: 创建启动脚本
echo Set WshShell = CreateObject("WScript.Shell") > "%INSTALL_DIR%\Hermes.vbs"
echo WshShell.Run "pythonw.exe ""%INSTALL_DIR%\hermes_gui.py""", 0, False >> "%INSTALL_DIR%\Hermes.vbs"

:: 创建桌面快捷方式
echo Set WshShell = CreateObject("WScript.Shell") > "%USERPROFILE%\Desktop\Hermes Pulse.vbs"
echo WshShell.Run "pythonw.exe ""%INSTALL_DIR%\hermes_gui.py""", 0, False >> "%USERPROFILE%\Desktop\Hermes Pulse.vbs"

echo.
echo  ╔══════════════════════════════════════╗
echo  ║   ✓ 安装完成！                      ║
echo  ║   双击桌面 "Hermes Pulse" 启动      ║
echo  ╚══════════════════════════════════════╝
echo.
pause
