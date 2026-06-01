#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hermes Pulse — Native Desktop Client for Hermes Agent
- pywebview 5.4 + WebView2 (Edge Chromium)
- 启动 config_server.py 作为子进程（无黑窗）
- 单实例锁（带进程存活检测）
- 系统托盘（最小化到托盘）
- Splash 启动画面
- 深色标题栏（DWM API）
"""
import sys
import os
import time
import threading
import socket
import subprocess
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

# PyInstaller bundle: use exe directory, not temp extraction dir
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

ICON_TASKBAR = os.path.join(SCRIPT_DIR, "hermes.ico")
LOGO_PNG = os.path.join(SCRIPT_DIR, "hermes-logo.png")
# EXE 模式：config_server 在 PyInstaller 解压目录；源码模式：在 SCRIPT_DIR
if getattr(sys, 'frozen', False):
    _meipass = getattr(sys, '_MEIPASS', SCRIPT_DIR)
    CONFIG_SERVER = os.path.join(_meipass, "config_server.py")
else:
    CONFIG_SERVER = os.path.join(SCRIPT_DIR, "config_server.py")

if _IS_WIN:
    DWMWA_CAPTION_COLOR = 35
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20

window = None
tray_icon = None
_minimize_to_tray = False


def _acquire_instance_lock():
    """Single-instance lock with stale-process recovery."""
    if not _IS_WIN:
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32

        pid_file = os.path.join(SCRIPT_DIR, ".hermes_gui.pid")

        h = kernel32.CreateMutexW(None, True, "HermesPulse_SingleInstance")
        err = kernel32.GetLastError()
        if err == 183:
            alive = False
            my_pid = os.getpid()
            try:
                if os.path.exists(pid_file):
                    with open(pid_file, "r") as f:
                        old_pid = int(f.read().strip())
                    if old_pid == my_pid:
                        alive = True
                    else:
                        PROCESS_QUERY_LIMITED = 0x1000
                        ph = kernel32.OpenProcess(PROCESS_QUERY_LIMITED, False, old_pid)
                        if ph:
                            kernel32.CloseHandle(ph)
                            alive = True
            except Exception:
                pass

            if not alive:
                try:
                    kernel32.CloseHandle(h)
                except Exception:
                    pass
                time.sleep(0.3)
                h = kernel32.CreateMutexW(None, True, "HermesPulse_SingleInstance")
                if kernel32.GetLastError() == 183:
                    return False
                try:
                    with open(pid_file, "w") as f:
                        f.write(str(os.getpid()))
                except Exception:
                    pass
                return True
            else:
                try:
                    user32 = ctypes.windll.user32
                    hwnd = user32.FindWindowW(None, "Hermes")
                    if hwnd:
                        user32.ShowWindow(hwnd, 9)
                        user32.SetForegroundWindow(hwnd)
                except Exception:
                    pass
                return False

        try:
            with open(pid_file, "w") as f:
                f.write(str(os.getpid()))
        except Exception:
            pass
        return True
    except Exception:
        return True


def _get_python_command():
    # EXE 模式（PyInstaller 打包后）→ 用自己跑 config_server
    # 因为 config_server 需要的依赖（claude_agent_sdk / fastapi / uvicorn 等）已经被打进 EXE
    if getattr(sys, 'frozen', False):
        return sys.executable
    # 源码模式 → 找 hermes-agent venv 的 pythonw（装了所有依赖）
    if _IS_WIN:
        candidates = [
            os.path.expandvars(r"%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\pythonw.exe"),
            r"C:\Program Files\Python311\pythonw.exe",
            os.path.join(os.path.dirname(sys.executable), "pythonw.exe"),
            os.path.join(sys.prefix, "pythonw.exe"),
        ]
        for p in candidates:
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
#  Splash HTML
# ══════════════════════════════════════════

def _splash_html():
    """Generate the splash HTML and write it to SCRIPT_DIR/splash.html.

    The splash is then loaded via load_url('file://.../splash.html') instead of
    `html=` parameter. This matters because:

      1. With `html=`, the whole document (including a 2.2MB base64-embedded
         PNG) lives in webview2's renderer memory from t=0, and first-paint
         can be 1-2s late — by which time our splash_min_ms clock has already
         triggered the handoff and the user sees only a black window that
         instantly switches to the main page.

      2. With a real file URL, webview2 streams the HTML, then loads the PNG
         via a separate <img src> fetch — so the page actually shows up
         fast, and the PNG fills in over the next ~200ms. User sees
         "structure → portrait" as a visible sequence, not "nothing → main".

    The splash file is re-generated on every launch (overwriting any prior
    version) so we always pick up the latest code without needing a reinstall.
    """
    splash_html = _splash_html_content()
    splash_path = os.path.join(SCRIPT_DIR, "splash.html")
    try:
        with open(splash_path, "w", encoding="utf-8") as _f:
            _f.write(splash_html)
    except Exception:
        # If we can't write to SCRIPT_DIR, fall back to the in-memory path
        return splash_html
    return splash_html


def _splash_html_content():
    """The actual splash HTML (no base64 PNG — the PNG is loaded via <img src>).

    Pure CSS animations, no JS:
      0.0s  portrait fades in (0.8s, scale 0.92→1)
      0.4s  title "HERMES" fades in
      0.6s  subtitle "轻于形 · 智于心" fades in
      0.5s  progress bar track fades in
      0.0s  bar fillBar 0% → 100% over 2.0s
      0.8s  status "正在准备" fades in (pulses gently)
      2.6s  entire splash fades out (0.8s) — graceful handoff
    """
    return """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{
  background:#000;                     /* 纯黑底 — 看得见 */
  width:100%;height:100%;overflow:hidden;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  color:#fff;
}
body{display:flex;align-items:center;justify-content:center}

