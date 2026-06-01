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
    global _instance_mutex
    if not _IS_WIN:
        return True
    try:
        import ctypes as _ctypes_mod
        kernel32 = _ctypes_mod.windll.kernel32
        _instance_mutex = kernel32.CreateMutexW(None, True, "HermesPulse_SingleInstance")
        if _ctypes_mod.windll.kernel32.GetLastError() == 183:
            return False
        return True
    except Exception:
        return True


# ══════════════════════════════════════════
#  Cross-platform helpers
# ══════════════════════════════════════════

def _get_python_command():
    if _IS_WIN:
        candidates = [
            r"C:\Program Files\Python311\pythonw.exe",
            os.path.join(sys.prefix, "pythonw.exe"),
        ]
        py_dir = os.path.dirname(sys.executable)
        candidates.insert(0, os.path.join(py_dir, "pythonw.exe"))
        for p in candidates:
            if os.path.isfile(p):
                return p
        return sys.executable
    else:
        return sys.executable


def _find_hermes_command():
    if _IS_WIN:
        hermes_exe = os.path.join(
            str(Path.home()), "AppData", "Local", "hermes", "hermes-agent",
            "venv", "Scripts", "hermes.exe"
        )
        if os.path.exists(hermes_exe):
            return hermes_exe
        hermes_which = _which("hermes.exe") or _which("hermes")
        if hermes_which:
            return hermes_which
        return None
    else:
        hermes_path = _which("hermes")
        if hermes_path:
            return hermes_path
        if _IS_MAC:
            venv_hermes = os.path.join(
                str(Path.home()), ".local", "hermes", "hermes-agent",
                "venv", "bin", "hermes"
            )
            if os.path.isfile(venv_hermes):
                return venv_hermes
        if _IS_LINUX:
            venv_hermes = os.path.join(
                str(Path.home()), ".local", "hermes", "hermes-agent",
                "venv", "bin", "hermes"
            )
            if os.path.isfile(venv_hermes):
                return venv_hermes
        return None


def _which(cmd):
    import shutil
    return shutil.which(cmd)


def _get_creationflags():
    if _IS_WIN:
        return 0x08000000
    return 0


def _open_url_in_browser(url):
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
#  Transparent Logo Splash Screen (tkinter)
# ══════════════════════════════════════════
import tkinter as tk


def run_splash():
    BG = "#010101"
    LOGO_SIZE = 280

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg=BG)

    if _IS_WIN:
        root.attributes("-transparentcolor", BG)
    elif _IS_MAC:
        try:
            root.attributes("-alpha", 0.95)
        except Exception:
            pass
    elif _IS_LINUX:
        try:
            root.attributes("-transparentcolor", BG)
        except Exception:
            pass

    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    W, H = 340, 360
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    canvas = tk.Canvas(root, width=W, height=H, bg=BG, highlightthickness=0)
    canvas.pack()

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

    text_bg_y = logo_y + LOGO_SIZE // 2 + 22

    def _draw_rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs):
        import math
        points = []
        cy = (y1 + y2) / 2
        rx = (x2 - x1) / 2
        ry = (y2 - y1) / 2
        cx = (x1 + x2) / 2
        for deg in range(-90, 91, 5):
            rad = math.radians(deg)
            points.append(cx + rx + ry * math.cos(rad))
            points.append(cy + ry * math.sin(rad))
        for deg in range(90, 271, 5):
            rad = math.radians(deg)
            points.append(cx - rx + ry * math.cos(rad))
            points.append(cy + ry * math.sin(rad))
        return canvas.create_polygon(points, smooth=False, **kwargs)

    _splash_font = ("Helvetica", 10)
    if _IS_WIN:
        _splash_font = ("Microsoft YaHei", 10)

    status_id = canvas.create_text(
        W // 2, text_bg_y,
        text="正 在 启 动 ...",
        font=_splash_font, fill="#cccccc", anchor="center"
    )
    root.update()

    def _update_splash_text(text):
        nonlocal text_bg_y
        canvas.itemconfig(status_id, text=text)
        root.update()
        bbox = canvas.bbox(status_id)
        if bbox:
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            pad_x, pad_y = 24, 10
            rx1 = W // 2 - tw // 2 - pad_x
            ry1 = text_bg_y - th // 2 - pad_y
            rx2 = W // 2 + tw // 2 + pad_x
            ry2 = text_bg_y + th // 2 + pad_y
            corner_r = (ry2 - ry1) // 2
            canvas.delete("splash_bg")
            _draw_rounded_rect(canvas, rx1, ry1, rx2, ry2, corner_r,
                               fill="#333333", outline="", stipple="gray50",
                               tags="splash_bg")
            canvas.tag_lower("splash_bg", status_id)

    root.update()

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
    cfg_ok = False
    gw_ok = False

    # 等待服务就绪（最多 8 秒）
    while time.time() - start_time < 8.0:
        elapsed = time.time() - start_time
        if not cfg_ok:
            cfg_ok = _port_ok(18765)
        if not gw_ok:
            gw_ok = _port_ok(8642)

        if cfg_ok and gw_ok:
            _update_splash_text("准 备 就 绪 ✓")
            break
        elif cfg_ok:
            _update_splash_text("网 关 就 绪 ✓")
        elif elapsed > 0.5:
            _update_splash_text("正 在 启 动 ...")

        try:
            root.update()
        except Exception:
            break
        time.sleep(0.05)

    # 淡出特效
    try:
        for i in range(8):
            alpha = 1.0 - (i + 1) / 8.0
            root.attributes("-alpha", max(alpha, 0.0))
            root.update()
            time.sleep(0.05)
    except Exception:
        pass

    try:
        root.destroy()
    except Exception:
        pass


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
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass
    for i in range(30):
        time.sleep(1)
        if _port_alive(18765):
            return


