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

# ── Win32 constants ──
if _IS_WIN:
    DWMWA_CAPTION_COLOR = 35
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    WS_POPUP = 0x80000000
    WS_EX_TOPMOST = 0x00000008
    WS_EX_TOOLWINDOW = 0x00000080
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_SHOWWINDOW = 0x0040
    HWND_TOPMOST = -1

window = None
tray_icon = None
_minimize_to_tray = False


# ══════════════════════════════════════════
#  Single-instance lock
# ══════════════════════════════════════════
_instance_mutex = None

def _acquire_instance_lock():
    global _instance_mutex
    if not _IS_WIN:
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        _instance_mutex = kernel32.CreateMutexW(None, True, "HermesPulse_SingleInstance")
        if kernel32.GetLastError() == 183:
            return False
        return True
    except Exception:
        return True


# ══════════════════════════════════════════
#  Helpers
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
    return sys.executable


def _get_creationflags():
    return 0x08000000 if _IS_WIN else 0


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
#  Win32 Splash Overlay（不依赖 tkinter）
# ══════════════════════════════════════════

class Win32Splash:
    """用 Win32 API 创建的 splash 覆盖窗口，不占用 tkinter"""

    def __init__(self):
        self.hwnd = None
        self._hbitmap = None
        self._hdc = None

    def show(self, duration=2.0):
        """显示 splash 并等待 duration 秒后自动关闭"""
        if not _IS_WIN:
            return
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        # 获取屏幕尺寸
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)

        # splash 尺寸
        W, H = 340, 360
        x = (sw - W) // 2
        y = (sh - H) // 2

        # 注册窗口类
        WNDCLASS = type('WNDCLASS', (ctypes.Structure,), {
            '_fields_': [
                ('style', ctypes.c_uint), ('lpfnWndProc', ctypes.c_void_p),
                ('cbClsExtra', ctypes.c_int), ('cbWndExtra', ctypes.c_int),
                ('hInstance', ctypes.c_void_p), ('hIcon', ctypes.c_void_p),
                ('hCursor', ctypes.c_void_p), ('hbrBackground', ctypes.c_void_p),
                ('lpszMenuName', ctypes.c_wchar_p), ('lpszClassName', ctypes.c_wchar_p),
            ]
        })

        wc = WNDCLASS()
        wc.style = 0
        wc.lpfnWndProc = 0
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hInstance = user32.GetModuleHandleW(None)
        wc.hIcon = 0
        wc.hCursor = 0
        wc.hbrBackground = 0
        wc.lpszMenuName = None
        wc.lpszClassName = "HermesSplash"

        user32.RegisterClassW(ctypes.byref(wc))

        # 创建 splash 窗口
        self.hwnd = user32.CreateWindowExW(
            WS_EX_TOPMOST | WS_EX_TOOLWINDOW,
            "HermesSplash", "Hermes",
            WS_POPUP,
            x, y, W, H,
            0, 0, wc.hInstance, 0
        )

        if not self.hwnd:
            return

        # 画 logo
        self._draw_logo(W, H)

        # 显示窗口
        user32.ShowWindow(self.hwnd, SWP_SHOWWINDOW)
        user32.UpdateWindow(self.hwnd)

        # 等待指定时间
        time.sleep(duration)

    def _draw_logo(self, W, H):
        """在 splash 窗口上画 logo"""
        if not os.path.exists(LOGO_PNG):
            return
        try:
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32

            hdc = user32.GetDC(self.hwnd)

            # 画黑色背景
            brush = gdi32.CreateSolidBrush(0x000000)
            rect = (ctypes.c_int * 4)(0, 0, W, H)
            gdi32.FillRect(hdc, rect, brush)
            gdi32.DeleteObject(brush)

            # 加载 logo
            from PIL import Image
            pil = Image.open(LOGO_PNG).convert("RGBA")
            pil = pil.resize((280, 280), Image.LANCZOS)

            # 转为 BMP 格式
            bmp = pil.convert("RGB")
            bmp_data = bmp.tobytes()

            BITMAPINFOHEADER = type('BITMAPINFOHEADER', (ctypes.Structure,), {
                '_fields_': [
                    ('biSize', ctypes.c_uint32), ('biWidth', ctypes.c_long),
                    ('biHeight', ctypes.c_long), ('biPlanes', ctypes.c_uint16),
                    ('biBitCount', ctypes.c_uint16), ('biCompression', ctypes.c_uint32),
                    ('biSizeImage', ctypes.c_uint32), ('biXPelsPerMeter', ctypes.c_long),
                    ('biYPelsPerMeter', ctypes.c_long), ('biClrUsed', ctypes.c_uint32),
                    ('biClrImportant', ctypes.c_uint32),
                ]
            })

            bi = BITMAPINFOHEADER()
            bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bi.biWidth = 280
            bi.biHeight = -280  # 负数 = top-down
            bi.biPlanes = 1
            bi.biBitCount = 24
            bi.biCompression = 0

            hbitmap = gdi32.CreateDIBSection(
                hdc, ctypes.byref(bi), 0,
                ctypes.byref(ctypes.c_void_p()), 0, 0
            )

            if hbitmap:
                # 复制像素数据
                mem_dc = gdi32.CreateCompatibleDC(hdc)
                old_bmp = gdi32.SelectObject(mem_dc, hbitmap)
                ctypes.memmove(ctypes.c_void_p(), bmp_data, len(bmp_data))
                gdi32.SelectObject(mem_dc, old_bmp)
                gdi32.DeleteDC(mem_dc)

                # 画到窗口
                logo_x = (W - 280) // 2
                logo_y = (H - 280) // 2 - 25
                gdi32.BitBlt(hdc, logo_x, logo_y, 280, 280, mem_dc, 0, 0, 0x00CC0020)
                gdi32.DeleteObject(hbitmap)

            user32.ReleaseDC(self.hwnd, hdc)
        except Exception:
            pass

    def close(self):
        """关闭 splash 窗口"""
        if self.hwnd and _IS_WIN:
            try:
                ctypes.windll.user32.DestroyWindow(self.hwnd)
            except:
                pass
            self.hwnd = None


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
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
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
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass
    for i in range(15):
        time.sleep(1)
        if _port_alive(8642):
            return


