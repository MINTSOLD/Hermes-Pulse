@echo off
chcp 65001 >nul
title Hermes Pulse 安装程序
color 0A

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║                                          ║
echo  ║      ✦  Hermes Pulse  安装程序  ✦       ║
echo  ║          轻于形 · 智于心                 ║
echo  ║                                          ║
echo  ╚══════════════════════════════════════════╝
echo.
echo  正在安装，请稍候...
echo.

:: ── 获取脚本所在目录（用户解压到哪就是哪）──
set "SRC_DIR=%~dp0"

:: ── 安装目录 ──
set "INSTALL_DIR=%ProgramFiles%\Hermes Agent"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: ── 复制所有文件 ──
echo  [1/3] 复制文件...
copy /Y "%SRC_DIR%hermes_gui.py" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%SRC_DIR%config_server.py" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%SRC_DIR%index.html" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%SRC_DIR%styles.css" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%SRC_DIR%app.js" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%SRC_DIR%hermes-logo.png" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%SRC_DIR%hermes.ico" "%INSTALL_DIR%\" >nul 2>&1
copy /Y "%SRC_DIR%hermes-titlebar.ico" "%INSTALL_DIR%\" >nul 2>&1
echo       完成 ✓
echo.

:: ── 安装 Python 依赖 ──
echo  [2/3] 安装运行环境...
python -m pip install pywebview pystray Pillow --quiet >nul 2>&1
if %errorlevel% neq 0 (
    python3 -m pip install pywebview pystray Pillow --quiet >nul 2>&1
)
echo       完成 ✓
echo.

:: ── 创建桌面快捷方式 ──
echo  [3/3] 创建桌面快捷方式...

:: 创建 VBS 启动脚本（隐藏窗口启动）
echo Set WshShell = CreateObject("WScript.Shell") > "%INSTALL_DIR%\Hermes.vbs"
echo WshShell.Run "pythonw.exe ""%INSTALL_DIR%\hermes_gui.py""", 0, False >> "%INSTALL_DIR%\Hermes.vbs"

:: 复制到桌面
copy /Y "%INSTALL_DIR%\Hermes.vbs" "%USERPROFILE%\Desktop\Hermes Pulse.vbs" >nul 2>&1

echo       完成 ✓
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║                                          ║
echo  ║         ✓  安装成功！                    ║
echo  ║                                          ║
echo  ║   双击桌面 "Hermes Pulse" 即可启动       ║
echo  ║                                          ║
echo  ╚══════════════════════════════════════════╝
echo.

:: 询问是否立即启动
set /p "START=是否立即启动？(Y/N): "
if /i "%START%"=="Y" (
    echo 正在启动 Hermes Pulse...
    start "" pythonw.exe "%INSTALL_DIR%\hermes_gui.py"
)

pause
