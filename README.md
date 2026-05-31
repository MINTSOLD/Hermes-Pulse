<div align="center">

# ✦ Hermes Desktop GUI

**一个为 Hermes Agent 打造的独立桌面客户端**

纯黑美学 · 呼吸光效 · 零框架依赖 · 开箱即用

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078d4.svg)](https://windows.com)

</div>

---

## ✨ 它是什么

Hermes Desktop GUI 是 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 的原生桌面客户端。它不是一个浏览器标签页——它是一个真正的独立应用窗口，拥有自定义标题栏、系统托盘图标、以及一整套精心设计的视觉体验。

打开即用：自动启动后端服务、自动连接网关、自动检测模型配置。

## 📸 界面预览

> *将你的截图放入 `screenshots/` 目录，替换下方占位图*

| 主界面 | 模型选择 | 工具调用 |
|:---:|:---:|:---:|
| ![主界面](screenshots/main.png) | ![模型选择](screenshots/model-picker.png) | ![工具调用](screenshots/tool-usage.png) |

| 多标签页 | 设置面板 | 消息队列 |
|:---:|:---:|:---:|
| ![多标签页](screenshots/multi-tab.png) | ![设置面板](screenshots/settings.png) | ![消息队列](screenshots/queue.png) |

## 🏆 为什么选择 Hermes Desktop GUI

### 对比主流 AI 客户端

| 特性 | Hermes GUI | ChatGPT Desktop | Open WebUI | LobeChat | ChatBox |
|:---|:---:|:---:|:---:|:---:|:---:|
| **独立桌面窗口** | ✅ 原生窗口 | ✅ Electron | ❌ 浏览器 | ❌ 浏览器 | ✅ Electron |
| **框架依赖** | ✅ 零依赖 | ❌ Electron 200MB+ | ❌ Node.js | ❌ Next.js | ❌ Electron |
| **启动速度** | ⚡ <2秒 | 🐌 5-10秒 | 🐌 需要 Docker | 🐌 需要 Node | 🐌 5-8秒 |
| **内存占用** | ~30MB | ~200MB+ | ~500MB+ | ~300MB+ | ~150MB+ |
| **呼吸光效动画** | ✅ 独创 | ❌ | ❌ | ❌ | ❌ |
| **多标签对话** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **多模型供应商** | ✅ 10+ | ❌ 仅 OpenAI | ✅ | ✅ | ✅ |
| **工具调用可视化** | ✅ 实时计时 + 折叠 | ❌ | ⚠️ 基础 | ⚠️ 基础 | ❌ |
| **消息排队** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **智能滚动** | ✅ 跟滚 + 回滚 | ⚠️ 基础 | ⚠️ 基础 | ⚠️ 基础 | ⚠️ 基础 |
| **自动服务管理** | ✅ 一键修复 | ❌ | ❌ | ❌ | ❌ |
| **文件拖拽上传** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **纯黑美学设计** | ✅ | ❌ 深灰 | ❌ | ❌ | ❌ |
| **中文优化** | ✅ 原生 | ⚠️ 翻译 | ⚠️ 翻译 | ✅ | ⚠️ 翻译 |

### 核心优势

#### 🖤 纯黑美学，呼吸光效

这不是又一个"深色模式"。Hermes GUI 采用纯黑底色 (#000000)，配合独创的呼吸光效系统：

- **输入框光环**：聚焦时多层渐变光晕脉动，如呼吸般自然
- **用户消息光带**：消息气泡上下方有微光流动
- **分隔线呼吸**：工具栏、输入区的分隔线缓慢明灭
- **连接状态光点**：在线时白色光点柔和脉动
- **Logo 悬浮**：启动页 Logo 带径向光晕缓慢升降

每一个动画都使用 `ease-in-out` 缓动，有机而克制。

#### ⚡ 零框架，极致轻量

前端完全由原生 HTML + CSS + JavaScript 构成：
- 没有 React、Vue、Angular
- 没有 Webpack、Vite、打包工具
- 没有 node_modules
- 总文件大小 < 200KB

一个 `app.js` (80KB) + 一个 `styles.css` (44KB) + 一个 `index.html` (8KB) = 完整的桌面应用前端。

对比 Electron 应用动辄 200MB+ 的体积和 200MB+ 的内存占用，Hermes GUI 仅需 ~30MB 内存。

#### 🔧 工具调用，实时可视化

当 Hermes Agent 调用工具时（搜索网页、读取文件、执行命令等）：

1. **实时显示**：工具名称、状态、计时器同步更新
2. **流式追踪**：每个工具调用独立计时，精确到秒
3. **自动折叠**：模型输出完毕后，工具区自动折叠为一行摘要
4. **摘要信息**：显示 "🔧 3 个工具已使用"，一目了然

#### 📑 多标签对话

像浏览器一样管理多个对话：
- 点击 `+` 创建新对话
- 自动命名：首条消息的前 15 个字成为标签名
- 切换标签时完整保留对话历史
- 每个标签独立的 token 统计

#### 🧠 智能滚动系统

**流式输出时**：
- 用户在底部 → 自动跟滚，最新内容始终可见
- 用户上滚回顾 → 不打断阅读，模型继续输出
- 用户回到底部 → 自动恢复跟滚

**输出结束后**：
- 自动平滑滚到助手回复的开头
- 用户可以从头往下读，无需手动滚动

#### 🛡️ 自动服务管理

- 启动时自动检测配置服务、网关、控制面板
- 发现服务异常时自动修复
- 后台看门狗每 30 秒巡检，掉线自动重启
- 一键重连按钮，逐项检测并修复

## 🚀 快速开始

### 前置条件

- Windows 10/11
- Python 3.11+
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) 已安装

### 安装

```bash
# 克隆仓库
git clone https://github.com/your-username/hermes-gui.git
cd hermes-gui

# 安装依赖
pip install pywebview

# 启动
python hermes_gui.py
```

### 作为 Windows 服务运行

1. 将整个文件夹放入 `C:\Program Files\Hermes Agent\`
2. 创建 Windows 计划任务，触发器设为"用户登录时"
3. 操作指向 `pythonw.exe hermes_gui.py`
4. 使用 VBS 包装器隐藏控制台窗口

## 🏗️ 架构

```
┌─────────────────────────────────────────┐
│           Hermes Desktop GUI            │
│         (pywebview + WebView2)          │
├─────────────┬───────────────────────────┤
│  前端 (浏览器)  │     后端 (Python)         │
│  index.html  │   config_server.py       │
│  app.js      │   ├─ 静态文件服务 (:18765) │
│  styles.css  │   ├─ 配置管理 API         │
│              │   ├─ 网关代理 (:8642)      │
│              │   └─ 服务看门狗            │
├─────────────┴───────────────────────────┤
│              Hermes Gateway             │
│            (AI 后端 :8642)               │
└─────────────────────────────────────────┘
```

## 📁 项目结构

```
hermes-gui/
├── hermes_gui.py          # 桌面启动器（pywebview + 服务管理）
├── config_server.py       # 后端服务（配置 + 代理 + 看门狗）
├── index.html             # GUI 入口页面
├── app.js                 # 前端逻辑（流式输出、标签管理、智能滚动）
├── styles.css             # 视觉系统（呼吸光效、纯黑主题）
├── start_config_server.vbs # VBS 包装器（隐藏控制台启动）
├── hermes-logo.png        # 应用 Logo
├── hermes.ico             # 任务栏图标
├── hermes-titlebar.ico    # 标题栏图标
├── screenshots/           # 界面截图
├── LICENSE                # MIT 许可证
└── README.md              # 本文件
```

## 🛠️ 技术栈

| 层级 | 技术 | 说明 |
|:---|:---|:---|
| 桌面窗口 | pywebview + WebView2 | 原生 Windows 窗口，非 Electron |
| 前端 | Vanilla HTML/CSS/JS | 零框架，零打包，零依赖 |
| 后端 | Python ThreadingHTTPServer | 单文件服务器，无第三方 Web 框架 |
| 动画 | CSS @keyframes | 10+ 独创呼吸光效动画 |
| 流式输出 | SSE (Server-Sent Events) | 实时逐字渲染 |
| 进程管理 | subprocess + socket | 自动启动、健康检查、看门狗 |

## 📄 License

[MIT](LICENSE) © 2026 Hermes

---

<div align="center">

**用 ❤️ 和 ☕ 构建**

</div>