/* Stack: portrait (with glow) → title → subtitle → progress bar → status */
.wrap{
  text-align:center;width:100%;max-width:520px;padding:0 24px;
  /* Splash → main handoff timeline (no abrupt cut):
      0.0s  splash content fully visible (logo big, opacity 1)
      2.4s  chrome (title / subtitle / bar / status) starts fading out
      2.5s  logo + halo start a "settle" — shrink from scale 1.0 to 0.85
            (this matches the welcome-screen's "from" scale in welcomeIn),
            opacity 1 → 0
      3.0s  load_url(URL) fires; the main page paints with the welcome
            screen at opacity 0 / scale 0.85, then welcomeIn animates it
            to opacity 1 / scale 1.0 over 0.6s. The eye sees the SAME
            logo, in the SAME place, at the SAME size, dissolving from
            "splash bg + content" into "main UI bg + content". */
  transform-origin:center center;
  animation:wrapSettle 0.5s 2.5s cubic-bezier(0.4,0,0.2,1) forwards;
}
@keyframes wrapSettle{
  0%   {opacity:1;transform:scale(1)}
  100% {opacity:0;transform:scale(0.54)}
}
.bar-track, .status, .title, .sub {
  animation:chromeOut 0.3s 2.4s ease forwards;
}
@keyframes chromeOut{
  to{opacity:0}
}

