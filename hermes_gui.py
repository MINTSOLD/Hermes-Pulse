import sys, os, ctypes, time, threading, socket, subprocess
from pathlib import Path
sys.path.insert(0, r'C:\Program Files\Python311\Lib\site-packages')
import webview

URL = "http://127.0.0.1:18765/"
ICON_TASKBAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hermes.ico")
ICON_TITLEBAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hermes-titlebar.ico")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHONW = r"C:\Program Files\Python311\pythonw.exe"
CONFIG_SERVER = os.path.join(SCRIPT_DIR, "config_server.py")

WM_SETICON = 0x0080
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_EX_DLGMODALFRAME = 0x00000001
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_FRAMECHANGED = 0x0020
DWMWA_CAPTION_COLOR = 35

def _port_alive(port, timeout=1):
    """检测端口是否有进程在监听"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except:
        return False
    finally:
        s.close()

def ensure_config_server():
    """检查 config_server 是否在运行，没有则启动"""
    if _port_alive(18765):
        return  # 已经在运行
    subprocess.Popen([PYTHONW, CONFIG_SERVER])
    for _ in range(30):
        time.sleep(1)
        if _port_alive(18765):
            return

def ensure_gateway():
    """检查 Gateway 是否在运行，没有则通过 hermes CLI 启动"""
    if _port_alive(8642):
        return  # 已经在运行
    hermes_exe = os.path.join(
        str(Path.home()), "AppData", "Local", "hermes", "hermes-agent",
        "venv", "Scripts", "hermes.exe"
    )
    if not os.path.exists(hermes_exe):
        return  # hermes 未安装，跳过
    try:
        subprocess.Popen(
            [hermes_exe, "gateway", "start"],
            creationflags=0x08000000,  # CREATE_NO_WINDOW
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except:
        pass
    # 等待 Gateway 就绪（最多 20 秒）
    for _ in range(20):
        time.sleep(1)
        if _port_alive(8642):
            return

def _set_icon_on_hwnd(hwnd):
    """对指定窗口句柄设置图标和样式"""
    user32 = ctypes.windll.user32
    dwmapi = ctypes.windll.dwmapi
    # 标题栏黑色
    try:
        dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(ctypes.c_int(0x000000)), 4)
    except: pass
    # 暗色标题栏
    try:
        dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)
    except: pass
    # 去掉默认图标
    try:
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_DLGMODALFRAME
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    except: pass
    # 设置标题栏图标
    try:
        if os.path.exists(ICON_TITLEBAR):
            h = user32.LoadImageW(0, ICON_TITLEBAR, 1, 0, 0, 0x0010)
            if h:
                user32.SendMessageW(hwnd, WM_SETICON, 0, h)
    except: pass
    # 设置任务栏图标
    try:
        if os.path.exists(ICON_TASKBAR):
            h = user32.LoadImageW(0, ICON_TASKBAR, 1, 0, 0, 0x0010)
            if h:
                user32.SendMessageW(hwnd, WM_SETICON, 1, h)
    except: pass
    # 强制重绘边框
    try:
        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)
    except: pass

def _find_hwnd_by_title(title, retries=50, interval=0.1):
    """按窗口标题查找句柄"""
    user32 = ctypes.windll.user32
    for _ in range(retries):
        time.sleep(interval)
        hwnd = user32.FindWindowW(None, title)
        if hwnd:
            return hwnd
    return None

def apply_icon_and_show():
    """找到窗口 → 设图标 → 显示，确保用户看不到 Python 图标"""
    hwnd = _find_hwnd_by_title('Hermes')
    if hwnd:
        _set_icon_on_hwnd(hwnd)
    # 显示窗口
    if w:
        w.show()

if __name__ == '__main__':
    ensure_config_server()
    ensure_gateway()
    w = webview.create_window(
        'Hermes', URL,
        width=1200, height=800, min_size=(800, 600),
        resizable=True, text_select=True, hidden=True)
    threading.Thread(target=apply_icon_and_show, daemon=True).start()
    webview.start(debug=False)
    os._exit(0)
