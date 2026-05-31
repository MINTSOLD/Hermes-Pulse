# Hermes Pulse — Hacker News "Show HN" 推广文案

## 标题

Show HN: Hermes Pulse – Native desktop client for Hermes Agent, ~30MB RAM, zero Electron

## 正文

https://github.com/MINTSOLD/hermes-pulse

Hermes Pulse is a native desktop GUI for Hermes Agent (open-source AI agent framework). Built on pywebview + WebView2 — true native window, not Electron.

Key design decisions:

1. **Zero frontend frameworks.** Three files (HTML/CSS/JS), < 200KB total. No React, no build tools, no node_modules.

2. **Breathing light effects as state visualization.** Input pulses when focused, connection dots glow when online, dividers fade in/out. Not decoration — information.

3. **Smart scroll.** Auto-follows streaming output. User scrolls up → stops following. Back to bottom → resumes. Completion → rolls back to response start.

4. **Tool call visualization.** Real-time timers during Hermes tool usage (web search, file ops, terminal). Auto-collapses to one-line summary on completion.

5. **Auto service management.** Background watchdog monitors config server + gateway, auto-restarts on failure. One-click reconnect.

Benchmarks vs Electron-based clients:
- Install: < 1MB vs 200MB+
- Memory: ~30MB vs 200-500MB
- Startup: < 2s vs 5-10s

Tech: pywebview + WebView2 (window), Python ThreadingHTTPServer (backend), CSS @keyframes (animations), SSE (streaming).

Currently Windows only. macOS/Linux support planned.

Feedback welcome — especially on what's missing from current AI desktop clients.
