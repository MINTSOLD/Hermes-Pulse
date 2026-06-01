import sys, os, time, threading, socket, subprocess
import platform
from pathlib import Path

# ── Windows-only: add custom Python site-packages path ──
if sys.platform == "win32":
    _py311 = r"C:\Program Files\Python311\Lib\site-packages"
    if os.path.isdir(_py311) and _py311 not in sys.path:
        sys.path.insert(0, _py311)

from PIL import Image as PILImage
import webview

# ── Platform detection ──
_IS_WIN = sys.platform == "win32"
_IS_MAC = sys.platform == "darwin"
_IS_LINUX = sys.platform.startswith("linux")
_IS_WSL = False
if _IS_LINUX:
    try:
        _proc_version = Path("/proc/version").read_text()
        _IS_WSL = "microsoft" in _proc_version.lower() or "wsl" in _proc_version.lower()
    except Exception:
        pass

# ── Cross-platform ctypes import (Windows only) ──
ctypes = None
if _IS_WIN:
    import ctypes as _ctypes
    ctypes = _ctypes

URL = "http://127.0.0.1:18765/"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_TASKBAR = os.path.join(SCRIPT_DIR, "hermes.ico")
LOGO_PNG = os.path.join(SCRIPT_DIR, "hermes-logo.png")
CONFIG_SERVER = os.path.join(SCRIPT_DIR, "config_server.py")

# ── Win32 constants (only used on Windows) ──
if _IS_WIN:
    DWMWA_CAPTION_COLOR = 35
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20

window = None
tray_icon = None
_minimize_to_tray = False


# ══════════════════════════════════════════
#  Single-instance lock (Windows only)
# ══════════════════════════════════════════
_instance_mutex = None

def _acquire_instance_lock():
    """尝试获取单实例锁，防止重复启动"""
    global _instance_mutex
    if not _IS_WIN:
        return True
    try:
        import ctypes as _ctypes_mod
        kernel32 = _ctypes_mod.windll.kernel32
        # CreateMutexW: 如果已存在则 GetLastError == ERROR_ALREADY_EXISTS (183)
        _instance_mutex = kernel32.CreateMutexW(None, True, "HermesPulse_SingleInstance")
        if _ctypes_mod.windll.kernel32.GetLastError() == 183:
            return False  # 已有实例在运行
        return True
    except Exception:
        return True  # 获取锁失败也放行


# ══════════════════════════════════════════
#  Cross-platform helpers
# ══════════════════════════════════════════

def _get_python_command():
    """Return the Python command to use for spawning config_server."""
    if _IS_WIN:
        # Look for pythonw.exe in common locations
        candidates = [
            r"C:\Program Files\Python311\pythonw.exe",
            os.path.join(sys.prefix, "pythonw.exe"),
        ]
        # Also try the same directory as the running python
        py_dir = os.path.dirname(sys.executable)
        candidates.insert(0, os.path.join(py_dir, "pythonw.exe"))
        for p in candidates:
            if os.path.isfile(p):
                return p
        # Fallback: use sys.executable (will show console window)
        return sys.executable
    else:
        # macOS / Linux: use the running Python interpreter
        return sys.executable


def _find_hermes_command():
    """Return the hermes command/path to use for launching gateway."""
    if _IS_WIN:
        # Check the known venv location first
        hermes_exe = os.path.join(
            str(Path.home()), "AppData", "Local", "hermes", "hermes-agent",
            "venv", "Scripts", "hermes.exe"
        )
        if os.path.exists(hermes_exe):
            return hermes_exe
        # Check if 'hermes' is on PATH
        hermes_which = _which("hermes.exe") or _which("hermes")
        if hermes_which:
            return hermes_which
        return None
    else:
        # macOS / Linux: look for 'hermes' in PATH
        hermes_path = _which("hermes")
        if hermes_path:
            return hermes_path
        # macOS venv pattern
        if _IS_MAC:
            venv_hermes = os.path.join(
                str(Path.home()), ".local", "hermes", "hermes-agent",
                "venv", "bin", "hermes"
            )
            if os.path.isfile(venv_hermes):
                return venv_hermes
        # Linux venv pattern
        if _IS_LINUX:
            venv_hermes = os.path.join(
                str(Path.home()), ".local", "hermes", "hermes-agent",
                "venv", "bin", "hermes"
            )
            if os.path.isfile(venv_hermes):
                return venv_hermes
        return None


def _which(cmd):
    """Simple shutil.which replacement."""
    import shutil
    return shutil.which(cmd)


def _get_creationflags():
    """Return creationflags for subprocess on Windows (DETACHED_PROCESS), else 0."""
    if _IS_WIN:
        return 0x08000000  # CREATE_NO_WINDOW / DETACHED
    return 0


