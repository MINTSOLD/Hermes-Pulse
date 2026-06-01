import sys, os, time, threading, socket, subprocess
import platform
from pathlib import Path

if sys.platform == "win32":
    _py311 = r"C:\Program Files\Python311\Lib\site-packages"
    if os.path.isdir(_py311) and _py311 not in sys.path:
        sys.path.insert(0, _py311)

from PIL import Image as PILImage
import webview

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

ctypes = None
if _IS_WIN:
    import ctypes as _ctypes
    ctypes = _ctypes

URL = "http://127.0.0.1:18765/"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_TASKBAR = os.path.join(SCRIPT_DIR, "hermes.ico")
LOGO_PNG = os.path.join(SCRIPT_DIR, "hermes-logo.png")
CONFIG_SERVER = os.path.join(SCRIPT_DIR, "config_server.py")

if _IS_WIN:
    DWMWA_CAPTION_COLOR = 35
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20

window = None
tray_icon = None
_minimize_to_tray = False


def _acquire_instance_lock():
    """Single-instance lock with stale-process recovery.

    Uses a Windows Mutex.  If the mutex already exists (ERROR_ALREADY_EXISTS =
    183), we check whether the owning process is still alive by scanning for a
    matching python/pythonw process whose PID matches our stored PID file.
    If the owner is dead, we clean up and re-acquire.
    """
    if not _IS_WIN:
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32

        # PID file used to verify the mutex owner
        pid_file = os.path.join(SCRIPT_DIR, ".hermes_gui.pid")

        h = kernel32.CreateMutexW(None, True, "HermesPulse_SingleInstance")
        err = kernel32.GetLastError()
        if err == 183:
            # Mutex already held — check if the owner is still alive
            alive = False
            my_pid = os.getpid()
            try:
                if os.path.exists(pid_file):
                    with open(pid_file, "r") as f:
                        old_pid = int(f.read().strip())
                    if old_pid == my_pid:
                        alive = True  # same process, we already hold it
                    else:
                        # Check if process is still running via OpenProcess
                        PROCESS_QUERY_LIMITED = 0x1000
                        ph = kernel32.OpenProcess(PROCESS_QUERY_LIMITED, False, old_pid)
                        if ph:
                            kernel32.CloseHandle(ph)
                            alive = True
            except Exception:
                pass

            if not alive:
                # Stale lock — force-release and re-acquire
                try:
                    kernel32.CloseHandle(h)
                except Exception:
                    pass
                # Small wait for the kernel to clean up
                time.sleep(0.3)
                h = kernel32.CreateMutexW(None, True, "HermesPulse_SingleInstance")
                if kernel32.GetLastError() == 183:
                    return False
                # Write our PID
                try:
                    with open(pid_file, "w") as f:
                        f.write(str(os.getpid()))
                except Exception:
                    pass
                return True
            else:
                return False

        # Fresh lock acquired — write our PID
        try:
            with open(pid_file, "w") as f:
                f.write(str(os.getpid()))
        except Exception:
            pass
        return True
    except Exception:
        return True


def _get_python_command():
    if _IS_WIN:
        for p in [r"C:\Program Files\Python311\pythonw.exe",
                   os.path.join(os.path.dirname(sys.executable), "pythonw.exe"),
                   os.path.join(sys.prefix, "pythonw.exe")]:
            if os.path.isfile(p):
                return p
        return sys.executable
    return sys.executable


def _port_alive(port, timeout=1):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except:
        return False
    finally:
        s.close()


