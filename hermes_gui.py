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
  background:#000;
  width:100%;height:100%;overflow:hidden;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  color:#fff;
  position:relative;
}
body{display:flex;align-items:center;justify-content:center;position:relative;z-index:1;}

/* ══════════════════════════════════════════
   Hex Grid Background — animated + breathing
   ══════════════════════════════════════════ */
.hex-grid{
  position:fixed;inset:0;
  background-image:
    linear-gradient(30deg,  transparent 49%, rgba(212,175,55,0.06) 49%, rgba(212,175,55,0.06) 51%, transparent 51%),
    linear-gradient(150deg, transparent 49%, rgba(212,175,55,0.06) 49%, rgba(212,175,55,0.06) 51%, transparent 51%),
    linear-gradient(90deg,  transparent 49%, rgba(212,175,55,0.04) 49%, rgba(212,175,55,0.04) 51%, transparent 51%),
    linear-gradient(210deg, transparent 49%, rgba(212,175,55,0.04) 49%, rgba(212,175,55,0.04) 51%, transparent 51%);
  background-size:60px 104px;
  background-position:0 0, 0 0, 30px 52px, 30px 52px;
  -webkit-mask-image:radial-gradient(ellipse at center, #000 30%, transparent 80%);
  mask-image:radial-gradient(ellipse at center, #000 30%, transparent 80%);
  animation:hexDrift 30s linear infinite;
  opacity:0.7;
  z-index:0;
}
@keyframes hexDrift{
  0%   {background-position:0 0, 0 0, 30px 52px, 30px 52px;}
  100% {background-position:60px 104px, 60px 104px, 90px 156px, 90px 156px;}
}

/* Scanline sweep — full-width moving band */
.scanline{
  position:fixed;left:0;right:0;height:80px;
  background:linear-gradient(180deg,
    transparent 0%, rgba(212,175,55,0.04) 50%, transparent 100%);
  top:0;z-index:1;pointer-events:none;
  animation:scanY 4s linear infinite;
}
@keyframes scanY{
  0%   {transform:translateY(-80px)}
  100% {transform:translateY(100vh)}
}
/* Faint horizontal CRT lines (top fixed) */
.crt-lines{
  position:fixed;inset:0;z-index:1;pointer-events:none;
  background:repeating-linear-gradient(
    to bottom,
    transparent 0,
    transparent 2px,
    rgba(255,255,255,0.012) 2px,
    rgba(255,255,255,0.012) 3px);
  mix-blend-mode:overlay;
}

/* Vignette */
.vignette{
  position:fixed;inset:0;z-index:1;pointer-events:none;
  background:radial-gradient(ellipse at center,
    transparent 40%, rgba(0,0,0,0.6) 100%);
}

/* Floating matrix particles */
.particles{position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden;}
.particle{
  position:absolute;width:1px;height:1px;
  background:rgba(212,175,55,0.6);
  box-shadow:0 0 4px 1px rgba(212,175,55,0.4);
  animation:particleFloat linear infinite;
}
@keyframes particleFloat{
  0%   {transform:translateY(100vh) translateX(0);opacity:0;}
  10%  {opacity:1;}
  90%  {opacity:1;}
  100% {transform:translateY(-10vh) translateX(40px);opacity:0;}
}

/* ══════════════════════════════════════════
   Main stack
   ══════════════════════════════════════════ */
.wrap{
  text-align:center;width:100%;max-width:520px;padding:0 24px;
  position:relative;z-index:2;
  animation:wrapOut 0.8s 2.4s cubic-bezier(0.4,0,0.2,1) forwards;
}
@keyframes wrapOut{
  0%   {opacity:1;transform:scale(1);filter:blur(0px)}
  100% {opacity:0;transform:scale(1.1);filter:blur(8px)}
}
.splash-center-fix { margin-top: -20px; }

/* corner brackets (HUD frame) */
.hud-bracket{
  position:absolute;width:24px;height:24px;
  border:1px solid rgba(212,175,55,0.4);
  pointer-events:none;
}
.hud-bracket.tl{top:-32px;left:50%;transform:translateX(-160px);border-right:0;border-bottom:0;}
.hud-bracket.tr{top:-32px;left:50%;transform:translateX(136px);border-left:0;border-bottom:0;}
.hud-bracket.bl{bottom:-32px;left:50%;transform:translateX(-160px);border-right:0;border-top:0;}
.hud-bracket.br{bottom:-32px;left:50%;transform:translateX(136px);border-left:0;border-top:0;}
.hud-bracket.bl,.hud-bracket.br{animation:hudPulse 2.5s 1.5s ease-in-out infinite alternate;}
@keyframes hudPulse{
  0%   {border-color:rgba(212,175,55,0.3)}
  100% {border-color:rgba(212,175,55,0.7)}
}

/* Tech startup rings — 6-ring multi-track + orbital particles */
.tech-wrap{
  position:relative;width:160px;height:160px;
  margin:0 auto 36px;
}
/* Outer pulsing aura */
.tech-aura{
  position:absolute;inset:-30px;border-radius:50%;
  background:radial-gradient(circle,rgba(212,175,55,0.18) 0%,transparent 65%);
  animation:auraPulse 3s ease-in-out infinite;
}
@keyframes auraPulse{
  0%,100%{opacity:0.5;transform:scale(0.95);}
  50%   {opacity:1;transform:scale(1.05);}
}
.tech-ring{
  position:absolute;border-radius:50%;
  top:50%;left:50%;transform:translate(-50%,-50%);
}
.tech-ring-outer{width:160px;height:160px;border:1px solid rgba(212,175,55,0.1);
  animation:techSpin 14s linear infinite;}
.tech-ring-r1{width:140px;height:140px;border:1px dashed rgba(212,175,55,0.18);
  animation:techSpin 9s linear infinite reverse;}
.tech-ring-r2{width:118px;height:118px;border:1px solid rgba(212,175,55,0.32);
  border-top-color:rgba(212,175,55,0.8);border-bottom-color:transparent;
  animation:techSpin 6s linear infinite;}
.tech-ring-mid{width:96px;height:96px;border:1px solid rgba(212,175,55,0.4);
  border-right-color:transparent;
  animation:techSpin 4s linear infinite reverse;}
.tech-ring-r3{width:74px;height:74px;border:1px solid rgba(212,175,55,0.18);
  animation:techSpin 2.4s linear infinite;}
.tech-ring-inner{width:48px;height:48px;border:1.5px solid rgba(212,175,55,0.6);
  animation:techSpin 1.6s linear infinite reverse;
  box-shadow:inset 0 0 12px rgba(212,175,55,0.3);
}
/* Core glow center */
.tech-core{
  position:absolute;width:14px;height:14px;border-radius:50%;
  top:50%;left:50%;transform:translate(-50%,-50%);
  background:#d4af37;
  box-shadow:0 0 16px 4px rgba(212,175,55,0.7),
             0 0 32px 8px rgba(212,175,55,0.3);
  animation:corePulse 1.5s ease-in-out infinite;
  z-index:3;
}
@keyframes corePulse{
  0%,100%{transform:translate(-50%,-50%) scale(0.85);opacity:0.7;}
  50%   {transform:translate(-50%,-50%) scale(1.15);opacity:1;}
}
/* Orbital particles on rings */
.tech-dot{
  position:absolute;width:5px;height:5px;
  background:#d4af37;border-radius:50%;
  box-shadow:0 0 10px 2px rgba(212,175,55,0.6);
}
.tech-dot-outer{top:-2.5px;left:50%;transform:translateX(-50%);}
.tech-dot-mid{top:50%;right:-2.5px;transform:translateY(-50%);}
.tech-dot-inner{top:-2.5px;left:50%;transform:translateX(-50%);}
/* Additional 3 orbital particles at different positions */
.tech-dot-r1{bottom:15%;right:8%;}
.tech-dot-r2{top:20%;left:8%;}
.tech-dot-r3{top:50%;left:-2.5px;transform:translateY(-50%);}
/* Scanline that sweeps across the rings */
.tech-scan{
  position:absolute;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(212,175,55,0.7),transparent);
  top:50%;pointer-events:none;
  animation:techScan 2.5s ease-in-out infinite alternate;
  z-index:2;
}
@keyframes techScan{
  0%   {transform:translateY(-70px);opacity:0;}
  20%  {opacity:1;}
  80%  {opacity:1;}
  100% {transform:translateY(70px);opacity:0;}
}
/* Scanning crosshair — HUD overlay */
.tech-cross{position:absolute;width:100px;height:100px;top:50%;left:50%;
  transform:translate(-50%,-50%) rotate(0deg);
  animation:crossSpin 20s linear infinite;
  pointer-events:none;
  z-index:1;
}
.tech-cross::before,.tech-cross::after{
  content:'';position:absolute;background:rgba(212,175,55,0.08);
}
.tech-cross::before{width:1px;height:100%;left:50%;transform:translateX(-50%);}
.tech-cross::after{width:100%;height:1px;top:50%;transform:translateY(-50%);}
@keyframes techSpin{to{transform:translate(-50%,-50%) rotate(360deg)}}
@keyframes crossSpin{to{transform:translate(-50%,-50%) rotate(360deg)}}
/* Stage 1: full "loading" UI — visible at t=0, fades out at t=2.5s */
.splash-loading { animation: stage1Out 0.6s 2.5s ease forwards; }
@keyframes stage1Out {
  0%   { opacity: 1; transform: scale(1); }
  100% { opacity: 0; transform: scale(1.08); filter: blur(4px); }
}
/* Stage 2: a static "main UI mock" (welcome screen). Hidden at t=0,
   fades in at t=2.7s and stays visible. The eye sees the splash's
   "loading" content morph into the main UI's welcome screen — same
   logo size, same layout, same colors — without any cross-document
   cut. At t=4.5s Python calls load_url(URL) to swap in the real
   webview2 main page, but since the mock and the real page look
   identical at the handoff, the user perceives one continuous UI. */
.splash-mock {
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  opacity: 0; transform: scale(0.96);
  animation: stage2In 0.8s 2.7s cubic-bezier(0.16,1,0.3,1) forwards;
}
@keyframes stage2In {
  0%   { opacity: 0; transform: scale(0.96); filter: blur(8px); }
  100% { opacity: 1; transform: scale(1);    filter: blur(0);   }
}
/* Same layout as the real main UI: toolbar (48px) → chat center → input. */
.splash-mock-toolbar {
  flex-shrink: 0; height: 48px;
  background: linear-gradient(180deg, #0a0a0a 0%, #000 100%);
  border-bottom: 1px solid rgba(255,255,255,0.06);
  opacity: 0; animation: mockChromeIn 0.5s 2.9s ease forwards;
}
.splash-mock-center {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  margin-top: -20px;
}
.splash-mock-input {
  flex-shrink: 0; height: 100px;
  background: linear-gradient(0deg, #0a0a0a 0%, #000 100%);
  border-top: 1px solid rgba(255,255,255,0.06);
  opacity: 0; animation: mockChromeIn 0.5s 2.9s ease forwards;
}
@keyframes mockChromeIn { to { opacity: 1; } }
.splash-mock-logo { width: 140px; height: 140px; object-fit: contain;
  filter: drop-shadow(0 4px 16px rgba(212,175,55,0.18));
  animation: mockLogoBreathe 4.5s ease-in-out infinite; }
@keyframes mockLogoBreathe {
  0%,100%{transform:scale(1)}
  50%{transform:scale(1.025)}
}
.splash-mock h1 { color: var(--text-muted); font-size: 24px; font-weight: 500; margin-top: 24px; margin-bottom: 8px; letter-spacing: 0.5px; }
.splash-mock-tag { color: var(--text-muted); font-size: 14px; opacity: 0.6; margin-bottom: 32px; letter-spacing: 4px; }
.splash-mock-status { color: var(--text-muted); font-size: 12px; opacity: 0.5; }

/* Title with typewriter reveal + glitch */
.title{
  font-size:32px;
  font-weight:300;
  letter-spacing:12px;
  margin-bottom:6px;
  font-family:"SF Mono","Consolas",monospace;
  background:linear-gradient(90deg,
    rgba(212,175,55,0.4) 0%,
    rgba(255,255,255,0.95) 25%,
    rgba(212,175,55,0.95) 50%,
    rgba(255,255,255,0.95) 75%,
    rgba(212,175,55,0.4) 100%);
  background-size:200% 100%;
  -webkit-background-clip:text;background-clip:text;
  -webkit-text-fill-color:transparent;
  animation:titleShimmer 2.4s linear infinite,
             titleGlitch 4s 0.5s steps(1) infinite;
}
@keyframes titleShimmer{
  0%   {background-position:200% 0}
  100% {background-position:-200% 0}
}
@keyframes titleGlitch{
  0%, 92%, 100%{transform:translate(0,0);text-shadow:none;}
  93%{transform:translate(-1px,0);text-shadow:1px 0 #d4af37;}
  95%{transform:translate(1px,0);text-shadow:-1px 0 rgba(255,255,255,0.6);}
  97%{transform:translate(0,1px);text-shadow:1px 0 #d4af37;}
}
/* Sub-caption */
.sub{
  color:#7a7a7a;
  font-size:11px;
  letter-spacing:6px;
  margin-bottom:24px;
  font-family:"SF Mono","Consolas",monospace;
  opacity:0;
  animation:subIn 0.6s 0.7s ease forwards;
}
@keyframes subIn{
  from{opacity:0;letter-spacing:2px;}
  to  {opacity:1;letter-spacing:6px;}
}
/* Title bracket frame */
.title-bracket{
  display:flex;align-items:center;justify-content:center;gap:12px;
  margin-bottom:24px;
  font-family:"SF Mono","Consolas",monospace;
  font-size:10px;color:rgba(212,175,55,0.5);
  letter-spacing:2px;
}
.title-bracket::before,.title-bracket::after{
  content:'';flex:0 0 60px;height:1px;
  background:linear-gradient(90deg,transparent,rgba(212,175,55,0.5),transparent);
}
.title-bracket::before{background:linear-gradient(90deg,transparent,rgba(212,175,55,0.5));}
.title-bracket::after{background:linear-gradient(-90deg,transparent,rgba(212,175,55,0.5));}

/* Waveform equalizer — 8 bars */
.wave-bars{
  display:flex;align-items:center;justify-content:center;
  gap:3px;height:32px;margin:0 auto 20px;
}
.wave-bars span{
  width:3px;height:8px;background:#d4af37;
  border-radius:1px;
  animation:waveBar 0.9s ease-in-out infinite;
  box-shadow:0 0 6px rgba(212,175,55,0.4);
}
.wave-bars span:nth-child(1){animation-delay:0.0s;}
.wave-bars span:nth-child(2){animation-delay:0.1s;}
.wave-bars span:nth-child(3){animation-delay:0.2s;}
.wave-bars span:nth-child(4){animation-delay:0.3s;}
.wave-bars span:nth-child(5){animation-delay:0.4s;}
.wave-bars span:nth-child(6){animation-delay:0.5s;}
.wave-bars span:nth-child(7){animation-delay:0.6s;}
.wave-bars span:nth-child(8){animation-delay:0.7s;}
@keyframes waveBar{
  0%,100%{height:6px;opacity:0.4;}
  50%   {height:28px;opacity:1;}
}

/* Progress bar with shimmer */
.bar-track{
  width:320px;height:2px;
  background:rgba(212,175,55,0.15);
  margin:0 auto 12px;
  position:relative;overflow:hidden;
  border-radius:1px;
  box-shadow:0 0 8px rgba(212,175,55,0.15);
}
.bar-fill{
  position:absolute;left:0;top:0;
  height:100%;width:0%;
  background:linear-gradient(90deg,transparent 0%,#d4af37 50%,transparent 100%);
  animation:fillBar 2.0s cubic-bezier(0.4,0,0.2,1) forwards;
  box-shadow:0 0 8px rgba(212,175,55,0.6);
}
.bar-shimmer{
  position:absolute;top:0;left:-30%;
  width:30%;height:100%;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,0.6),transparent);
  animation:shimmer 1.6s linear infinite;
}
@keyframes fillBar{0%{width:0%}100%{width:100%}}
@keyframes shimmer{0%{left:-30%}100%{left:100%}}

/* Status line with blinking LED */
.status{
  color:#5a5a5a;
  font-size:10px;
  letter-spacing:3px;
  min-height:14px;
  font-family:"SF Mono","Consolas",monospace;
  display:inline-flex;align-items:center;gap:8px;
  animation:statusFade 1.6s ease-in-out infinite;
}
.status::before{
  content:'';width:6px;height:6px;border-radius:50%;
  background:#d4af37;
  box-shadow:0 0 6px 1px rgba(212,175,55,0.7);
  animation:ledBlink 0.8s ease-in-out infinite;
}
@keyframes ledBlink{
  0%,100%{opacity:0.3;}
  50%   {opacity:1;}
}
@keyframes statusFade{
  0%,100%{opacity:0.5}
  50%{opacity:0.95}
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
<div class="hex-grid"></div>
<div class="scanline"></div>
<div class="crt-lines"></div>
<div class="vignette"></div>
<div class="particles">
  <div class="particle" style="left:10%;animation-duration:8s;animation-delay:0s;"></div>
  <div class="particle" style="left:25%;animation-duration:12s;animation-delay:1s;"></div>
  <div class="particle" style="left:45%;animation-duration:9s;animation-delay:2s;"></div>
  <div class="particle" style="left:65%;animation-duration:11s;animation-delay:0.5s;"></div>
  <div class="particle" style="left:80%;animation-duration:7s;animation-delay:3s;"></div>
  <div class="particle" style="left:90%;animation-duration:10s;animation-delay:1.5s;"></div>
  <div class="particle" style="left:35%;animation-duration:13s;animation-delay:2.5s;"></div>
  <div class="particle" style="left:55%;animation-duration:8.5s;animation-delay:0.8s;"></div>
</div>
<!-- Stage 1: full sci-fi startup UI. Fades out at 2.4s. -->
<div class="splash-loading">
<div class="splash-center-fix">
<div class="wrap">
  <div class="title-bracket">SYSTEM BOOT</div>
  <div class="tech-wrap">
    <div class="tech-aura"></div>
    <div class="tech-ring tech-ring-outer"><span class="tech-dot tech-dot-outer"></span></div>
    <div class="tech-ring tech-ring-r1"><span class="tech-dot tech-dot-r1"></span></div>
    <div class="tech-ring tech-ring-r2"><span class="tech-dot tech-dot-r2"></span></div>
    <div class="tech-ring tech-ring-mid"><span class="tech-dot tech-dot-mid"></span></div>
    <div class="tech-ring tech-ring-r3"><span class="tech-dot tech-dot-r3"></span></div>
    <div class="tech-ring tech-ring-inner"><span class="tech-dot tech-dot-inner"></span></div>
    <div class="tech-scan"></div>
    <div class="tech-cross"></div>
    <div class="tech-core"></div>
  </div>
  <div class="title">HERMES</div>
  <div class="sub">轻于形 · 智于心</div>
  <div class="wave-bars">
    <span></span><span></span><span></span><span></span>
    <span></span><span></span><span></span><span></span>
  </div>
  <div class="bar-track"><div class="bar-shimmer"></div><div class="bar-fill"></div></div>
  <div class="status">INITIALIZING</div>
  <div class="hud-bracket tl"></div>
  <div class="hud-bracket tr"></div>
  <div class="hud-bracket bl"></div>
  <div class="hud-bracket br"></div>
  </div>
  </div>
  </div>

  <!-- Stage 2: main UI mock (welcome screen, 140px logo, brand title). Fades
     in at 2.7s. Looks identical to the real main UI, so when Python
     calls load_url(URL) at 4.5s to swap in the real webview2 page, the
     user perceives zero cut. -->
<div class="splash-mock">
  <div class="splash-mock-toolbar"></div>
  <div class="splash-mock-center">
    <img class="splash-mock-logo" src="hermes-logo.png" alt="Hermes">
    <h1>Hermes</h1>
    <div class="splash-mock-tag">轻于形 · 智于心</div>
    <div class="splash-mock-status">选择模型 · 开始对话</div>
  </div>
  <div class="splash-mock-input"></div>
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
    # 1. Immersive dark mode for the title bar (attribute 20). Without this,
    #    DWM uses a white caption on most Win10 themes regardless of any
    #    color attribute we set next.
    try: dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(ctypes.c_int(1)), 4)
    except Exception: pass
    # 2. Caption bar background = #000000 (matches the app's dark theme).
    #    BGR-ordered COLORREF: 0x00BBGGRR.
    try: dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(ctypes.c_int(0x00000000)), 4)
    except Exception: pass
    # 3. Caption text color = #d4af37 (gold "Hermes"). Win11 22H2+; harmless
    #    error on older Windows. BGR: 0x0037afd4.
    try: dwmapi.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(ctypes.c_int(0x0037afd4)), 4)
    except Exception: pass

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
    w = webview.create_window('Hermes Pulse', url=splash_url,
            x=(sw-win_w)//2, y=(sh-win_h)//2,
            width=win_w, height=win_h,
            min_size=(800, 600), resizable=True, text_select=True,
            background_color="#000000")
    window = w
    w.events.closing += on_window_close

        # Apply dark titlebar ASAP — right after window creation, not after
        # load_url. Without this the splash phase shows a white title bar
        # against the black splash background.
    if _IS_WIN:
        def _dark_titlebar_early():
            for _ in range(100):
                try:
                    if window and window.native and window.native.Handle:
                        _apply_dark_titlebar(window.native.Handle.ToInt32())
                        return
                except Exception:
                    pass
                time.sleep(0.05)
        threading.Thread(target=_dark_titlebar_early, daemon=True).start()
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
        _splash_min_ms = 4500   # splash 跑 stage1 (2.5s) + stage2 mock (1.8s) + 缓冲 0.2s = 4.5s 后才切真主页

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