def _open_url_in_browser(url):
    """Open a URL in the default browser (used by WSL fallback)."""
    import webbrowser
    webbrowser.open(url)


# ══════════════════════════════════════════
#  Port check
# ══════════════════════════════════════════

def _port_alive(port, timeout=1):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except Exception:
        return False
    finally:
        s.close()


# ══════════════════════════════════════════
#  Transparent Logo Splash Screen
# ══════════════════════════════════════════
import tkinter as tk


def run_splash():
    """
    Transparent background: logo + semi-transparent status text.
    Returns (screen_cx, logo_screen_y).
    Works on Windows (transparentcolor), simplified on macOS/Linux.
    """
    BG = "#010101"
    LOGO_SIZE = 280

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg=BG)

    # Platform-specific transparency
    if _IS_WIN:
        # Windows: transparentcolor makes the BG color invisible
        root.attributes("-transparentcolor", BG)
    elif _IS_MAC:
        # macOS: can't do color-key transparency; use alpha for a dark themed splash
        # This makes the whole window slightly transparent — still looks good
        try:
            root.attributes("-alpha", 0.95)
        except Exception:
            pass
    elif _IS_LINUX:
        # Linux/X11: try transparentcolor (works on some WMs), fall back to solid BG
        try:
            root.attributes("-transparentcolor", BG)
        except Exception:
            pass
    # WSL: same as Linux

    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()

    # Window size: Logo(280) + gap(20) + text area(50) = 350
    W, H = 340, 360
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    canvas = tk.Canvas(root, width=W, height=H, bg=BG, highlightthickness=0)
    canvas.pack()

    # Logo centered upper area
    logo_y = H // 2 - 25
    logo_tk = None
    if os.path.exists(LOGO_PNG):
        try:
            pil = PILImage.open(LOGO_PNG).convert("RGBA")
            pil = pil.resize((LOGO_SIZE, LOGO_SIZE), PILImage.LANCZOS)
            from PIL import ImageTk
            logo_tk = ImageTk.PhotoImage(pil)
            canvas.create_image(W // 2, logo_y, image=logo_tk, anchor="center")
        except Exception:
            pass

    # Semi-transparent dark bg + white status text — 动态大小圆角矩形
    text_bg_y = logo_y + LOGO_SIZE // 2 + 22

    def _draw_rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs):
        """画胶囊形（两端半圆）"""
        import math
        points = []
        # 右半圆
        cy = (y1 + y2) / 2
        rx = (x2 - x1) / 2
        ry = (y2 - y1) / 2
        cx = (x1 + x2) / 2
        # 右半圆 (0 to 180)
        for deg in range(-90, 91, 5):
            rad = math.radians(deg)
            points.append(cx + rx + ry * math.cos(rad))
            points.append(cy + ry * math.sin(rad))
        # 左半圆 (180 to 360)
        for deg in range(90, 271, 5):
            rad = math.radians(deg)
            points.append(cx - rx + ry * math.cos(rad))
            points.append(cy + ry * math.sin(rad))
        return canvas.create_polygon(points, smooth=False, **kwargs)

    _splash_font = ("Helvetica", 10)
    if _IS_WIN:
        _splash_font = ("Microsoft YaHei", 10)

    # 先创建文字，测量宽度后再画背景
    status_id = canvas.create_text(
        W // 2, text_bg_y,
        text="正 在 启 动 ...",
        font=_splash_font, fill="#cccccc", anchor="center"
    )
    root.update()

    def _update_splash_text(text):
        """更新文字并动态调整背景大小"""
        nonlocal text_bg_y
        canvas.itemconfig(status_id, text=text)
        root.update()
        # 测量文字实际宽度
        bbox = canvas.bbox(status_id)
        if bbox:
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            pad_x, pad_y = 24, 10
            rx1 = W // 2 - tw // 2 - pad_x
            ry1 = text_bg_y - th // 2 - pad_y
            rx2 = W // 2 + tw // 2 + pad_x
            ry2 = text_bg_y + th // 2 + pad_y
            # 胶囊形：圆角半径 = 高度的一半
            corner_r = (ry2 - ry1) // 2
            # 删除旧背景
            canvas.delete("splash_bg")
            _draw_rounded_rect(canvas, rx1, ry1, rx2, ry2, corner_r,
                               fill="#333333", outline="", stipple="gray50",
                               tags="splash_bg")
            # 把背景移到文字下面
            canvas.tag_lower("splash_bg", status_id)

    root.update()

    # 真实检测服务状态，最多等 8 秒
    import socket as _sock
    def _port_ok(port, timeout=1):
        s = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect(("127.0.0.1", port))
            s.close()
            return True
        except:
            return False

    start_time = time.time()
    step = 0
    max_wait = 8.0  # 网关已通过 Scheduled Task 启动，不需要等太久

    while time.time() - start_time < max_wait:
        elapsed = time.time() - start_time

        if step == 0:
            _update_splash_text("正 在 启 动 ...")
            step = 1
        elif step == 1 and elapsed >= 0.5:
            if _port_ok(18765):
                _update_splash_text("配 置 服 务 就 绪 ✓")
                step = 2
            else:
                _update_splash_text("等 待 配 置 服 务 ...")
        elif step == 2 and elapsed >= 1.5:
            if _port_ok(8642):
                _update_splash_text("AI 网 关 就 绪 ✓")
                step = 3
            elif elapsed >= 3.0:
                # 网关没就绪也不要卡住，直接继续
                step = 3
        elif step == 3 and elapsed >= 2.0:
            _update_splash_text("准 备 就 绪")
            step = 4
            break  # 所有服务就绪，立即退出

        try:
            root.update()
        except Exception:
            break
        time.sleep(0.05)

    # 最终状态：根据实际端口检测结果准确显示
    cfg_ok = _port_ok(18765)
    gw_ok = _port_ok(8642)
    if cfg_ok and gw_ok:
        _update_splash_text("准 备 就 绪")
    elif cfg_ok:
        _update_splash_text("网 关 启 动 中 ...")
    else:
        _update_splash_text("准 备 就 绪")
    try:
        root.update()
    except Exception:
        pass

    logo_screen_y = y + logo_y
    try:
        root.destroy()
    except Exception:
        pass

    return sw // 2, logo_screen_y