/* Portrait + halo group — bigger and more dramatic */
.portrait-wrap{
  position:relative;
  width:260px;height:260px;
  margin:0 auto 44px;
  display:flex;align-items:center;justify-content:center;
  animation:portraitIn 1.0s cubic-bezier(0.16,1,0.3,1) both;
}
.portrait{
  width:260px;height:260px;
  object-fit:contain;
  filter:drop-shadow(0 6px 32px rgba(212,175,55,0.22));
  position:relative;z-index:2;
  animation:portraitBreathe 4.5s ease-in-out infinite;
}
.halo{
  position:absolute;
  left:50%;top:50%;
  width:340px;height:340px;
  transform:translate(-50%,-50%);
  border-radius:50%;
  background:radial-gradient(circle,rgba(212,175,55,0.25) 0%,rgba(212,175,55,0.08) 40%,transparent 70%);
  z-index:1;
  animation:haloPulse 3.2s ease-in-out infinite;
}
.halo-ring{
  position:absolute;
  left:50%;top:50%;
  width:300px;height:300px;
  transform:translate(-50%,-50%);
  border-radius:50%;
  border:1px solid rgba(212,175,55,0.18);
  z-index:1;
  animation:ringRotate 18s linear infinite;
}
.halo-ring::before{
  content:"";
  position:absolute;
  top:-3px;left:50%;
  width:6px;height:6px;
  background:#d4af37;
  border-radius:50%;
  transform:translateX(-50%);
  box-shadow:0 0 12px 2px rgba(212,175,55,0.6);
}
@keyframes portraitIn{
  from{opacity:0;transform:translateY(28px) scale(0.88)}
  to{opacity:1;transform:translateY(0) scale(1)}
}
@keyframes portraitBreathe{
  0%,100%{transform:scale(1)}
  50%{transform:scale(1.025)}
}
@keyframes haloPulse{
  0%,100%{opacity:0.5;transform:translate(-50%,-50%) scale(1)}
  50%{opacity:1;transform:translate(-50%,-50%) scale(1.08)}
}
@keyframes ringRotate{
  from{transform:translate(-50%,-50%) rotate(0deg)}
  to{transform:translate(-50%,-50%) rotate(360deg)}
}

/* Title + subtitle */
.title{
  color:#fff;
  font-size:28px;
  font-weight:200;
  letter-spacing:10px;
  margin-bottom:10px;
  animation:titleIn 0.7s 0.4s cubic-bezier(0.16,1,0.3,1) both;
}
.sub{
  color:#7a7a7a;
  font-size:12px;
  letter-spacing:4px;
  margin-bottom:48px;
  animation:titleIn 0.7s 0.6s cubic-bezier(0.16,1,0.3,1) both;
}
@keyframes titleIn{
  from{opacity:0;transform:translateY(10px)}
  to{opacity:1;transform:translateY(0)}
}

