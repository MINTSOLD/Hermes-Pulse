<div align="center">

# ✦ Hermes Pulse

**Native Desktop Client for Hermes Agent — Light in Form, Intelligent at Heart**

Pure Black Aesthetic · Breathing Light Effects · Zero Frameworks · 30MB Memory · Ready to Use

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078d4.svg)](https://windows.com)
[![Memory](https://img.shields.io/badge/Memory-~30MB-brightgreen.svg)]()

**[中文 🌐](README.md)**

</div>

---

## ✨ What is Hermes Pulse

> ⚠️ **Current version supports Windows 10/11 only** (built on pywebview + WebView2, native Windows components). macOS / Linux support is on the roadmap.

Hermes Pulse is a **native desktop client** for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

It's not another Electron wrapper, not another browser tab — it's a true native window built on **pywebview + WebView2**, designed for Windows, blending seamlessly with your system.

**Design Philosophy: Light in form, intelligent at heart.**

We believe AI clients shouldn't be bloated. Hermes Pulse's entire frontend is under 200KB, uses ~30MB of memory, and starts in under 2 seconds — yet every pixel, every animation frame, every interaction has been carefully crafted.

> *We don't pile on features. We refine experiences.*
> *We don't chase "big and complete." We pursue "light and powerful."*
> *Every pulse of the breathing light effect externalizes Hermes' intelligent state.*

---

## 📸 Screenshots

| Main Interface | Model Selection |
|:---:|:---:|
| ![Main Interface](screenshots/main.png) | ![Model Selection](screenshots/model-picker.png) |

| Settings Panel | Multi-Platform Setup |
|:---:|:---:|
| ![Settings Panel](screenshots/settings.png) | ![Multi-Platform](screenshots/platforms.png) |

---

## 🏆 Why Hermes Pulse

### Ultra-Lightweight: Redefining AI Clients

| | Hermes Pulse | Hermes Agent CLI | OpenClaw | LobeChat | NextChat |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Type** | Native Desktop Client | Terminal CLI | Web UI | Web UI | Web UI |
| **Tech Stack** | pywebview Native | Python CLI | Docker + Node | Next.js | Electron |
| **Install Size** | **< 1 MB** | ~50 MB | 500 MB+ | 300 MB+ | 150 MB+ |
| **Memory Usage** | **~30 MB** | ~20 MB | ~500 MB+ | ~300 MB+ | ~150 MB+ |
| **Startup Time** | **< 2 sec** | < 1 sec | Needs Docker | Needs Node | 5-8 sec |
| **Interface** | Native Window GUI | Terminal Text | Browser | Browser | Pseudo-native |
| **Breathing Effects** | ✅ Original | ❌ | ❌ | ❌ | ❌ |
| **Smart Scroll** | ✅ Follow + Rollback | ❌ | ⚠️ Basic | ⚠️ Basic | ⚠️ Basic |
| **Tool Visualization** | ✅ Real-time + Collapse | ⚠️ Plain Text | ⚠️ Basic | ⚠️ Basic | ❌ |
| **Multi-Tab** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Message Queue** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Auto-DevOps** | ✅ Watchdog | ❌ Manual | ❌ Manual | ❌ | ❌ |

> **Hermes Pulse is the only native desktop client in the Hermes Agent ecosystem.**
> CLI is for power users, Web UI is for self-hosters — Pulse is for everyone who wants an elegant experience.
> With < 1MB install size and ~30MB memory, we deliver the complete experience that others need 200MB+ for.

### Breathing Light Effects: More Than Just Pretty

Hermes Pulse's original breathing light system isn't decoration — it's **intelligent state visualization**:

- 🫁 **Input Pulse**: Multi-layer gradient glow breathes when focused, suggesting Hermes is listening
- ✨ **Message Light Bands**: Subtle light flows above and below user messages, delineating conversation boundaries
- 🟢 **Connection Indicator**: White dot pulses gently when online, dims when offline — status at a glance, no text needed
- 🎭 **Tool Tracking**: Real-time timers during tool calls, auto-collapses to summary on completion — transparent process, clear results
- 🌊 **Divider Breathing**: Toolbar and input area dividers slowly fade in and out — the entire interface seems to breathe

> *When AI thinks, the interface breathes.*
> *When AI acts, the lights pulse.*
> *This is Hermes Pulse — an AI client with a heartbeat.*

### Smart Interaction: Intuitive by Design

**Smart Scroll System**:
- Auto-follows during model output — you always see the latest content
- Stops when you scroll up — never interrupts your reading
- Resumes when you scroll back down — seamless transition
- Returns to response start after completion — read from the beginning, no manual scrolling

**Multi-Tab Conversations**:
- Manage multiple chats like browser tabs
- Auto-naming: first message becomes the tab name
- Full history and token stats preserved per tab

**Message Queue**:
- Keep typing while the model thinks
- Messages queue up and send in order
- Never lose an idea

**Tool Call Visualization**:
- Real-time display of tool names, statuses, and timers
- Independent tracking for each tool call
- Auto-collapses to one-line summary: "🔧 3 tools used"

### Multi-Model · Multi-Platform · One-Click Switch

- **10+ Providers**: OpenAI, Anthropic, Google, DeepSeek, Kimi, MiniMax, Xiaomi, Qwen, xAI...
- **Multi-Platform**: Telegram, Discord, Slack, WeChat, QQ, Feishu, WhatsApp...
- **One-Click Model Switch**: Click the toolbar to switch — no restart needed
- **Config Visualization**: All API keys and platform statuses at a glance

### Auto-DevOps: Just Chat

- Automatically detects and starts all dependent services on launch
- Background watchdog checks every 30 seconds, auto-restarts on failure
- One-click reconnect button with step-by-step diagnostics
- You don't need to know what "ports" or "processes" are — Hermes Pulse handles it all

---

## 🚀 Quick Start

### Option 1: Download Installer (Recommended)

Download `HermesPulse-1.0.0.zip` from [Releases](https://github.com/MINTSOLD/hermes-pulse/releases), extract, and double-click `install.bat`.

### Option 2: Manual Install

```bash
# Prerequisites
# - Windows 10/11
# - Python 3.11+
# - Hermes Agent installed (pip install hermes-agent)

# Clone the repo
git clone https://github.com/MINTSOLD/hermes-pulse.git
cd hermes-gui

# Install dependencies
pip install pywebview

# Launch
python hermes_gui.py
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│           Hermes Pulse Window               │
│        pywebview + WebView2 Native          │
├──────────────────┬──────────────────────────┤
│   Frontend (Browser)│    Backend (Python)     │
│                  │                          │
│  index.html      │   config_server.py       │
│  app.js    80KB  │   ├─ Static Server (:18765)│
│  styles.css 44KB │   ├─ Config API           │
│                  │   ├─ Gateway Proxy (:8642) │
│  Total < 200KB   │   └─ Service Watchdog     │
├──────────────────┴──────────────────────────┤
│              Hermes Gateway                  │
│            (AI Backend :8642)                │
└─────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
hermes-pulse/
├── hermes_gui.py          # Desktop launcher (pywebview + service orchestration)
├── config_server.py       # Backend server (config + proxy + watchdog)
├── index.html             # GUI entry point
├── app.js                 # Frontend logic (streaming, tabs, smart scroll)
├── styles.css             # Visual system (breathing effects, pure black theme)
├── start_config_server.vbs # VBS wrapper (hide console)
├── hermes-logo.png        # App logo
├── hermes.ico             # Taskbar icon
├── hermes-titlebar.ico    # Title bar icon
├── installer/             # Installer scripts
├── screenshots/           # Interface screenshots
├── LICENSE                # MIT License
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology | Description |
|:---|:---|:---|
| Desktop Window | **pywebview + WebView2** | Native Windows window, not Electron |
| Frontend | **Vanilla HTML/CSS/JS** | Zero frameworks, zero bundling, zero node_modules |
| Backend | **Python ThreadingHTTPServer** | Single-file server, no third-party web framework |
| Animations | **CSS @keyframes** | 10+ original breathing light effect animations |
| Streaming | **SSE (Server-Sent Events)** | Real-time token-by-token rendering |
| Process Mgmt | **subprocess + socket** | Auto-start, health checks, watchdog |

---

## 🗺️ Roadmap

- [ ] One-click installer (Inno Setup)
- [ ] System tray resident mode
- [ ] Session export (Markdown / PDF)
- [ ] Voice input
- [ ] Plugin system
- [ ] Custom theme colors
- [ ] Multi-language support
- [ ] macOS / Linux adaptation

---

## 🤝 Contributing

We welcome any form of feedback!

- 🐛 **Report Bugs**: [Submit an Issue](https://github.com/MINTSOLD/hermes-pulse/issues)
- 💡 **Feature Requests**: [Start a Discussion](https://github.com/MINTSOLD/hermes-pulse/discussions)
- 🔧 **Submit Code**: Fork → Branch → PR
- ⭐ **Star Us**: The simplest way to show support

> *Hermes Pulse is a young project. Every piece of feedback shapes its future.*

---

## 📄 License

[MIT](LICENSE) © 2026 Hermes

---

<div align="center">

**Light in Form. Intelligent at Heart.**

</div>
