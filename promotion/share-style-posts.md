# Hermes Pulse — 分享风格文案（发现+体验+推荐）

## 英文版 — Reddit / Twitter / Discord 通用

### 标题
Found a really lightweight AI desktop client that deserves more attention

### 正文

Was looking for a proper desktop client for Hermes Agent (tired of using the CLI for everything) and stumbled upon this project called Hermes Pulse.

Tried it for a few days and honestly surprised how well it works for something so small.

**What stood out:**

The whole thing is like 200KB of frontend code. No Electron, no React, no node_modules folder that weighs more than my OS. Just HTML/CSS/JS + a Python backend. Installs in seconds, uses ~30MB RAM.

The UI has these breathing light effects that actually serve a purpose — the input area pulses when it's listening, connection status is shown through a glowing dot instead of text, tool calls show real-time timers that collapse into a summary when done. Sounds gimmicky but it's actually useful for knowing what's happening at a glance.

Smart scroll is the feature I didn't know I needed. During streaming it follows the output, but when I scroll up to read something it stops. Scroll back down and it resumes. When the response finishes it rolls back to the beginning so I can read from the top. Small thing but makes a big difference in daily use.

Supports a ton of providers out of the box — OpenAI, Anthropic, Google, DeepSeek, Kimi, and a bunch of Chinese ones I hadn't heard of before. Tab system works like browser tabs, auto-names based on first message.

**What could be better:**
- Windows only for now
- No dark/light theme toggle (it's always pure black)
- Would love to see session export someday

GitHub if anyone wants to check it out: https://github.com/MINTSOLD/Hermes-Pulse

Anyone else using Hermes Agent? What client are you using?


---

## 中文版 — V2EX / 即刻 / 知乎 通用

### 标题
发现一个很轻的 Hermes Agent 桌面客户端，用了几天觉得不错

### 正文

最近在找 Hermes Agent 的 GUI 客户端，CLI 用久了想换个有界面的。搜了一圈发现一个叫 Hermes Pulse 的项目，试了几天说说体验。

**第一印象：真的很小**

整个前端就三个文件，加起来不到 200KB。没有 Electron，没有 node_modules，安装包 1MB 都不到。启动速度秒开，内存占用 30MB 左右。对比那些 Electron 动辄 200MB+ 的客户端，这个体量确实惊艳。

**界面：呼吸光效不是噱头**

一开始以为呼吸光效是花里胡哨的装饰，用了才发现是真的有功能性：
- 输入框聚焦时会脉动，表示正在接收输入
- 连接状态用光点闪烁表示，不用看文字
- 工具调用时有实时计时器，完成后自动折叠成一行摘要

整个界面是纯黑底色，所有动画都是 CSS 原生实现，流畅且不费性能。

**智能滚动：用回不去的功能**

流式输出时自动跟滚，但你上滚阅读时它会停下来不打断你。回到底部又自动恢复。输出结束后还会自动滚回复开头，方便从头读。这个设计确实比其他客户端做得好。

**多供应商支持**

开箱支持 OpenAI、Anthropic、Google、DeepSeek、Kimi、MiniMax、通义等十几家。多标签对话，自动命名，独立 token 统计。

**不足：**
- 目前只有 Windows
- 没有明暗主题切换（固定纯黑）
- 希望以后能加会话导出

GitHub：https://github.com/MINTSOLD/Hermes-Pulse

用 Hermes Agent 的朋友你们用什么客户端？


---

## Twitter/X 短版 Thread

### Tweet 1
Found a lightweight desktop client for Hermes Agent that I want to share.

It's called Hermes Pulse — pure HTML/CSS/JS frontend, ~30MB RAM, < 2s startup. No Electron.

Tried it for a few days, here's what I think 🧵

### Tweet 2
The breathing light effects actually serve a purpose:

• Input pulses when listening
• Connection shown via glowing dot
• Tool calls have real-time timers
• Everything collapses to summary when done

Not just aesthetics — it's state visualization.

### Tweet 3
Smart scroll is the feature I didn't know I needed:

• Streaming → auto-follows
• Scroll up → stops
• Scroll down → resumes
• Complete → rolls back to start

Makes reading long responses so much better.

### Tweet 4
What surprised me most:

• Install: < 1MB
• RAM: ~30MB
• Startup: < 2 seconds
• Zero node_modules

The entire frontend is 3 files under 200KB. That's how desktop apps should be.

### Tweet 5
Supports OpenAI, Anthropic, Google, DeepSeek, Kimi, Qwen, MiniMax and more.

Tab system like browser, auto-names conversations.

Windows only for now, but solid for what it is.

GitHub: https://github.com/MINTSOLD/Hermes-Pulse

Worth a look if you use Hermes Agent.


---

## GitHub Discussion（直接发）

### 标题
Just tried Hermes Pulse — here's my experience

### 正文

Hey everyone,

Wanted to share my experience with Hermes Pulse after using it for a few days.

Coming from the CLI, having a proper desktop GUI is a nice change. The thing that impressed me most is how lightweight it is — the whole frontend is < 200KB, no Electron overhead, ~30MB RAM usage.

The breathing light effects look cool but also serve a functional purpose. Tool calls show real-time timers and auto-collapse when done. The smart scroll follows streaming output but stops when you scroll up to read.

It supports a bunch of providers out of the box which is convenient for switching between models.

Overall a solid client if you want something light and fast. Would love to see macOS/Linux support in the future.

GitHub: https://github.com/MINTSOLD/Hermes-Pulse
