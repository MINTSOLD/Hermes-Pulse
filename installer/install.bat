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

:: ============================================
:: 步骤 1: 检查 Python
:: ============================================
echo  [1/6] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found.
    echo  Please install Python 3.11+ from:
    echo  https://www.python.org/downloads/
    echo  (Make sure to check "Add Python to PATH" during install)
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%a in ('python --version 2^>^&1') do set PYVER=%%a
echo  OK Python %PYVER%

:: ============================================
:: 步骤 2: 检查 pywebview
:: ============================================
echo.
echo  [2/6] Checking pywebview...
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

:: ============================================
:: 步骤 3: 检查 Hermes Agent
:: ============================================
echo.
echo  [3/6] Checking Hermes Agent...
set "HERMES_FOUND=0"

:: 方法1: 检查 hermes.exe (venv)
where hermes.exe >nul 2>&1
if not errorlevel 1 (
    set "HERMES_FOUND=1"
    echo  OK Hermes Agent found (hermes.exe)
)

:: 方法2: 检查 pip 安装的 hermes
if "%HERMES_FOUND%"=="0" (
    python -c "import hermes" >nul 2>&1
    if not errorlevel 1 (
        set "HERMES_FOUND=1"
        echo  OK Hermes Agent found (Python package)
    )
)

:: 方法3: 检查常见安装路径
if "%HERMES_FOUND%"=="0" (
    if exist "%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\hermes.exe" (
        set "HERMES_FOUND=1"
        echo  OK Hermes Agent found at %LOCALAPPDATA%\hermes
    )
)

:: 方法4: 检查 Program Files
if "%HERMES_FOUND%"=="0" (
    if exist "%ProgramFiles%\Hermes Agent\hermes.exe" (
        set "HERMES_FOUND=1"
        echo  OK Hermes Agent found at %ProgramFiles%\Hermes Agent
    )
)

:: 未找到 → 询问是否安装
if "%HERMES_FOUND%"=="0" (
    echo.
    echo  [WARNING] Hermes Agent not detected!
    echo.
    echo  Hermes Pulse requires Hermes Agent as backend.
    echo  Would you like to install it now?
    echo.
    set /p INSTALL_HERMES="Install Hermes Agent? (Y/N): "
    if /i "!INSTALL_HERMES!"=="Y" (
        call :InstallHermes
    ) else (
        echo.
        echo  [INFO] Skipping Hermes Agent installation.
        echo  You can install it later manually:
        echo    pip install hermes-agent
        echo    https://github.com/NousResearch/hermes-agent
        echo.
    )
)

:: ============================================
:: 步骤 4: 安装 Hermes Pulse 文件
:: ============================================
echo.
echo  [4/6] Installing Hermes Pulse...
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

:: ============================================
:: 步骤 5: 创建桌面快捷方式
:: ============================================
echo.
echo  [5/6] Creating desktop shortcut...
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut([System.IO.Path]::Combine([System.Environment]::GetFolderPath('Desktop'),'Hermes Pulse.lnk')); $s.TargetPath='pythonw.exe'; $s.Arguments='hermes_gui.py'; $s.WorkingDirectory='%INSTALL_DIR%'; $s.IconLocation='%INSTALL_DIR%\hermes.ico'; $s.Save()" >nul 2>&1
if exist "%USERPROFILE%\Desktop\Hermes Pulse.lnk" (
    echo  OK Desktop shortcut created
) else (
    echo  Warning: Shortcut creation failed, but installation is complete
)

:: ============================================
:: 步骤 6: 完成
:: ============================================
echo.
echo  [6/6] Done!
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
exit /b 0

:: ============================================
:: 子程序: 安装 Hermes Agent
:: ============================================
:InstallHermes
echo.
echo  Detecting network region...

:: 通过 IP 检测地区（国内用镜像，国外用 PyPI）
set "PIP_INDEX=https://pypi.org/simple"
set "REGION=international"

:: 尝试检测 IP
for /f "tokens=*" %%a in ('python -c "import urllib.request; r=urllib.request.urlopen('https://ipinfo.io/json', timeout=5); print(r.read().decode())" 2^>nul') do set IPINFO=%%a

echo %IPINFO% | findstr /i "China" >nul 2>&1
if not errorlevel 1 (
    set "PIP_INDEX=https://mirrors.aliyun.com/pypi/simple/"
    set "REGION=china"
    echo  Detected: China (using Aliyun mirror)
) else (
    echo  Detected: International (using PyPI)
)

echo.
echo  Installing Hermes Agent via pip...
echo  (This may take a few minutes on first install)
echo.

:: 先尝试用 uv（更快）
where uv >nul 2>&1
if not errorlevel 1 (
    echo  Using uv (fast installer)...
    uv pip install hermes-agent --system --index-url %PIP_INDEX% 2>&1
    if not errorlevel 1 (
        echo  OK Hermes Agent installed via uv
        goto :eof
    )
)

:: 回退到 pip
echo  Using pip...
pip install hermes-agent --index-url %PIP_INDEX% 2>&1
if errorlevel 1 (
    echo.
    echo  [WARNING] Auto-install failed. Please install manually:
    echo    pip install hermes-agent
    echo    https://github.com/NousResearch/hermes-agent
    echo.
) else (
    echo  OK Hermes Agent installed via pip
)
goto :eof