# ══════════════════════════════════════════
#  System Tray
# ══════════════════════════════════════════

def _tray_show(icon, item):
    global window
    if window:
        window.show()
        _focus_window()


def _tray_hide(icon, item):
    global window
    if window:
        window.hide()


def _tray_exit(icon, item):
    global _minimize_to_tray
    _minimize_to_tray = False
    if window:
        window.destroy()
    if tray_icon:
        tray_icon.stop()
    os._exit(0)


def _focus_window():
    global window
    if not window:
        return
    if _IS_WIN:
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.FindWindowW(None, "Hermes")
            if hwnd:
                user32.SetForegroundWindow(hwnd)
                user32.ShowWindow(hwnd, 9)
        except Exception:
            pass
    # macOS/Linux: pystray + pywebview handle focus natively
    # No extra action needed.


def start_tray():
    global tray_icon
    import pystray
    icon_image = None
    if os.path.exists(ICON_TASKBAR):
        try:
            icon_image = PILImage.open(ICON_TASKBAR)
        except Exception:
            pass
    if icon_image is None:
        icon_image = PILImage.new("RGB", (16, 16), (212, 175, 55))
    menu = pystray.Menu(
        pystray.MenuItem("显示 Hermes", _tray_show, default=True),
        pystray.MenuItem("隐藏 Hermes", _tray_hide),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", _tray_exit),
    )
    tray_icon = pystray.Icon("Hermes", icon_image, "Hermes Pulse", menu)
    tray_icon.run()


# ══════════════════════════════════════════
#  Service Launchers
# ══════════════════════════════════════════

def ensure_config_server():
    if _port_alive(18765):
        return
    python_cmd = _get_python_command()
    try:
        subprocess.Popen(
            [python_cmd, CONFIG_SERVER],
            creationflags=_get_creationflags(),
            stdout=subprocess.DEVNULL if not _IS_WIN else subprocess.DEVNULL,
            stderr=subprocess.DEVNULL if not _IS_WIN else subprocess.DEVNULL,
        )
    except Exception:
        pass
    for i in range(30):
        time.sleep(1)
        if _port_alive(18765):
            return


