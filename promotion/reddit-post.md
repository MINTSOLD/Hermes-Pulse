# Hermes Pulse — Reddit r/LocalLLaMA 推广文案

## 标题（英文）

[Release] Hermes Pulse – A native desktop client for Hermes Agent. Pure black, breathing light effects, zero frameworks, ~30MB RAM. How an AI client should feel.

## 正文

Hey everyone! 👋

I've been building a native desktop client for Hermes Agent and wanted to share it with the community.

**What is it?** Hermes Pulse is a lightweight desktop GUI for Hermes Agent — the open-source AI agent framework. It's built on pywebview + WebView2, so it's a true native window, not another Electron wrapper.

**Why I built it:**
- Every AI client I tried was either a browser tab or a 200MB+ Electron app
- I wanted something that feels like a real desktop app — fast, light, beautiful
- Hermes Agent deserved a proper GUI, not just a CLI

**What makes it different:**

🫁 **Breathing Light Effects** — The interface literally breathes. Input glows when focused, connection dots pulse when online, dividers fade in and out. It's not just aesthetics — it's state visualization.

⚡ **Ultra Lightweight:**
- Install size: < 1 MB (vs 200MB+ for Electron apps)
- Memory: ~30MB (vs 200-500MB)
- Startup: < 2 seconds
- Zero node_modules, zero build tools

🧠 **Smart Scroll** — During streaming, it auto-follows the output. Scroll up to review? It stops following. Back to bottom? It resumes. After completion? Rolls back to the response start so you can read from the beginning.

🔧 **Tool Visualization** — When Hermes calls tools (web search, file ops, terminal), you see real-time timers and status. After completion, everything collapses into a neat one-line summary.

📑 **Multi-Tab** — Like browser tabs for conversations. Auto-names based on first message.

🔗 **Multi-Provider** — OpenAI, Anthropic, Google, DeepSeek, Kimi, MiniMax, Xiaomi, Qwen, xAI... all in one interface.

**Tech stack (for the curious):**
- Frontend: Pure HTML/CSS/JS — 3 files, < 200KB total
- Backend: Python ThreadingHTTPServer — single file
- Window: pywebview + WebView2
- Animations: 10+ CSS @keyframes breathing effects

**Install:**
```bash
git clone https://github.com/MINTSOLD/hermes-pulse.git
cd hermes-pulse
pip install pywebview
python hermes_gui.py
```
Or grab the release zip — the installer handles everything including Hermes Agent detection.

**GitHub:** https://github.com/MINTSOLD/hermes-pulse

I'd love to hear your feedback! What features would you want in an AI desktop client? What's missing from current solutions?

---

*Hermes Pulse — Light in form, intelligent at heart.* ✦

---

# 备用中文版（如果要发中文社区）

## 标题

[发布] Hermes Pulse – Hermes Agent 原生桌面客户端。纯黑美学·呼吸光效·零框架·30MB内存

## 正文

大家好！分享一个我做的 Hermes Agent 桌面客户端。

**为什么做这个？**
试了一圈 AI 客户端，要么是浏览器标签页，要么是 200MB+ 的 Electron 包壳。我想要一个真正的桌面应用——快、轻、美。

**核心特点：**
- 🫁 呼吸光效：界面会"呼吸"，输入框脉动、连接点闪烁、分隔线明灭
- ⚡ 极致轻量：< 1MB 安装包，~30MB 内存，< 2秒启动
- 🧠 智能滚动：流式输出自动跟滚，上滚回顾不打断，结束后回滚到开头
- 🔧 工具可视化：实时计时，完成后自动折叠
- 📑 多标签对话：自动命名，独立历史
- 🔗 10+ 供应商：OpenAI/Anthropic/Google/DeepSeek/Kimi...

**技术栈：**
前端三个文件 < 200KB，后端一个 Python 文件，pywebview 原生窗口。零 Electron，零 node_modules。

**安装：**
```bash
git clone https://github.com/MINTSOLD/hermes-pulse.git
cd hermes-pulse && pip install pywebview && python hermes_gui.py
```

GitHub：https://github.com/MINTSOLD/hermes-pulse

欢迎试用反馈！
