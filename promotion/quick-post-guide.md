# 一键发布指南（每个平台只需 2 分钟）

---

## 1. V2EX（国内开发者，效果最好）

打开 https://www.v2ex.com → 登录 → 点"创作"

**节点选：** 分享发现 或 程序员

**标题：**
```
用了几天 Hermes Agent，发现一个挺有意思的桌面客户端
```

**正文（全选复制粘贴）：**
```
最近在折腾 Hermes Agent，CLI 用了一段时间后想找个有界面的客户端。

翻了一圈 GitHub，找到一个叫 Hermes Pulse 的项目，试了几天，说说真实体验。

安装体验
下载解压后一个 install.bat，自动检测 Python、自动装依赖、自动配快捷方式。整个过程不到 1 分钟。

第一印象：这个体积有点意外
整个前端就三个文件，HTML + CSS + JS，加起来不到 200KB。没有 Electron，没有 node_modules。启动后看了下任务管理器，内存占用 30MB 左右。

呼吸光效
输入框聚焦的时候会脉动，告诉你"我在听"。连接状态用一个白色光点表示，在线就闪烁，离线就熄灭。工具调用的时候有实时计时器，调用完自动折叠成一行。

智能滚动
流式输出的时候内容会自动往下滚。但你往上滚去看前面的内容，它就停下来不跟着动了。等你回到最下面，它又自动恢复。输出结束后还会自动滚回复的第一行。

不足
- 目前只有 Windows
- 没有明暗主题切换
- 希望以后能加会话导出

GitHub：https://github.com/MINTSOLD/Hermes-Pulse

你们在用什么客户端？
```

---

## 2. 掘金（前端/开发者社区）

打开 https://juejin.cn → 登录 → 点"写文章"

**分类：** 前端 / 开源推荐

**标题：**
```
用 200KB 前端代码做了个 AI 桌面客户端，效果怎么样？
```

**正文：** 用 V2EX 那段，加几张截图

---

## 3. Reddit r/SideProject

打开 https://www.reddit.com/r/SideProject/submit

**标题：**
```
I made a lightweight desktop client for Hermes Agent – ~30MB RAM, no Electron, breathing light effects
```

**正文（全选复制粘贴）：**
```
Hey! Been working on a desktop client for Hermes Agent called Hermes Pulse.

What it does:
- Native desktop window (pywebview + WebView2, not Electron)
- ~30MB RAM, < 2s startup, < 1MB install
- Breathing light effects that show system state
- Smart scroll that follows streaming output
- Tool call visualization with timers
- Multi-tab conversations
- 10+ AI provider support

Tech stack: Pure HTML/CSS/JS frontend (3 files, < 200KB), Python backend.

GitHub: https://github.com/MINTSOLD/Hermes-Pulse

Would love feedback!
```

---

## 4. Hacker News

打开 https://news.ycombinator.com/submit

**标题：**
```
Show HN: Hermes Pulse – Lightweight desktop client for Hermes Agent (~30MB RAM)
```

**URL:** https://github.com/MINTSOLD/Hermes-Pulse

---

## 5. Twitter/X

发 6 条推文组成 Thread：

**Tweet 1:**
```
Been using Hermes Agent via CLI, wanted a GUI. Found this project called Hermes Pulse.

Tried it for a few days. Here's what I think 🧵
```

**Tweet 2:**
```
First thing I noticed: the size.

The entire frontend is 3 files under 200KB. No Electron. ~30MB RAM. Starts in under 2 seconds.
```

**Tweet 3:**
```
The UI has breathing light effects that actually serve a purpose:

• Input pulses when listening
• Connection shown via glowing dot
• Tool calls have real-time timers
• Collapses to one-line summary when done
```

**Tweet 4:**
```
Smart scroll is the feature I didn't know I needed:

• Streaming → auto-follows
• Scroll up → stops
• Back down → resumes
• Complete → rolls back to start
```

**Tweet 5:**
```
Supports OpenAI, Anthropic, Google, DeepSeek, Kimi, Qwen, MiniMax and more.

Tab system like browser, auto-names conversations.
```

**Tweet 6:**
```
If you use Hermes Agent and want something light, worth a look.

GitHub: https://github.com/MINTSOLD/Hermes-Pulse

What client are you using?
```

---

## 6. Discord 群

加入以下群，发短消息：

**消息：**
```
Hey, been using Hermes Agent for a while and found a desktop client called Hermes Pulse. It's surprisingly lightweight (~30MB RAM, no Electron). Has breathing light effects and smart scrolling. GitHub: https://github.com/MINTSOLD/Hermes-Pulse Anyone else tried it?
```

**要加的群：**
- Hermes Agent Discord（搜 "Hermes Agent"）
- LM Studio Discord
- Ollama Discord

---

## 发布顺序建议

1. ✅ GitHub Discussions（已发）
2. V2EX（5分钟）
3. Reddit r/SideProject（3分钟）
4. Twitter/X Thread（5分钟）
5. Hacker News（2分钟）
6. 掘金（10分钟，需要写文章格式）
7. Discord 群（逐个发，每个1分钟）