def ensure_gateway():
    """确保 Gateway 运行，如未运行则通过 pythonw.exe 静默启动"""
    if _port_alive(8642):
        return
    # 先等 5 秒，让 Scheduled Task 有机会启动
    for i in range(5):
        time.sleep(1)
        if _port_alive(8642):
            return
    # 还没运行？用 pythonw.exe 静默启动（绝对不弹黑窗口）
    if _IS_WIN:
        hermes_dir = Path.home() / "AppData" / "Local" / "hermes" / "hermes-agent"
        pythonw = hermes_dir / "venv" / "Scripts" / "pythonw.exe"
        if pythonw.exists():
            try:
                subprocess.Popen(
                    [str(pythonw), "-m", "hermes_cli.main", "gateway", "run"],
                    cwd=str(hermes_dir),
                    creationflags=0x08000000,  # CREATE_NO_WINDOW
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass
    # 等待 Gateway 端口就绪（最多 15 秒）
    for i in range(15):
        time.sleep(1)
        if _port_alive(8642):
            return


# ══════════════════════════════════════════
#  Win32 Dark Title Bar (Windows only)
# ══════════════════════════════════════════

def _apply_dark_titlebar(hwnd):
    """设置深色标题栏（仅颜色，图标由 pywebview 原生处理）"""
    if not _IS_WIN:
        return
    dwmapi = ctypes.windll.dwmapi
    # 设置标题栏颜色为纯黑
    try:
        dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR,
            ctypes.byref(ctypes.c_int(0x000000)), 4)
    except Exception:
        pass
    # 设置边框颜色为纯黑（消除 Windows 11 的灰色边框）
    try:
        dwmapi.DwmSetWindowAttribute(hwnd, 34,  # DWMWA_BORDER_COLOR
            ctypes.byref(ctypes.c_int(0x000000)), 4)
    except Exception:
        pass
    # 启用深色模式
    try:
        dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(ctypes.c_int(1)), 4)
    except Exception:
        pass


# ══════════════════════════════════════════
#  Window Close Handler
# ══════════════════════════════════════════

def on_window_close():
    global window, _minimize_to_tray
    if _minimize_to_tray:
        window.hide()
        return False
    return True


# ══════════════════════════════════════════
#  Main Entry Point
# ══════════════════════════════════════════

if __name__ == '__main__':
    # Start background services
    threading.Thread(target=ensure_config_server, daemon=True).start()
    threading.Thread(target=ensure_gateway, daemon=True).start()

    # Show the transparent logo splash
    splash_cx, logo_screen_y = run_splash()

    # ── WSL 2 fallback: start services, print URL, exit ──
    if _IS_WSL:
        # Give services time to start
        time.sleep(1)
        print("=" * 50)
        print("  Hermes Pulse (WSL 2 mode)")
        print("=" * 50)
        print(f"\n  Config server: {URL}")
        print(f"  Gateway:       http://127.0.0.1:8642/\n")
        print("  Open the URL above in your Windows browser.")
        print("  To install WSLg support for native GUI:")
        print("    - Ensure WSLg is enabled in your WSL distro")
        print("    - Or run this script from Windows directly.\n")
        try:
            _open_url_in_browser(URL)
            print("  ✓ Attempted to open browser automatically.\n")
        except Exception:
            pass
        # Keep running to maintain the services
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n  Shutting down...")
        sys.exit(0)

    # ── Normal GUI mode (Windows, macOS, Linux with display) ──
    # Check for display on Linux
    if _IS_LINUX and not _IS_WSL:
        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            print("ERROR: No display server detected (DISPLAY/WAYLAND_DISPLAY not set).")
            print("       Please run from a graphical session or set DISPLAY=:0")
            sys.exit(1)

    # ── Single-instance lock (prevent duplicate windows) ──
    if not _acquire_instance_lock():
        # 已有实例在运行，直接退出
        sys.exit(0)

    # Detect screen size
    sw, sh = 1920, 1080
    try:
        import tkinter as _tk
        _r = _tk.Tk()
        sw, sh = _r.winfo_screenwidth(), _r.winfo_screenheight()
        _r.destroy()
    except Exception:
        pass

    win_w, win_h = 1200, 800
    win_x = (sw - win_w) // 2
    win_y = (sh - win_h) // 2

    w = webview.create_window(
        'Hermes', URL,
        x=win_x, y=win_y,
        width=win_w, height=win_h,
        min_size=(800, 600),
        resizable=True, text_select=True,
        hidden=True,
        background_color="#000000")
    window = w
    w.events.closing += on_window_close
    _minimize_to_tray = True

    def show_main():
        global window
        # 先立即显示窗口（不等标题栏），消除 splash → 主程序的空白间隔
        if window:
            window.show()
        # Windows: 后台设置深色标题栏（用户已经看到窗口了）
        if _IS_WIN:
            def _apply_later():
                for _ in range(50):
                    try:
                        if window.native and window.native.Handle:
                            hwnd = window.native.Handle.ToInt32()
                            _apply_dark_titlebar(hwnd)
                            return
                    except Exception:
                        pass
                    time.sleep(0.1)
            threading.Thread(target=_apply_later, daemon=True).start()
        threading.Thread(target=start_tray, daemon=True).start()

    threading.Thread(target=show_main, daemon=True).start()

    # 用 pywebview 原生 icon 参数设置图标（标题栏+任务栏都正确）
    _icon_arg = ICON_TASKBAR if os.path.exists(ICON_TASKBAR) else None
    webview.start(debug=False, icon=_icon_arg)
    os._exit(0)
