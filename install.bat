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
python -m pip install pywebview pystray Pillow
if %errorlevel% neq 0 (
    echo   ✗ 依赖安装失败
    pause
    exit /b 1
)
echo   ✓ 依赖安装完成

:: ── 检测 Hermes Agent ──
echo [4/5] 检测 Hermes Agent ...
where hermes >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✓ Hermes Agent 已安装
    goto :deploy
)

echo   ◌ Hermes Agent 未检测到，正在安装...
python -m pip install hermes-agent
if %errorlevel% neq 0 (
    echo   ✗ 安装失败，请手动安装: pip install hermes-agent
    pause
    exit /b 1
)
echo   ✓ Hermes Agent 安装完成

:deploy
:: ── 部署文件 ──
echo [5/5] 部署 Hermes Pulse ...
:: 用户目录，不要管理员权限
set "INSTALL_DIR=%LOCALAPPDATA%\Programs\Hermes Pulse"

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
copy /Y "%~dp0start_config_server.vbs" "%INSTALL_DIR%\" >nul 2>nul

:: 找到 pythonw.exe 绝对路径
for /f "delims=" %%P in ('where pythonw 2^>nul') do set "PYTHONW=%%P"
if "%PYTHONW%"=="" set "PYTHONW=pythonw.exe"

:: 创建 VBS 启动器（绝对路径，无黑窗）
> "%INSTALL_DIR%\Hermes.vbs" echo Set WshShell = CreateObject("WScript.Shell")
>> "%INSTALL_DIR%\Hermes.vbs" echo WshShell.CurrentDirectory = "%INSTALL_DIR%"
>> "%INSTALL_DIR%\Hermes.vbs" echo WshShell.Run """%PYTHONW%"" ""%INSTALL_DIR%\hermes_gui.py""", 0, False

:: 创建桌面 .lnk 快捷方式（无 UAC 弹窗）
:: 桌面可能在 D 盘（中文 Windows），两个都建
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $d1 = [Environment]::GetFolderPath('Desktop'); $targets = @($d1, 'D:\桌面', 'D:\Desktop'); foreach ($d in $targets) { if (Test-Path $d) { $lnk = $ws.CreateShortcut((Join-Path $d 'Hermes Pulse.lnk')); $lnk.TargetPath = '%INSTALL_DIR%\Hermes.vbs'; $lnk.WorkingDirectory = '%INSTALL_DIR%'; $lnk.IconLocation = '%INSTALL_DIR%\hermes.ico,0'; $lnk.WindowStyle = 7; $lnk.Description = 'Hermes Pulse - Hermes Agent 桌面客户端'; $lnk.Save(); Write-Host ('  ✓ 桌面快捷方式: ' + (Join-Path $d 'Hermes Pulse.lnk')) } }"

echo.
echo  ╔══════════════════════════════════════╗
echo  ║   ✓ 安装完成！                      ║
echo  ║   安装目录: %INSTALL_DIR%           ║
echo  ║   双击桌面 "Hermes Pulse" 启动      ║
echo  ╚══════════════════════════════════════╝
echo.
pause