def ensure_gateway():
    if _port_alive(8642):
        return
    for i in range(5):
        time.sleep(1)
        if _port_alive(8642):
            return
    if _IS_WIN:
        hermes_dir = Path.home() / "AppData" / "Local" / "hermes" / "hermes-agent"
        pythonw = hermes_dir / "venv" / "Scripts" / "pythonw.exe"
        if pythonw.exists():
            try:
                subprocess.Popen(
                    [str(pythonw), "-m", "hermes_cli.main", "gateway", "run"],
                    cwd=str(hermes_dir),
                    creationflags=0x08000000,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass
    for i in range(15):
        time.sleep(1)
        if _port_alive(8642):
            return


# ══════════════════════════════════════════
#  Win32 Dark Title Bar (Windows only)
# ══════════════════════════════════════════

def _apply_dark_titlebar(hwnd):
    if not _IS_WIN:
        return
    dwmapi = ctypes.windll.dwmapi
    try:
        dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR,
            ctypes.byref(ctypes.c_int(0x000000)), 4)
    except Exception:
        pass
    try:
        dwmapi.DwmSetWindowAttribute(hwnd, 34,
            ctypes.byref(ctypes.c_int(0x000000)), 4)
    except Exception:
        pass
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

    # ── Single-instance lock ──
    if not _acquire_instance_lock():
        sys.exit(0)

    # Detect screen size
    sw, sh = 1920, 1080
    if _IS_WIN:
        try:
            user32 = ctypes.windll.user32
            sw = user32.GetSystemMetrics(0)
            sh = user32.GetSystemMetrics(1)
        except Exception:
            pass
    else:
        try:
            import tkinter as _tk
            _r = _tk.Tk()
            _r.withdraw()
            sw, sh = _r.winfo_screenwidth(), _r.winfo_screenheight()
            _r.destroy()
        except Exception:
            pass

    win_w, win_h = 1200, 800
    win_x = (sw - win_w) // 2
    win_y = (sh - win_h) // 2

    # 先启动 splash（主线程），同时服务在后台线程启动
    run_splash()

    # splash 结束后，创建窗口并启动 WebView2
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
        if window:
            window.show()
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

    _icon_arg = ICON_TASKBAR if os.path.exists(ICON_TASKBAR) else None
    webview.start(debug=False, icon=_icon_arg)
