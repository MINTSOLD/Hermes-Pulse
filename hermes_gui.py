import sys, os, ctypes, time, threading, socket, subprocess
from pathlib import Path
sys.path.insert(0, r'C:\Program Files\Python311\Lib\site-packages')
from PIL import Image as PILImage
import webview

URL = "http://127.0.0.1:18765/"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_TASKBAR = os.path.join(SCRIPT_DIR, "hermes.ico")
ICON_TITLEBAR = os.path.join(SCRIPT_DIR, "hermes-titlebar.ico")
LOGO_PNG = os.path.join(SCRIPT_DIR, "hermes-logo.png")
PYTHONW = r"C:\Program Files\Python311\pythonw.exe"
CONFIG_SERVER = os.path.join(SCRIPT_DIR, "config_server.py")

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
#  启动画面 — 透明底，140px Logo 居中 + 状态文字
# ══════════════════════════════════════════
import tkinter as tk

def run_splash():
    """透明底小窗：Logo 居中 + 状态文字。返回屏幕中心坐标。"""
    BG = "#010101"

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg=BG)
    root.attributes("-transparentcolor", BG)

    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()

    # 窗口大小：Logo(140) + 间距(30) + 状态文字(20) = 190，取 220
    W, H = 240, 220
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    canvas = tk.Canvas(root, width=W, height=H, bg=BG, highlightthickness=0)
    canvas.pack()

    # Logo 居中
    logo_tk = None
    logo_y = H // 2 - 15  # 稍偏上，给状态文字留空间
    if os.path.exists(LOGO_PNG):
        try:
            pil = PILImage.open(LOGO_PNG).convert("RGBA")
            pil = pil.resize((140, 140), PILImage.LANCZOS)
            from PIL import ImageTk
            logo_tk = ImageTk.PhotoImage(pil)
            canvas.create_image(W // 2, logo_y, image=logo_tk, anchor="center")
        except:
            pass

    # 状态文字
    status_id = canvas.create_text(
        W // 2, logo_y + 70 + 25,  # Logo 底部 + 间距
        text="正在启动...",
        font=("Segoe UI", 9), fill="#666666", anchor="center"
    )

    root.update()

    # 等服务
    def wait_for_services():
        for _ in range(30):
            if _port_alive(18765):
                break
            try:
                canvas.itemconfig(status_id, text="启动配置服务...")
                root.update()
            except:
                return
            time.sleep(1)
        try:
            canvas.itemconfig(status_id, text="配置服务就绪")
            root.update()
        except:
            return
        for _ in range(20):
            if _port_alive(8642):
                break
            try:
                canvas.itemconfig(status_id, text="启动 Gateway...")
                root.update()
            except:
                return
            time.sleep(1)
        try:
            canvas.itemconfig(status_id, text="准备就绪")
            root.update()
        except:
            return
        for _ in range(4):
            try:
                root.update()
            except:
                return
            time.sleep(0.25)

    wait_for_services()
    cx, cy = sw // 2, sh // 2
    try:
        root.destroy()
    except:
        pass
    return cx, cy


# ══════════════════════════════════════════
#  系统托盘
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
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, "Hermes")
        if hwnd:
            user32.SetForegroundWindow(hwnd)
            user32.ShowWindow(hwnd, 9)
    except:
        pass

def start_tray():
    global tray_icon
    import pystray
    icon_image = None
    if os.path.exists(ICON_TASKBAR):
        try:
            icon_image = PILImage.open(ICON_TASKBAR)
        except:
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
#  后台服务
# ══════════════════════════════════════════
def ensure_config_server():
    if _port_alive(18765):
        return
    subprocess.Popen([PYTHONW, CONFIG_SERVER])
    for i in range(30):
        time.sleep(1)
        if _port_alive(18765):
            return

def ensure_gateway():
    if _port_alive(8642):
        return
    hermes_exe = os.path.join(
        str(Path.home()), "AppData", "Local", "hermes", "hermes-agent",
        "venv", "Scripts", "hermes.exe"
    )
    if not os.path.exists(hermes_exe):
        return
    try:
        subprocess.Popen(
            [hermes_exe, "gateway", "start"],
            creationflags=0x08000000,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except:
        pass
    for i in range(20):
        time.sleep(1)
        if _port_alive(8642):
            return


# ══════════════════════════════════════════
#  窗口图标
# ══════════════════════════════════════════
def _set_icon_on_hwnd(hwnd):
    user32 = ctypes.windll.user32
    dwmapi = ctypes.windll.dwmapi
    try:
        dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR,
            ctypes.byref(ctypes.c_int(0x000000)), 4)
    except: pass
    try:
        dwmapi.DwmSetWindowAttribute(hwnd, 20,
            ctypes.byref(ctypes.c_int(1)), 4)
    except: pass
    try:
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_DLGMODALFRAME
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    except: pass
    try:
        if os.path.exists(ICON_TITLEBAR):
            h = user32.LoadImageW(0, ICON_TITLEBAR, 1, 0, 0, 0x0010)
            if h:
                user32.SendMessageW(hwnd, WM_SETICON, 0, h)
    except: pass
    try:
        if os.path.exists(ICON_TASKBAR):
            h = user32.LoadImageW(0, ICON_TASKBAR, 1, 0, 0, 0x0010)
            if h:
                user32.SendMessageW(hwnd, WM_SETICON, 1, h)
    except: pass
    try:
        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | 0x0004 | SWP_FRAMECHANGED)
    except: pass


def _find_hwnd_by_title(title, retries=50, interval=0.1):
    user32 = ctypes.windll.user32
    for _ in range(retries):
        time.sleep(interval)
        hwnd = user32.FindWindowW(None, title)
        if hwnd:
            return hwnd
    return None


def on_window_close():
    global window, _minimize_to_tray
    if _minimize_to_tray:
        window.hide()
        return False
    return True


# ══════════════════════════════════════════
#  主流程
# ══════════════════════════════════════════
if __name__ == '__main__':
    threading.Thread(target=ensure_config_server, daemon=True).start()
    threading.Thread(target=ensure_gateway, daemon=True).start()

    # 启动画面：Logo 居中 + 状态文字
    splash_cx, splash_cy = run_splash()

    # 主窗口：居中，黑色背景
    win_w, win_h = 1200, 800
    win_x = splash_cx - win_w // 2
    win_y = splash_cy - win_h // 2

    w = webview.create_window(
        'Hermes', URL,
        x=win_x, y=win_y,
        width=win_w, height=win_h,
        min_size=(800, 600),
        resizable=True, text_select=True, hidden=True,
        background_color="#000000")
    window = w
    w.events.closing += on_window_close
    _minimize_to_tray = True

    def show_main():
        global window
        hwnd = _find_hwnd_by_title('Hermes', retries=100, interval=0.1)
        if hwnd:
            _set_icon_on_hwnd(hwnd)
        if window:
            window.show()
        threading.Thread(target=start_tray, daemon=True).start()

    threading.Thread(target=show_main, daemon=True).start()

    webview.start(debug=False)
    os._exit(0)