# ══════════════════════════════════════════
#  Quick Splash (tkinter, 1.5s brand display)
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
        try: root.attributes("-alpha", 0.95)
        except: pass
    elif _IS_LINUX:
        try: root.attributes("-transparentcolor", BG)
        except: pass

    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    W, H = 340, 360
    x, y = (sw - W) // 2, (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")
    canvas = tk.Canvas(root, width=W, height=H, bg=BG, highlightthickness=0)
    canvas.pack()

    logo_y = H // 2 - 25
    if os.path.exists(LOGO_PNG):
        try:
            pil = PILImage.open(LOGO_PNG).convert("RGBA")
            pil = pil.resize((LOGO_SIZE, LOGO_SIZE), PILImage.LANCZOS)
            from PIL import ImageTk
            logo_tk = ImageTk.PhotoImage(pil)
            canvas.create_image(W // 2, logo_y, image=logo_tk, anchor="center")
        except: pass

    root.update()
    time.sleep(1.5)  # 品牌展示 1.5 秒

    # 淡出 0.3 秒
    try:
        for i in range(6):
            root.attributes("-alpha", 1.0 - (i + 1) / 6.0)
            root.update()
            time.sleep(0.05)
    except: pass

    try: root.destroy()
    except: pass


# ══════════════════════════════════════════
#  Services
# ══════════════════════════════════════════

def ensure_config_server():
    if _port_alive(18765): return
    try:
        subprocess.Popen([_get_python_command(), CONFIG_SERVER],
            creationflags=0x08000000 if _IS_WIN else 0,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass
    for _ in range(30):
        time.sleep(1)
        if _port_alive(18765): return

def ensure_gateway():
    if _port_alive(8642): return
    for _ in range(5):
        time.sleep(1)
        if _port_alive(8642): return
    if _IS_WIN:
        pw = Path.home() / "AppData/Local/hermes/hermes-agent/venv/Scripts/pythonw.exe"
        if pw.exists():
            try:
                subprocess.Popen([str(pw), "-m", "hermes_cli.main", "gateway", "run"],
                    cwd=str(pw.parent.parent.parent),
                    creationflags=0x08000000,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except: pass
    for _ in range(15):
        time.sleep(1)
        if _port_alive(8642): return


# ══════════════════════════════════════════
#  System Tray
# ══════════════════════════════════════════

def _tray_show(icon, item):
    global window
    if window: window.show()

def _tray_hide(icon, item):
    global window
    if window: window.hide()

def _tray_exit(icon, item):
    global _minimize_to_tray
    _minimize_to_tray = False
    if window: window.destroy()
    if tray_icon: tray_icon.stop()
    os._exit(0)

def start_tray():
    global tray_icon
    import pystray
    icon_image = None
    if os.path.exists(ICON_TASKBAR):
        try: icon_image = PILImage.open(ICON_TASKBAR)
        except: pass
    if not icon_image:
        icon_image = PILImage.new("RGB", (16, 16), (212, 175, 55))
    menu = pystray.Menu(
        pystray.MenuItem("显示 Hermes", _tray_show, default=True),
        pystray.MenuItem("隐藏 Hermes", _tray_hide),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", _tray_exit))
    tray_icon = pystray.Icon("Hermes", icon_image, "Hermes Pulse", menu)
    tray_icon.run()


def _apply_dark_titlebar(hwnd):
    if not _IS_WIN: return
    dwmapi = ctypes.windll.dwmapi
    try: dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(ctypes.c_int(0)), 4)
    except: pass
    try: dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(ctypes.c_int(0)), 4)
    except: pass
    try: dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(ctypes.c_int(1)), 4)
    except: pass

def on_window_close():
    global window, _minimize_to_tray
    if _minimize_to_tray:
        window.hide()
        return False
    return True


# ══════════════════════════════════════════
#  Main
# ══════════════════════════════════════════

if __name__ == '__main__':
    threading.Thread(target=ensure_config_server, daemon=True).start()
    threading.Thread(target=ensure_gateway, daemon=True).start()

    if not _acquire_instance_lock():
        sys.exit(0)

    # Splash（1.5 秒品牌展示 + 0.3 秒淡出）
    run_splash()

    # 直接创建窗口并启动
    sw, sh = 1920, 1080
    if _IS_WIN:
        try:
            sw = ctypes.windll.user32.GetSystemMetrics(0)
            sh = ctypes.windll.user32.GetSystemMetrics(1)
        except: pass

    win_w, win_h = 1200, 800
    w = webview.create_window('Hermes', URL,
        x=(sw-win_w)//2, y=(sh-win_h)//2,
        width=win_w, height=win_h,
        min_size=(800, 600), resizable=True, text_select=True,
        hidden=True, background_color="#000000")
    window = w
    w.events.closing += on_window_close
    _minimize_to_tray = True

    def show_main():
        global window
        if window: window.show()
        if _IS_WIN:
            def _later():
                for _ in range(50):
                    try:
                        if window.native and window.native.Handle:
                            _apply_dark_titlebar(window.native.Handle.ToInt32())
                            return
                    except: pass
                    time.sleep(0.1)
            threading.Thread(target=_later, daemon=True).start()
        threading.Thread(target=start_tray, daemon=True).start()

    threading.Thread(target=show_main, daemon=True).start()

    _icon = ICON_TASKBAR if os.path.exists(ICON_TASKBAR) else None
    webview.start(debug=False, icon=_icon)
