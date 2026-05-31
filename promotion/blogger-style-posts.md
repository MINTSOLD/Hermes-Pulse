# Hermes Pulse — 博主分享风格文案（全部平台通用）

---

## 📝 核心原则

1. **不说"我做的"** — 说"我发现的"、"我试用的"
2. **不说"推荐"** — 说"说说体验"、"聊聊感受"
3. **不说"功能强大"** — 说"有个细节让我印象深刻"
4. **像写博客** — 有开头、有体验、有优缺点、有总结
5. **留互动** — 结尾问读者在用什么，引发讨论

---

## 🇨🇳 中文版 — V2EX / 掘金 / CSDN / 知乎 / 即刻

### 标题
用了几天 Hermes Agent，发现一个挺有意思的桌面客户端

### 正文

最近在折腾 Hermes Agent，CLI 用了一段时间后想找个有界面的客户端。

翻了一圈 GitHub，找到一个叫 Hermes Pulse 的项目，试了几天，说说真实体验。

**安装体验**

下载解压后一个 install.bat，自动检测 Python、自动装依赖、自动配快捷方式。整个过程不到 1 分钟，没有那种"装完一堆报错"的情况。

**第一印象：这个体积有点意外**

安装完看了下，整个前端就三个文件，HTML + CSS + JS，加起来不到 200KB。没有 Electron，没有 node_modules。启动后看了下任务管理器，内存占用 30MB 左右。

说实话有点意外，现在做个桌面客户端不套个 Electron 都不好意思打招呼了。

**有个设计让我印象比较深**

界面上有一些呼吸光效，一开始以为是花里胡哨的装饰。用了一会儿发现不是——

输入框聚焦的时候会脉动，告诉你"我在听"。连接状态用一个白色光点表示，在线就闪烁，离线就熄灭，不用看文字就知道状态。

还有工具调用的时候，每个工具旁边有实时计时器，调用完自动折叠成一行"🔧 3 个工具已使用"。这个在 CLI 里完全看不到。

**智能滚动这个功能用回不去了**

流式输出的时候，内容会自动往下滚。但你往上滚去看前面的内容，它就停下来不跟着动了。等你看完回到最下面，它又自动恢复跟滚。

输出结束后还会自动滚回复的第一行，方便从头读。这个设计确实比直接到底要好。

**不足也说一下**

- 目前只有 Windows，macOS 和 Linux 还没适配
- 没有明暗主题切换，固定纯黑（虽然挺好看的）
- 希望以后能加会话导出功能

**总结**

用了几天，整体感觉是个认真做的项目。不是那种"功能堆一堆但体验稀烂"的类型。如果你也在用 Hermes Agent，可以试试看。

GitHub：https://github.com/MINTSOLD/Hermes-Pulse

你们在用什么客户端？有没有类似的推荐？

---

## 🇬🇧 英文版 — Reddit / Hacker News / Dev.to / Product Hunt

### Title (Reddit)
Used Hermes Agent for a while, found an interesting desktop client worth sharing

### Title (Hacker News)
Show HN: Hermes Pulse – A lightweight desktop client for Hermes Agent

###正文

Been using Hermes Agent via CLI for a while and wanted a proper GUI. Found this project called Hermes Pulse on GitHub, tried it for a few days, here's my honest experience.

**Installation**

Download, extract, run install.bat. It auto-detects Python, installs pywebview, copies files, creates shortcuts. Under 1 minute, no errors. That already puts it ahead of most tools I've tried.

**First surprise: the size**

The entire frontend is 3 files — HTML, CSS, JS — under 200KB total. No Electron, no node_modules. Checked task manager: ~30MB RAM usage. In 2026, that's almost refreshing.

**The breathing light effects aren't just decoration**

The input area pulses when focused (tells you it's listening). Connection status is a white dot that glows when online, dims when offline. No text needed.

Tool calls show real-time timers next to each tool name. When done, everything collapses into one line: "🔧 3 tools used." Clean and informative.

**Smart scroll — didn't know I needed this**

During streaming, it follows the output. Scroll up to read something? It stops. Back to bottom? Resumes. When response finishes, it rolls back to the beginning so you can read from the top.

Small detail, but makes a big difference in daily use.

**What could be better**

- Windows only for now (macOS/Linux on roadmap)
- No dark/light theme toggle (always pure black, though it looks good)
- Would love session export someday

**Verdict**

Solid client if you want something light and fast for Hermes Agent. Not feature-bloated, not sluggish. Just works.

GitHub: https://github.com/MINTSOLD/Hermes-Pulse

Anyone else using Hermes Agent? What client are you using?

---

## 🐦 Twitter/X Thread — 英文

### Tweet 1
Been using Hermes Agent via CLI, wanted a GUI. Found this project called Hermes Pulse.

Tried it for a few days. Here's what I think 🧵

### Tweet 2
First thing I noticed: the size.

The entire frontend is 3 files under 200KB. No Electron. ~30MB RAM. Starts in under 2 seconds.

In 2026, that's almost refreshing.

### Tweet 3
The UI has breathing light effects that actually serve a purpose:

• Input pulses when listening
• Connection shown via glowing dot (no text needed)
• Tool calls have real-time timers
• Collapses to one-line summary when done

Not decoration — information.

### Tweet 4
Smart scroll is the feature I didn't know I needed:

• Streaming → auto-follows
• Scroll up → stops
• Back down → resumes
• Complete → rolls back to start

Makes reading long responses way better.

### Tweet 5
Supports OpenAI, Anthropic, Google, DeepSeek, Kimi, Qwen, MiniMax and more.

Tab system like browser, auto-names conversations.

Windows only for now, but solid for what it is.

### Tweet 6
If you use Hermes Agent and want something lighter than Electron clients, worth a look.

GitHub: https://github.com/MINTSOLD/Hermes-Pulse

What client are you using? Curious to hear.

---

## 💬 Discord 短版本

Hey, been using Hermes Agent for a while and found a desktop client called Hermes Pulse. Tried it for a few days — it's surprisingly lightweight (~30MB RAM, no Electron). Has some nice touches like breathing light effects and smart scrolling during streaming.

GitHub: https://github.com/MINTSOLD/Hermes-Pulse

Anyone else tried it? What client do you use?

---

## 📰 掘金/CSDN 技术文章标题

- 用 200KB 前端代码做了个 AI 桌面客户端，效果怎么样？
- 不用 Electron 也能做桌面客户端？Hermes Pulse 开发分享
- 一个只有 30MB 内存的 AI 客户端是怎么做到的
- 呼吸光效、智能滚动、工具可视化——聊聊 AI 客户端的体验设计