/* Progress bar */
.bar-track{
  width:280px;height:1px;
  background:rgba(212,175,55,0.18);
  margin:0 auto 14px;
  position:relative;overflow:hidden;
  border-radius:1px;
  animation:titleIn 0.6s 0.5s cubic-bezier(0.16,1,0.3,1) both;
}
.bar-fill{
  position:absolute;left:0;top:0;
  height:100%;width:0%;
  background:linear-gradient(90deg,transparent 0%,#d4af37 50%,transparent 100%);
  animation:fillBar 2.0s cubic-bezier(0.4,0,0.2,1) forwards;
}
.bar-shimmer{
  position:absolute;top:0;left:-30%;
  width:30%;height:100%;
  background:linear-gradient(90deg,transparent,rgba(212,175,55,0.8),transparent);
  animation:shimmer 1.6s linear infinite;
}
@keyframes fillBar{0%{width:0%}100%{width:100%}}
@keyframes shimmer{0%{left:-30%}100%{left:100%}}

.status{
  color:#4a4a4a;
  font-size:11px;
  letter-spacing:3px;
  min-height:16px;
  font-family:"SF Mono","Consolas",monospace;
  animation:statusFade 2s ease-in-out infinite, titleIn 0.6s 0.8s cubic-bezier(0.16,1,0.3,1) both;
}
@keyframes statusFade{
  0%,100%{opacity:0.5}
  50%{opacity:0.95}
}
</style></head><body>
<div class="wrap">
  <div class="portrait-wrap">
    <div class="halo"></div>
    <div class="halo-ring"></div>
    <img class="portrait" src="hermes-logo.png" alt="Hermes">
  </div>
  <div class="title">HERMES</div>
  <div class="sub">轻于形 · 智于心</div>
  <div class="bar-track"><div class="bar-shimmer"></div><div class="bar-fill"></div></div>
  <div class="status">正在准备</div>
</div>
</body></html>"""


# ══════════════════════════════════════════
#  Services
# ══════════════════════════════════════════

def _run_config_server_inline():
    """EXE 模式：直接在线程里跑 config_server 的 serve_forever（同进程，无子进程）。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("config_server", CONFIG_SERVER)
    if not spec or not spec.loader:
        return False
    cs = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(cs)
    except SystemExit:
        pass
    except Exception as e:
        print(f"[ConfigServer] 加载失败: {e}")
        return False
    # 在新线程跑 ensure_gateway_on_startup（异步，不阻塞）
    if hasattr(cs, "ensure_gateway_on_startup"):
        threading.Thread(target=cs.ensure_gateway_on_startup, daemon=True).start()
    if hasattr(cs, "_gateway_watchdog"):
        threading.Thread(target=cs._gateway_watchdog, daemon=True).start()
    # 在新线程跑 serve_forever
    if hasattr(cs, "ThreadingHTTPServer") and hasattr(cs, "Handler") and hasattr(cs, "PORT"):
        def _serve():
            try:
                server = cs.ThreadingHTTPServer(("127.0.0.1", cs.PORT), cs.Handler)
                print(f"[ConfigServer] listening on 127.0.0.1:{cs.PORT}", flush=True)
                server.serve_forever()
            except Exception as e:
                print(f"[ConfigServer] serve_forever 失败: {e}")
        threading.Thread(target=_serve, daemon=True).start()
        return True
    return False


def ensure_config_server():
    if _port_alive(18765): return
    if getattr(sys, 'frozen', False):
        # EXE 模式：同进程跑 config_server（PyInstaller 子进程找不到文件）
        _run_config_server_inline()
    else:
        # 源码模式：启子进程
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

def start_tray():
    global tray_icon
    try:
        import pystray
        if os.path.exists(ICON_TASKBAR):
            icon_image = PILImage.open(ICON_TASKBAR)
        else:
            from PIL import ImageDraw
            icon_image = PILImage.new('RGBA', (64, 64), (212, 175, 55, 255))
        menu = pystray.Menu(
            pystray.MenuItem("显示", _tray_show, default=True),
            pystray.MenuItem("隐藏", _tray_hide),
            pystray.MenuItem("退出", _tray_exit),
        )
        tray_icon = pystray.Icon("Hermes", icon_image, "Hermes Pulse", menu)
        tray_icon.run()
    except Exception:
        pass


# ══════════════════════════════════════════
#  DWM
# ══════════════════════════════════════════

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
    # EXE 模式：把 stdout/stderr 重定向到用户目录日志文件，方便调试
    if getattr(sys, 'frozen', False):
        try:
            log_dir = Path.home() / "AppData" / "Local" / "Hermes Pulse" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / "hermes_pulse.log"
            log_f = open(log_path, "a", encoding="utf-8", buffering=1)
            sys.stdout = log_f
            sys.stderr = log_f
            print(f"\n=== Hermes Pulse EXE 启动 {time.strftime('%Y-%m-%d %H:%M:%S')} ===", flush=True)
            print(f"sys.executable: {sys.executable}", flush=True)
            print(f"sys._MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}", flush=True)
            print(f"SCRIPT_DIR: {SCRIPT_DIR}", flush=True)
        except Exception as e:
            import traceback
            try:
                with open(Path.home() / "AppData/Local/Hermes Pulse/logs/err.log", "a") as f:
                    f.write(f"log init failed: {e}\n{traceback.format_exc()}\n")
            except: pass

    # Start backend services in background — splash stays visible until both are ready
    threading.Thread(target=ensure_config_server, daemon=True).start()
    threading.Thread(target=ensure_gateway, daemon=True).start()

    if not _acquire_instance_lock():
        sys.exit(0)

    # Screen size for centering
    sw, sh = 1920, 1080
    if _IS_WIN:
        try:
            sw = ctypes.windll.user32.GetSystemMetrics(0)
            sh = ctypes.windll.user32.GetSystemMetrics(1)
        except Exception:
            pass

    win_w, win_h = 1200, 800

    # Write splash.html to SCRIPT_DIR and load it via real file:// URL.
    # Loading a real file (not a base64-blob `html=`) means webview2 actually
    # paints quickly, and the splash is visible to the user.
    _splash_html()  # writes SCRIPT_DIR/splash.html as a side effect
    splash_path = os.path.join(SCRIPT_DIR, "splash.html")
    if os.path.exists(splash_path):
        splash_url = "file:///" + splash_path.replace("\\", "/")
    else:
        # Last-ditch fallback if the write failed: in-memory HTML
        splash_url = _splash_html_content()
    w = webview.create_window('Hermes', url=splash_url,
        x=(sw-win_w)//2, y=(sh-win_h)//2,
        width=win_w, height=win_h,
        min_size=(800, 600), resizable=True, text_select=True,
        background_color="#000000")
    window = w
    w.events.closing += on_window_close
    _minimize_to_tray = True

    def _splash_progress_thread():
        """Drive the splash → main-page handoff with proper timing.

        Timing budget:
          0.0s  splash HTML visible, bar starts filling (CSS @keyframes)
          ~0.3s webview2 first-paint, user actually sees splash
          0.5s+ config_server / gateway come up (EXE mode is fast, source mode slower)
          1.8s  bar reaches 100% (pure CSS)
          2.0s  we call load_url(URL) — instant, but the splash disappears
          →  BUT we want the user to actually see the bar reach 100% AND a graceful
             exit, so we ALWAYS hold splash for >= 2.2s and trigger a 0.45s fade
             by loading a tiny fade-out bridge HTML first (one extra load_url, no
             visual jolt).

        Why >= 2.2s minimum: even if the backend is up at t=0.2s, the user needs
        time to register the brand. < 1.5s feels like a flash and defeats the
        purpose of having a splash.
        """
        global window
        t0 = time.time()
        cs_ready_at = None
        gw_ready_at = None
        _splash_min_ms = 3000   # splash 2.5s 触发 collapse + 0.5s 跑完 = 3.0s 后才切主页

        # Poll services for up to 12s
        for i in range(120):
            cs_ok = _port_alive(18765)
            gw_ok = _port_alive(8642)
            elapsed_ms = int((time.time() - t0) * 1000)
            if cs_ok and cs_ready_at is None:
                cs_ready_at = elapsed_ms
            if gw_ok and gw_ready_at is None:
                gw_ready_at = elapsed_ms

            # Done: both services up AND min brand display elapsed
            if (cs_ready_at is not None and gw_ready_at is not None
                    and elapsed_ms >= _splash_min_ms):
                break
            # Timeout safety: 12s hard cap (give up and just go)
            if elapsed_ms > 12000:
                break
            time.sleep(0.1)

        # The splash has its own CSS-driven fade-out at 2.0s (splash_internal
        # `.wrap` animation: opacity 1 → 0 over 0.6s). By the time we call
        # load_url(URL), webview2 is already showing an empty transparent page,
        # so the navigation to the main chat UI is visually seamless.
        try:
            w.load_url(URL)
        except Exception:
            pass

        # Apply dark titlebar once the real window is up
        if _IS_WIN:
            def _later():
                for _ in range(50):
                    try:
                        if window and window.native and window.native.Handle:
                            _apply_dark_titlebar(window.native.Handle.ToInt32())
                            return
                    except Exception:
                        pass
                    time.sleep(0.1)
            threading.Thread(target=_later, daemon=True).start()

        # Start system tray after main window is up
        threading.Thread(target=start_tray, daemon=True).start()

    threading.Thread(target=_splash_progress_thread, daemon=True).start()

    _icon = ICON_TASKBAR if os.path.exists(ICON_TASKBAR) else None
    webview.start(debug=False, icon=_icon)
