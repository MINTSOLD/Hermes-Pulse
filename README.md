<div align="center">

# ✦ Hermes Pulse

**Hermes Agent 的原生桌面客户端 — 轻于形，智于心**

纯黑美学 · 呼吸光效 · 零框架 · 30MB 内存 · 开箱即用

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078d4.svg)](https://windows.com)
[![Memory](https://img.shields.io/badge/Memory-~30MB-brightgreen.svg)]()

**[English 🌐](README_EN.md)**

</div>

---

## ✨ 什么是 Hermes Pulse

Hermes Pulse 是 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 的**原生桌面客户端**。

它不是又一个 Electron 包壳，不是又一个浏览器标签页——它是基于 **pywebview + WebView2** 打造的真正原生窗口，专为 Windows 而生，与系统浑然一体。

**设计哲学：轻于形，智于心。**

我们相信 AI 客户端不应该是臃肿的。Hermes Pulse 的全部前端代码不超过 200KB，运行时仅占 30MB 内存，启动不到 2 秒——但它的每一个像素、每一帧动画、每一次交互，都经过精心打磨。

> *我们不堆砌功能，我们打磨体验。*
> *我们不追求"大而全"，我们追求"轻而强"。*
> *每一次呼吸光效的脉动，都是 Hermes 智能状态的外化。*

---

## 📸 界面预览

| 主界面 | 模型选择 |
|:---:|:---:|
| ![主界面](screenshots/main.png) | ![模型选择](screenshots/model-picker.png) |

| 设置面板 | 多平台一键设置 |
|:---:|:---:|
| ![设置面板](screenshots/settings.png) | ![多平台设置](screenshots/platforms.png) |

---

## 🏆 为什么选择 Hermes Pulse

### 极致轻量：重新定义 AI 客户端

| | Hermes Pulse | Hermes Agent CLI | OpenClaw | LobeChat | NextChat |
|:---|:---:|:---:|:---:|:---:|:---:|
| **类型** | 原生桌面客户端 | 终端 CLI | Web UI | Web UI | Web UI |
| **技术栈** | pywebview 原生 | Python CLI | Docker + Node | Next.js | Electron |
| **安装体积** | **< 1 MB** | ~50 MB | 500 MB+ | 300 MB+ | 150 MB+ |
| **运行内存** | **~30 MB** | ~20 MB | ~500 MB+ | ~300 MB+ | ~150 MB+ |
| **启动速度** | **< 2 秒** | < 1 秒 | 需 Docker | 需 Node | 5-8 秒 |
| **界面** | 原生窗口 GUI | 终端文本 | 浏览器 | 浏览器 | 伪原生 |
| **呼吸光效** | ✅ 独创 | ❌ | ❌ | ❌ | ❌ |
| **智能滚动** | ✅ 跟滚+回滚 | ❌ | ⚠️ 基础 | ⚠️ 基础 | ⚠️ 基础 |
| **工具可视化** | ✅ 实时+折叠 | ⚠️ 纯文本 | ⚠️ 基础 | ⚠️ 基础 | ❌ |
| **多标签** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **消息排队** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **自动运维** | ✅ 看门狗 | ❌ 手动 | ❌ 手动 | ❌ | ❌ |

> **Hermes Pulse 是 Hermes Agent 生态中唯一的原生桌面客户端。**
> CLI 适合极客，Web UI 适合自部署——而 Pulse 适合每一个想要优雅体验的用户。
> 我们用 < 1MB 的体积、~30MB 的内存，提供了其他项目 200MB+ 才能做到的完整体验。

### 呼吸光效：不只是好看

Hermes Pulse 独创的呼吸光效系统不是装饰——它是**智能状态的可视化**：

- 🫁 **输入框脉动**：聚焦时多层渐变光晕如呼吸般起伏，暗示 Hermes 正在聆听
- ✨ **消息光带**：用户消息上下方微光流动，区分对话边界
- 🟢 **连接光点**：在线时白色光点柔和脉动，离线时熄灭——无需文字，一眼知状态
- 🎭 **工具追踪**：调用工具时实时计时，完成后自动折叠为摘要——过程透明，结果清晰
- 🌊 **分隔线呼吸**：工具栏、输入区的分隔线缓慢明灭，整个界面仿佛在呼吸

> *当 AI 在思考，界面在呼吸。*
> *当 AI 在行动，光效在脉动。*
> *这就是 Hermes Pulse——有生命的 AI 客户端。*

### 智能交互：懂你所想

**智能滚动系统**：
- 模型输出时自动跟滚——你永远能看到最新内容
- 你上滚回顾时自动停止——不打断你的阅读
- 你回到底部时自动恢复——无缝衔接
- 输出结束后自动回滚到回复开头——从头读起，无需手动

**多标签对话**：
- 像浏览器一样管理多个对话
- 自动命名：首条消息成为标签名
- 切换时完整保留历史和 token 统计

**消息排队**：
- 模型思考时，你可以继续输入
- 消息自动排队，依次发送
- 不错过任何一个灵感

**工具调用可视化**：
- 实时显示工具名称、状态、计时器
- 每个工具调用独立追踪
- 完成后自动折叠为一行摘要："🔧 3 个工具已使用"

### 多模型 · 多平台 · 一键切换

- **10+ 供应商**：OpenAI、Anthropic、Google、DeepSeek、Kimi、MiniMax、小米、通义、xAI...
- **多平台集成**：Telegram、Discord、Slack、微信、QQ、飞书、WhatsApp...
- **一键切换模型**：点击顶栏即可切换，无需重启
- **配置可视化**：所有 API Key、平台状态一目了然

### 自动运维：你只管聊天

- 启动时自动检测并启动所有依赖服务
- 后台看门狗每 30 秒巡检，掉线自动重启
- 一键重连按钮，逐项检测并修复
- 你不需要知道什么是"端口"、什么是"进程"——Hermes Pulse 都替你管好了

---

## 🚀 快速开始

### 方式一：下载安装包（推荐）

从 [Releases](https://github.com/MINTSOLD/hermes-pulse/releases) 下载 `HermesPulse-1.0.0.zip`，解压后双击 `install.bat` 即可。

### 方式二：手动安装

```bash
# 前置条件
# - Windows 10/11
# - Python 3.11+
# - Hermes Agent 已安装 (pip install hermes-agent)

# 克隆仓库
git clone https://github.com/MINTSOLD/hermes-pulse.git
cd hermes-gui

# 安装依赖
pip install pywebview

# 启动
python hermes_gui.py
```

---

## 🏗️ 架构

```
┌─────────────────────────────────────────────┐
│           Hermes Pulse 窗口                  │
│        pywebview + WebView2 原生窗口         │
├──────────────────┬──────────────────────────┤
│    前端 (浏览器)   │      后端 (Python)        │
│                  │                          │
│  index.html      │   config_server.py       │
│  app.js    80KB  │   ├─ 静态文件服务 (:18765) │
│  styles.css 44KB │   ├─ 配置管理 API         │
│                  │   ├─ 网关代理 (:8642)      │
│  总计 < 200KB    │   └─ 服务看门狗            │
├──────────────────┴──────────────────────────┤
│              Hermes Gateway                  │
│            (AI 后端 :8642)                    │
└─────────────────────────────────────────────┘
```

---

## 📁 项目结构

```
hermes-pulse/
├── hermes_gui.py          # 桌面启动器（pywebview + 服务编排）
├── config_server.py       # 后端服务（配置 + 代理 + 看门狗）
├── index.html             # GUI 入口
├── app.js                 # 前端逻辑（流式输出、标签管理、智能滚动）
├── styles.css             # 视觉系统（呼吸光效、纯黑主题）
├── start_config_server.vbs # VBS 包装器（隐藏控制台）
├── hermes-logo.png        # 应用 Logo
├── hermes.ico             # 任务栏图标
├── hermes-titlebar.ico    # 标题栏图标
├── installer/             # 安装包脚本
├── screenshots/           # 界面截图
├── LICENSE                # MIT 许可证
└── README.md
```

---

## 🛠️ 技术栈

| 层级 | 技术 | 说明 |
|:---|:---|:---|
| 桌面窗口 | **pywebview + WebView2** | 原生 Windows 窗口，非 Electron |
| 前端 | **Vanilla HTML/CSS/JS** | 零框架，零打包，零 node_modules |
| 后端 | **Python ThreadingHTTPServer** | 单文件服务器，无第三方 Web 框架 |
| 动画 | **CSS @keyframes** | 10+ 独创呼吸光效动画 |
| 流式输出 | **SSE (Server-Sent Events)** | 实时逐字渲染 |
| 进程管理 | **subprocess + socket** | 自动启动、健康检查、看门狗 |

---

## 🗺️ 路线图

- [ ] 一键安装包（Inno Setup）
- [ ] 系统托盘常驻
- [ ] 会话导出（Markdown / PDF）
- [ ] 语音输入
- [ ] 插件系统
- [ ] 自定义主题色
- [ ] 多语言支持
- [ ] macOS / Linux 适配

---

## 🤝 参与贡献

我们欢迎任何形式的反馈！

- 🐛 **报告 Bug**：[提交 Issue](https://github.com/MINTSOLD/hermes-pulse/issues)
- 💡 **功能建议**：[发起 Discussion](https://github.com/MINTSOLD/hermes-pulse/discussions)
- 🔧 **提交代码**：Fork → Branch → PR
- ⭐ **给我们 Star**：这是最简单的支持方式

> *Hermes Pulse 是一个年轻的项目，你的每一个反馈都在塑造它的未来。*

---

## 📄 License

[MIT](LICENSE) © 2026 Hermes

---

<div align="center">

**轻于形 · 智于心**

</div>