# ══════════════════════════════════════════
#  System Tray
# ══════════════════════════════════════════

def _tray_show(icon, item):
    global window
    if window:
        window.show()

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
#  Dark Title Bar
# ══════════════════════════════════════════

def _apply_dark_titlebar(hwnd):
    if not _IS_WIN:
        return
    dwmapi = ctypes.windll.dwmapi
    try:
        dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR,
            ctypes.byref(ctypes.c_int(0x000000)), 4)
    except: pass
    try:
        dwmapi.DwmSetWindowAttribute(hwnd, 34,
            ctypes.byref(ctypes.c_int(0x000000)), 4)
    except: pass
    try:
        dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(ctypes.c_int(1)), 4)
    except: pass


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
    # 后台启动服务
    threading.Thread(target=ensure_config_server, daemon=True).start()
    threading.Thread(target=ensure_gateway, daemon=True).start()

    if not _acquire_instance_lock():
        sys.exit(0)

    if _IS_WIN:
        # ═══ Windows: 两个状态并行 ═══
        # 1. 创建 webview 窗口（hidden），后台线程启动 WebView2
        # 2. 主线程显示 Win32 splash 覆盖层
        # 3. splash 结束后，关闭覆盖层，显示 webview 窗口

        sw, sh = ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)
        win_w, win_h = 1200, 800
        win_x, win_y = (sw - win_w) // 2, (sh - win_h) // 2

        w = webview.create_window(
            'Hermes', URL,
            x=win_x, y=win_y,
            width=win_w, height=win_h,
            min_size=(800, 600), resizable=True, text_select=True,
            hidden=True, background_color="#000000")
        window = w
        w.events.closing += on_window_close
        _minimize_to_tray = True

        # 后台线程启动 WebView2（预加载页面）
        _icon_arg = ICON_TASKBAR if os.path.exists(ICON_TASKBAR) else None
        def _start_webview():
            webview.start(debug=False, icon=_icon_arg)
        _wv_thread = threading.Thread(target=_start_webview, daemon=True)
        _wv_thread.start()

        # 主线程显示 Win32 splash（2 秒品牌展示）
        splash = Win32Splash()
        splash.show(duration=2.0)
        splash.close()

        # splash 结束，显示 webview 窗口（页面已预加载）
        if window:
            window.show()
        if _IS_WIN:
            def _apply_later():
                for _ in range(50):
                    try:
                        if window.native and window.native.Handle:
                            _apply_dark_titlebar(window.native.Handle.ToInt32())
                            return
                    except: pass
                    time.sleep(0.1)
            threading.Thread(target=_apply_later, daemon=True).start()
        threading.Thread(target=start_tray, daemon=True).start()

        _wv_thread.join()
        os._exit(0)

    else:
        # ═══ macOS / Linux: 简单方案 ═══
        sw, sh = 1920, 1080
        try:
            import tkinter as _tk
            _r = _tk.Tk()
            _r.withdraw()
            sw, sh = _r.winfo_screenwidth(), _r.winfo_screenheight()
            _r.destroy()
        except: pass

        win_w, win_h = 1200, 800
        win_x, win_y = (sw - win_w) // 2, (sh - win_h) // 2

        w = webview.create_window(
            'Hermes', URL,
            x=win_x, y=win_y,
            width=win_w, height=win_h,
            min_size=(800, 600), resizable=True, text_select=True,
            hidden=True, background_color="#000000")
        window = w
        w.events.closing += on_window_close
        _minimize_to_tray = True

        def show_main():
            global window
            if window:
                window.show()
            threading.Thread(target=start_tray, daemon=True).start()

        threading.Thread(target=show_main, daemon=True).start()

        _icon_arg = ICON_TASKBAR if os.path.exists(ICON_TASKBAR) else None
        webview.start(debug=False, icon=_icon_arg)
