@echo off
chcp 65001 >nul 2>&1
title Hermes Pulse Installer
color 0F

echo.
echo  ========================================
echo       Hermes Pulse Installer
echo       Light in Form. Intelligent at Heart.
echo  ========================================
echo.

:: 获取脚本所在目录（解压后的目录）
set "SRC_DIR=%~dp0"
set "SRC_DIR=%SRC_DIR:~0,-1%"

:: 检查 Python
echo  [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found.
    echo  Please install Python 3.11+ from:
    echo  https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%a in ('python --version 2^>^&1') do set PYVER=%%a
echo  OK Python %PYVER%

:: 检查 pywebview
echo.
echo  [2/5] Checking pywebview...
python -c "import webview" >nul 2>&1
if errorlevel 1 (
    echo  Installing pywebview...
    pip install pywebview >nul 2>&1
    if errorlevel 1 (
        echo  [ERROR] Failed to install pywebview.
        echo  Please run: pip install pywebview
        pause
        exit /b 1
    )
)
echo  OK pywebview ready

:: 创建安装目录
echo.
echo  [3/5] Installing files...
set "INSTALL_DIR=%ProgramFiles%\Hermes Agent"
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
    if errorlevel 1 (
        echo  [ERROR] Cannot create %INSTALL_DIR%
        echo  Try running as Administrator.
        pause
        exit /b 1
    )
)

:: 复制核心文件
copy /Y "%SRC_DIR%\hermes_gui.py" "%INSTALL_DIR%\" >nul
copy /Y "%SRC_DIR%\config_server.py" "%INSTALL_DIR%\" >nul
copy /Y "%SRC_DIR%\app.js" "%INSTALL_DIR%\" >nul
copy /Y "%SRC_DIR%\styles.css" "%INSTALL_DIR%\" >nul
copy /Y "%SRC_DIR%\index.html" "%INSTALL_DIR%\" >nul
copy /Y "%SRC_DIR%\hermes-logo.png" "%INSTALL_DIR%\" >nul
copy /Y "%SRC_DIR%\hermes.ico" "%INSTALL_DIR%\" >nul
copy /Y "%SRC_DIR%\hermes-titlebar.ico" "%INSTALL_DIR%\" >nul
copy /Y "%SRC_DIR%\start_config_server.vbs" "%INSTALL_DIR%\" >nul
copy /Y "%SRC_DIR%\LICENSE" "%INSTALL_DIR%\" >nul

:: 验证安装
if not exist "%INSTALL_DIR%\hermes_gui.py" (
    echo  [ERROR] File copy failed.
    pause
    exit /b 1
)
echo  OK Installed to %INSTALL_DIR%

:: 创建桌面快捷方式
echo.
echo  [4/5] Creating desktop shortcut...
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut([System.IO.Path]::Combine([System.Environment]::GetFolderPath('Desktop'),'Hermes Pulse.lnk')); $s.TargetPath='pythonw.exe'; $s.Arguments='hermes_gui.py'; $s.WorkingDirectory='%INSTALL_DIR%'; $s.IconLocation='%INSTALL_DIR%\hermes.ico'; $s.Save()" >nul 2>&1
if exist "%USERPROFILE%\Desktop\Hermes Pulse.lnk" (
    echo  OK Desktop shortcut created
) else (
    echo  Warning: Shortcut creation failed, but installation is complete
)

:: 完成
echo.
echo  [5/5] Done!
echo.
echo  ========================================
echo       Installation Complete!
echo  ========================================
echo.
echo  Location: %INSTALL_DIR%
echo  Launch:   Double-click "Hermes Pulse" on desktop
echo            or run: pythonw.exe hermes_gui.py
echo.

set /p LAUNCH="Launch now? (Y/N): "
if /i "%LAUNCH%"=="Y" (
    echo  Starting Hermes Pulse...
    start "" pythonw.exe "%INSTALL_DIR%\hermes_gui.py"
)

pause
