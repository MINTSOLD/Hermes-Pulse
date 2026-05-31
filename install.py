#!/usr/bin/env python3
"""
Hermes Pulse — 跨平台一键安装器
用法: python install.py
支持: Windows / macOS / Linux / WSL 2
"""

import sys
import os
import subprocess
import platform
import shutil
import urllib.request
from pathlib import Path

# ── 平台检测 ──
IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform == "linux"
IS_WSL = False

if IS_LINUX:
    try:
        with open("/proc/version", "r") as f:
            ver = f.read().lower()
            IS_WSL = "microsoft" in ver or "wsl" in ver
    except:
        pass

# ── 颜色输出 ──
def ok(msg):   print(f"  \033[32m✓\033[0m {msg}")
def fail(msg): print(f"  \033[31m✗\033[0m {msg}")
def info(msg): print(f"  \033[36m●\033[0m {msg}")
def warn(msg): print(f"  \033[33m!\033[0m {msg}")

SCRIPT_DIR = Path(__file__).parent.resolve()

# ══════════════════════════════════════════
#  1. 检测 Python
# ══════════════════════════════════════════
def check_python():
    print("\n[1/6] 检测 Python ...")
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 11):
        fail(f"需要 Python 3.11+，当前: {v.major}.{v.minor}.{v.micro}")
        fail("下载地址: https://www.python.org/downloads/")
        sys.exit(1)
    ok(f"Python {v.major}.{v.minor}.{v.micro}")
    return sys.executable

# ══════════════════════════════════════════
#  2. 安装 pip 依赖
# ══════════════════════════════════════════
def install_deps(python):
    print("\n[2/6] 安装依赖 ...")
    deps = ["pywebview", "pystray", "Pillow"]
    subprocess.check_call(
        [python, "-m", "pip", "install"] + deps + ["--quiet"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    ok(f"已安装: {', '.join(deps)}")

# ══════════════════════════════════════════
#  3. 检测/安装 Hermes Agent
# ══════════════════════════════════════════
def check_hermes(python):
    print("\n[3/6] 检测 Hermes Agent ...")
    # 检查 hermes 命令
    hermes_cmd = shutil.which("hermes")
    if hermes_cmd:
        ok(f"Hermes Agent 已安装: {hermes_cmd}")
        return True

    # 尝试 pip 安装
    warn("Hermes Agent 未检测到，正在安装...")
    try:
        subprocess.check_call(
            [python, "-m", "pip", "install", "hermes-agent", "--quiet"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        ok("Hermes Agent 安装完成")
        return True
    except:
        fail("安装失败，请手动安装: pip install hermes-agent")
        return False

# ══════════════════════════════════════════
#  4. 确定安装目录
# ══════════════════════════════════════════
def get_install_dir():
    if IS_WIN:
        return Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Hermes Agent"
    elif IS_MAC:
        return Path.home() / "Library" / "Application Support" / "Hermes Pulse"
    else:
        return Path.home() / ".local" / "share" / "hermes-pulse"

# ══════════════════════════════════════════
#  5. 部署文件
# ══════════════════════════════════════════
def deploy_files(install_dir):
    print("\n[4/6] 部署文件 ...")
    install_dir.mkdir(parents=True, exist_ok=True)

    files = [
        "hermes_gui.py", "config_server.py",
        "index.html", "styles.css", "app.js",
        "hermes-logo.png", "hermes.ico", "hermes-titlebar.ico",
    ]

    for f in files:
        src = SCRIPT_DIR / f
        dst = install_dir / f
        if src.exists():
            shutil.copy2(src, dst)
        else:
            warn(f"跳过（不存在）: {f}")

    ok(f"已部署到: {install_dir}")

# ══════════════════════════════════════════
#  6. 创建启动方式
# ══════════════════════════════════════════
def create_launcher(install_dir, python):
    print("\n[5/6] 创建启动方式 ...")

    gui_script = install_dir / "hermes_gui.py"

    if IS_WIN:
        # VBS 启动器（隐藏窗口）
        vbs = install_dir / "Hermes.vbs"
        vbs_content = f'Set WshShell = CreateObject("WScript.Shell")\nWshShell.Run """{python}"" ""{gui_script}""", 0, False'
        vbs.write_text(vbs_content, encoding="utf-8")

        # 桌面快捷方式
        desktop = Path.home() / "Desktop"
        shortcut = desktop / "Hermes Pulse.vbs"
        shutil.copy2(vbs, shortcut)
        ok(f"桌面快捷方式: {shortcut}")

    elif IS_MAC:
        # .command 脚本
        cmd = install_dir / "Hermes.command"
        cmd.write_text(f'#!/bin/bash\nexec "{python}" "{gui_script}"\n', encoding="utf-8")
        os.chmod(cmd, 0o755)

        # 桌面快捷方式
        desktop = Path.home() / "Desktop"
        link = desktop / "Hermes Pulse.command"
        if not link.exists():
            os.symlink(cmd, link)
        ok(f"桌面启动脚本: {link}")

    else:
        # Linux: ~/.local/bin 命令
        bin_dir = Path.home() / ".local" / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        wrapper = bin_dir / "hermes-pulse"
        wrapper.write_text(
            f'#!/bin/bash\nexec "{python}" "{gui_script}" "$@"\n',
            encoding="utf-8"
        )
        os.chmod(wrapper, 0o755)
        ok(f"命令已创建: hermes-pulse")

        # 检查 PATH
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)
        if str(bin_dir) not in path_dirs:
            warn(f"请将 {bin_dir} 添加到 PATH")
            warn(f"  echo 'export PATH=\"{bin_dir}:$PATH\"' >> ~/.bashrc")

# ══════════════════════════════════════════
#  7. WSL 特殊处理
# ══════════════════════════════════════════
def wsl_note():
    if IS_WSL:
        print("\n" + "=" * 50)
        warn("检测到 WSL 2 环境")
        info("Hermes Pulse 会启动服务并打印 URL")
        info("请在 Windows 浏览器中打开该 URL")
        info("或安装 WSLg 后直接运行 GUI")
        print("=" * 50)

# ══════════════════════════════════════════
#  主流程
# ══════════════════════════════════════════
def main():
    os_name = "Windows" if IS_WIN else "macOS" if IS_MAC else "WSL 2" if IS_WSL else "Linux"
    print(f"\n{'=' * 50}")
    print(f"  ✦ Hermes Pulse 安装程序")
    print(f"  平台: {os_name}")
    print(f"{'=' * 50}")

    python = check_python()
    install_deps(python)
    check_hermes(python)
    install_dir = get_install_dir()
    deploy_files(install_dir)
    create_launcher(install_dir, python)
    wsl_note()

    print(f"\n{'=' * 50}")
    print(f"  ✓ 安装完成！")
    if IS_WIN:
        print(f"  双击桌面 'Hermes Pulse' 启动")
    elif IS_MAC:
        print(f"  双击桌面 'Hermes Pulse' 启动")
    else:
        print(f"  终端输入 hermes-pulse 启动")
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    main()
