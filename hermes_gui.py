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
ICON_TITLEBAR = os.path.join(SCRIPT_DIR, "hermes-titlebar.ico")
LOGO_PNG = os.path.join(SCRIPT_DIR, "hermes-logo.png")
CONFIG_SERVER = os.path.join(SCRIPT_DIR, "config_server.py")

# ── Win32 constants (only used on Windows) ──
if _IS_WIN:
    WM_SETICON = 0x0080
    GWL_EXSTYLE = -20
    WS_EX_DLGMODALFRAME = 0x00000001
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_FRAMECHANGED = 0x0020
    DWMWA_CAPTION_COLOR = 35

window = None
tray_icon = None
_minimize_to_tray = False


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

    # Semi-transparent dark bg + white status text
    text_bg_y = logo_y + LOGO_SIZE // 2 + 22
    canvas.create_rectangle(
        W // 2 - 70, text_bg_y - 14,
        W // 2 + 70, text_bg_y + 14,
        fill="#333333", outline="", stipple="gray50"
    )

    # Use cross-platform font: fallback from Microsoft YaHei to system default
    _splash_font = ("Helvetica", 10)
    if _IS_WIN:
        _splash_font = ("Microsoft YaHei", 10)

    status_id = canvas.create_text(
        W // 2, text_bg_y,
        text="正 在 启 动 ...",
        font=_splash_font, fill="#cccccc", anchor="center"
    )

    root.update()

    # Fixed 3-second splash with time-based status updates
    start_time = time.time()
    status_texts = [
        (0.0, "正 在 启 动 ..."),
        (1.0, "配 置 服 务 就 绪"),
        (2.0, "准 备 就 绪"),
    ]
    text_idx = 0

    while time.time() - start_time < 3.0:
        elapsed = time.time() - start_time
        while text_idx < len(status_texts) and elapsed >= status_texts[text_idx][0]:
            try:
                canvas.itemconfig(status_id, text=status_texts[text_idx][1])
            except Exception:
                break
            text_idx += 1
        try:
            root.update()
        except Exception:
            break
        time.sleep(0.05)

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
    if _port_alive(8642):
        return
    hermes_cmd = _find_hermes_command()
    if not hermes_cmd:
        return
    try:
        kwargs = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if _IS_WIN:
            kwargs["creationflags"] = 0x08000000
        subprocess.Popen([hermes_cmd, "gateway", "start"], **kwargs)
    except Exception:
        pass
    for i in range(20):
        time.sleep(1)
        if _port_alive(8642):
            return


# ══════════════════════════════════════════
#  Win32 Window Styling (Windows only)
# ══════════════════════════════════════════

def _set_icon_on_hwnd(hwnd):
    """Apply dark title bar + icons to the pywebview HWND (Windows only)."""
    if not _IS_WIN:
        return
    user32 = ctypes.windll.user32
    dwmapi = ctypes.windll.dwmapi
    try:
        dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR,
            ctypes.byref(ctypes.c_int(0x000000)), 4)
    except Exception:
        pass
    try:
        dwmapi.DwmSetWindowAttribute(hwnd, 20,
            ctypes.byref(ctypes.c_int(1)), 4)
    except Exception:
        pass
    try:
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_DLGMODALFRAME
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    except Exception:
        pass
    try:
        if os.path.exists(ICON_TITLEBAR):
            h = user32.LoadImageW(0, ICON_TITLEBAR, 1, 0, 0, 0x0010)
            if h:
                user32.SendMessageW(hwnd, WM_SETICON, 0, h)
    except Exception:
        pass
    try:
        if os.path.exists(ICON_TASKBAR):
            h = user32.LoadImageW(0, ICON_TASKBAR, 1, 0, 0, 0x0010)
            if h:
                user32.SendMessageW(hwnd, WM_SETICON, 1, h)
    except Exception:
        pass
    try:
        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | 0x0004 | SWP_FRAMECHANGED)
    except Exception:
        pass


def _find_hwnd_by_title(title, retries=50, interval=0.1):
    """Find a Win32 HWND by window title (Windows only)."""
    if not _IS_WIN:
        return None
    user32 = ctypes.windll.user32
    for _ in range(retries):
        time.sleep(interval)
        hwnd = user32.FindWindowW(None, title)
        if hwnd:
            return hwnd
    return None


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
        # Windows: apply dark title bar + icons via Win32 API
        if _IS_WIN:
            hwnd = _find_hwnd_by_title('Hermes', retries=100, interval=0.1)
            if hwnd:
                _set_icon_on_hwnd(hwnd)
        if window:
            window.show()
        threading.Thread(target=start_tray, daemon=True).start()

    threading.Thread(target=show_main, daemon=True).start()

    webview.start(debug=False)
    os._exit(0)
