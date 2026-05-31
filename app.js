/* Hermes GUI - 简化版：不依赖任何插件 import */

const ICON_SEND = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>';
const ICON_STOP = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>';
let CACHED_PROVIDERS = [];
let CACHED_DEFAULT_MODEL = 'mimo-v2.5';

const state = {
  connected: false, currentModel: 'mimo-v2.5', currentSession: null,
  sessions: [], isGenerating: false, messages: [],
  abortController: null, messageQueue: [], isProcessingQueue: false,
  dashboardConnected: false, chatHistory: [], failReason: '', maxContext: 0,
  sessionId: 'gui-session-' + Date.now().toString(36),
  autoScroll: true,  // 用户未手动上滚时保持跟滚
};

// Tab management
let tabs = [{ id: 'tab-0', name: '新对话', chatHistory: [], totalPromptTokens: 0, completedTokens: 0, messagesHtml: '', sessionId: 'gui-session-' + Date.now().toString(36) }];
let currentTabIndex = 0;

function currentTab() { return tabs[currentTabIndex]; }

// ============================================
// 配置读取 — 直接用 window.__TAURI__
// ============================================

const CONFIG_SERVER = '';  // 同源，不需要完整 URL
let API_BASE = '/gateway';  // 通过 config_server 代理
let configServerRunning = false;

async function ensureConfigServer() {
  try {
    const resp = await fetch(`${CONFIG_SERVER}/health`, { signal: AbortSignal.timeout(2000) });
    if (resp.ok) { configServerRunning = true; return true; }
  } catch {}
  // 服务没运行，尝试启动
  try {
    const { invoke } = await import('@tauri-apps/api/core');
    await invoke('plugin:shell|execute', { program: 'python', args: ['scripts/config_server.py'], sidecar: false });
    await new Promise(r => setTimeout(r, 1500));
    const resp = await fetch(`${CONFIG_SERVER}/health`, { signal: AbortSignal.timeout(3000) });
    if (resp.ok) { configServerRunning = true; return true; }
  } catch {}
  configServerRunning = false;
  return false;
}

async function loadRealConfig() {
  if (!configServerRunning) await ensureConfigServer();
  try {
    const resp = await fetch(`${CONFIG_SERVER}/config`, { signal: AbortSignal.timeout(10000) });
    const data = await resp.json();
    CACHED_PROVIDERS = data.providers || [];
    CACHED_PRESETS = data.unconfigured_presets || [];
    CACHED_DEFAULT_MODEL = data.default_model || 'mimo-v2.5';
    state.gatewayApiKey = data.api_key || '';
    window.MODEL_PROVIDERS = CACHED_PROVIDERS.map(p => ({
      name: p.name, type: p.type, api_key_configured: p.api_key_configured, models: p.models,
    }));
    window.ALL_MODELS = CACHED_PROVIDERS.flatMap(p => p.models);
    console.log('[Hermes] 供应商数:', CACHED_PROVIDERS.length);
    return true;
  } catch (e) {
    console.error('[Hermes] 读取配置失败:', e);
    CACHED_PROVIDERS = []; CACHED_PRESETS = []; window.MODEL_PROVIDERS = []; window.ALL_MODELS = [];
    return false;
  }
}

async function discoverGateway() {
  try {
    const resp = await fetch(`${CONFIG_SERVER}/config`, { signal: AbortSignal.timeout(2000) });
    const data = await resp.json();
    if (data.hermes_dir) console.log('[Hermes] 配置目录:', data.hermes_dir);
  } catch {}
  // 网关地址始终通过 config_server 代理（同源）
  API_BASE = '/gateway';
}

function getModelName(id) { return (window.ALL_MODELS || []).find(m => m.id === id)?.name || id; }

// ============================================
// 初始化
// ============================================

document.addEventListener('DOMContentLoaded', async () => {
  initEventListeners();
  // 启动时自动连接
  await discoverGateway();
  await loadRealConfig();
  loadModels();
  loadSessions();
  await manualReconnect();
  // 每30秒自动检查连接状态
  setInterval(checkConnection, 30000);
});

function initEventListeners() {
  document.getElementById('btn-send').addEventListener('click', handleSendOrStop);
  document.getElementById('btn-settings')?.addEventListener('click', openSettings);

  const input = document.getElementById('message-input');
  const wrapper = document.getElementById('input-wrapper');
  input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendOrStop(); } });
  input.addEventListener('input', autoResize);
  input.addEventListener('focus', () => { wrapper.classList.add('focused'); document.getElementById('token-bar')?.classList.add('visible'); });
  input.addEventListener('blur', () => {
    setTimeout(() => {
      if (document.activeElement !== input) {
        wrapper.classList.remove('focused');
        // 有token用量时保持显示，否则隐藏
        const usage = document.getElementById('token-usage')?.textContent;
        if (!usage || usage === '0') document.getElementById('token-bar')?.classList.remove('visible');
      }
    }, 150);
  });

  document.getElementById('btn-new-chat')?.addEventListener('click', newChat);
  document.getElementById('btn-new-tab')?.addEventListener('click', newChat);
  document.getElementById('current-model')?.addEventListener('click', showModelModal);
  document.getElementById('btn-queue-send')?.addEventListener('click', sendQueuedMessages);
  document.getElementById('btn-queue-clear')?.addEventListener('click', clearQueue);
  document.getElementById('btn-reconnect')?.addEventListener('click', manualReconnect);

  // 智能滚动检测：监听 chat-area 滚动，判断用户是否手动上滚
  const chatArea = document.getElementById('chat-area');
  if (chatArea) {
    chatArea.addEventListener('scroll', () => {
      // 距离底部 50px 内视为"在底部"，开启跟滚
      const atBottom = chatArea.scrollHeight - chatArea.scrollTop - chatArea.clientHeight < 50;
      state.autoScroll = atBottom;
    });
  }

  // 上传按钮
  const uploadBtn = document.getElementById('btn-upload');
  if (uploadBtn) {
    // 创建隐藏的文件输入
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.multiple = true;
    fileInput.accept = 'image/*,.pdf,.txt,.md,.json,.csv,.py,.js,.ts,.html,.css';
    fileInput.style.display = 'none';
    fileInput.id = 'file-input';
    document.body.appendChild(fileInput);
    uploadBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileUpload);
  }

  // 拖拽上传
  const inputWrapper = document.getElementById('input-wrapper');
  if (inputWrapper) {
    ['dragenter', 'dragover'].forEach(evt => {
      inputWrapper.addEventListener(evt, (e) => { e.preventDefault(); e.stopPropagation(); inputWrapper.classList.add('drag-over'); });
    });
    ['dragleave', 'drop'].forEach(evt => {
      inputWrapper.addEventListener(evt, (e) => { e.preventDefault(); e.stopPropagation(); inputWrapper.classList.remove('drag-over'); });
    });
    inputWrapper.addEventListener('drop', (e) => {
      const files = e.dataTransfer?.files;
      if (files?.length) handleFileUpload({ target: { files } });
    });
  }

  // 点击弹窗空白处关闭（拖选文本时不关闭）
  document.getElementById('model-modal')?.addEventListener('click', (e) => {
    if (e.target.id === 'model-modal') {
      const sel = window.getSelection();
      if (sel && sel.toString().length > 0) return;
      closeModal('model-modal');
    }
  });
  // 滚轮穿透：在弹窗遮罩层滚动时，让内容区跟着滚
  document.getElementById('model-modal')?.addEventListener('wheel', (e) => {
    const body = document.querySelector('#modal-content .modal-body') || document.querySelector('#modal-content .config-body');
    if (!body) return;
    if (body.contains(e.target)) return;
    e.preventDefault();
    body.scrollTop += e.deltaY;
  }, { passive: false });

  // Key 输入完成后自动重新拉取模型
  document.getElementById('model-modal')?.addEventListener('change', (e) => {
    if (e.target.id === 'ap-key') {
      const url = document.getElementById('ap-url')?.value?.trim();
      const key = e.target.value?.trim();
      const modelSection = document.getElementById('ap-model-section');
      if (url && key && modelSection && modelSection.style.display !== 'none') {
        fetchProviderModels(url, key);
      }
    }
  });

  // 点击空白处清除文本选中（body user-select:none 会阻止默认清除行为）
  document.addEventListener('mousedown', (e) => {
    if (!e.target.closest('.message-content') && !e.target.closest('.message-bubble')) {
      const sel = window.getSelection();
      if (sel && sel.toString().length > 0) sel.removeAllRanges();
    }
  });
}

async function manualReconnect() {
  const btn = document.getElementById('btn-reconnect');
  const el = document.getElementById('connection-status');
  const dot = el?.querySelector('.status-dot');
  const text = el?.querySelector('.status-text');

  // 第一步：显示未连接
  state.connected = false;
  updateConnectionStatus();

  // 第二步：按钮持续旋转 + 显示检测中
  btn.classList.add('spinning');
  if (el) el.className = 'status-indicator connecting';
  if (dot) { dot.style.background = '#666666'; dot.style.animation = 'none'; }
  if (text) text.textContent = '检测所有服务配置...';
  btn?.classList.remove('connected');

  // 逐项检测并修复
  const steps = [
    { name: '配置服务', check: () => fetch(`${CONFIG_SERVER}/health`, { signal: AbortSignal.timeout(3000) }).then(r => r.ok).catch(() => false),
      fix: async () => { await startConfigServer(); } },
    { name: '网关', check: () => fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) }).then(r => r.json()).then(d => d.status === 'ok').catch(() => false),
      fix: async () => { await startGateway(); } },
    { name: '控制面板', check: async () => {
        try {
          const r = await fetch(`${CONFIG_SERVER}/health`, { signal: AbortSignal.timeout(3000) });
          const d = await r.json();
          return d.dashboard === true;
        } catch { return false; }
      },
      fix: async () => { await startDashboard(); } },
  ];

  for (const step of steps) {
    if (text) text.textContent = `检测 ${step.name}...`;
    await new Promise(r => setTimeout(r, 600)); // 保证用户能看到
    let ok = await step.check();
    if (!ok) {
      if (text) text.textContent = `修复 ${step.name}...`;
      try { await step.fix(); } catch {}
      await new Promise(r => setTimeout(r, 1500));
      ok = await step.check();
    }
  }

  // 第三步：最终检测
  if (text) text.textContent = '最终检测...';
  await new Promise(r => setTimeout(r, 800));
  await loadRealConfig();
  loadModels();
  await checkConnection();

  btn.classList.remove('spinning');
  // 提示显示在刷新按钮附近
  showToolbarToast(state.connected ? '已连接' : `连接失败: ${state.failReason || '服务不可用'}`);
}

// ============================================
// 自动修复：启动各服务
// ============================================

async function startConfigServer() {
  // config_server 已经在运行（因为这个页面就是它提供的）
  return true;
}

async function startGateway() {
  try {
    const r = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(2000) });
    if (r.ok) return true;
  } catch {}
  // 网关不在线 → 主动调用 config_server 的重启接口
  try {
    await fetch(`${CONFIG_SERVER}/restart_gateway`, {
      method: 'POST',
      signal: AbortSignal.timeout(10000),
    });
  } catch {}
  // 等待 Gateway 恢复（最多 20 秒）
  for (let i = 0; i < 20; i++) {
    await new Promise(r => setTimeout(r, 1000));
    try {
      const r = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(2000) });
      const d = await r.json();
      if (d.status === 'ok') return true;
    } catch {}
  }
  return false;
}

async function startDashboard() {
  try {
    const r = await fetch('http://127.0.0.1:9119/', { signal: AbortSignal.timeout(1000) });
    if (r.ok) return true;
  } catch {}
  // Dashboard 通常随 Hermes 主进程启动，尝试通过 config server
  try {
    await fetch(`${CONFIG_SERVER}/start_dashboard`, { method: 'POST', signal: AbortSignal.timeout(5000) });
  } catch {}
  for (let i = 0; i < 5; i++) {
    await new Promise(r => setTimeout(r, 1000));
    try {
      const r = await fetch('http://127.0.0.1:9119/', { signal: AbortSignal.timeout(2000) });
      if (r.ok) return true;
    } catch {}
  }
  return false;
}

// ============================================
// 发送/停止
// ============================================

function handleSendOrStop() {
  if (state.isGenerating) stopGeneration();
  else if (state.messageQueue.length > 0 && !state.isProcessingQueue) sendQueuedMessages();
  else sendMessage();
}

function updateSendButton() {
  const btn = document.getElementById('btn-send');
  if (state.isGenerating) { btn.innerHTML = ICON_STOP; btn.className = 'btn-send is-stop'; }
  else { btn.innerHTML = ICON_SEND; btn.className = 'btn-send'; }
}

// ============================================
// 连接
// ============================================

async function checkConnection() {
  let gatewayOk = false;
  let platformsOk = true;
  let dashboardOk = false;

  // 一次请求检查所有服务（config_server 的 /health 已代理检查 gateway + dashboard）
  try {
    const r = await fetch(`${CONFIG_SERVER}/health`, { signal: AbortSignal.timeout(5000) });
    const d = await r.json();
    gatewayOk = d.gateway === true;
    dashboardOk = d.dashboard === true;
  } catch {}

  // 如果 Gateway 掉线，自动触发一次修复（不阻塞 UI）
  if (!gatewayOk && !state._autoRepairing) {
    state._autoRepairing = true;
    startGateway().then(recovered => {
      state._autoRepairing = false;
      if (recovered) {
        checkConnection(); // 修复成功后重新检测
      }
    });
  }

  state.connected = gatewayOk && platformsOk && dashboardOk;
  state.dashboardConnected = dashboardOk;

  if (!state.connected) {
    let reason = [];
    if (!gatewayOk) reason.push('网关');
    if (!platformsOk) reason.push('消息平台');
    if (!dashboardOk) reason.push('控制面板');
    state.failReason = reason.join('、');
  } else {
    state.failReason = '';
  }

  updateConnectionStatus();
}

function updateConnectionStatus() {
  const el = document.getElementById('connection-status');
  const btn = document.getElementById('btn-reconnect');
  const footer = document.getElementById('global-footer');
  if (!el) return;
  const dot = el.querySelector('.status-dot');
  const text = el.querySelector('.status-text');
  if (state.connected) {
    el.className = 'status-indicator online';
    if (text) text.textContent = '已连接';
    if (dot) dot.style.background = '#fff';
    btn?.classList.add('connected');
    footer?.classList.add('connected');
  } else {
    el.className = 'status-indicator offline';
    if (text) text.textContent = state.failReason ? `未连接 · ${state.failReason}` : '未连接';
    if (dot) dot.style.background = '#333';
    btn?.classList.remove('connected');
    footer?.classList.remove('connected');
  }
}

// ============================================
// 模型管理
// ============================================

function loadModels() {
  state.currentModel = CACHED_DEFAULT_MODEL;
  document.querySelector('.model-name').textContent = getModelName(CACHED_DEFAULT_MODEL);
  updateTokenBar();
}

function formatTokens(n) {
  if (!n && n !== 0) return '--';
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return Math.round(n / 1000) + 'K';
  return String(n);
}

// 上下文长度数据库 — 与终端 hermes model 完全一致
const CONTEXT_MAP = {
  // 小米 MiMo
  'mimo-v2.5': 1048576, 'mimo-v2.5-pro': 1048576, 'mimo-v2-pro': 1048576,
  'mimo-v2-omni': 262144, 'mimo-v2-flash': 262144,
  // DeepSeek
  'deepseek-v4-flash': 1000000, 'deepseek-v4-pro': 1000000,
  'deepseek-chat': 1000000, 'deepseek-reasoner': 1000000, 'deepseek': 128000,
  // MiniMax
  'MiniMax-M2.7': 204800, 'MiniMax-M2.7-highspeed': 204800,
  'MiniMax-M2.5': 204800, 'MiniMax-M2.5-highspeed': 204800,
  'MiniMax-M2.1': 204800, 'MiniMax-M2': 204800,
  // Kimi
  'kimi-k2.6': 262144, 'kimi-k2.5': 262144,
  'kimi-k2-thinking': 262144, 'kimi-k2-thinking-turbo': 262144,
  'kimi-for-coding': 262144, 'kimi': 262144,
  // OpenAI
  'gpt-5.5': 1050000, 'gpt-5.4': 1050000, 'gpt-5': 400000,
  'gpt-4.1': 1047576, 'gpt-4': 128000,
  // Anthropic
  'claude-opus-4-7': 1000000, 'claude-sonnet-4-6': 1000000, 'claude': 200000,
  // Google
  'gemini': 1048576,
  // Qwen
  'qwen3.6-plus': 1048576, 'qwen3-coder-plus': 1000000,
  'qwen3-coder': 262144, 'qwen': 131072,
  // xAI
  'grok-4.20': 2000000, 'grok-4.3': 1000000, 'grok-4': 256000, 'grok': 131072,
  // GLM
  'glm': 202752,
  // NVIDIA
  'nemotron': 131072,
  // Meta
  'llama': 131072,
};

function getContextLength(modelId) {
  // 1. 精确匹配
  if (CONTEXT_MAP[modelId]) return CONTEXT_MAP[modelId];
  // 2. 子串匹配（从长到短，跟终端逻辑一致）
  const sorted = Object.entries(CONTEXT_MAP).sort((a, b) => b[0].length - a[0].length);
  for (const [key, val] of sorted) {
    if (modelId.toLowerCase().includes(key.toLowerCase())) return val;
  }
  return 0;
}

function updateTokenBar() {
  const ctxEl = document.getElementById('token-context');
  let ctx = 0;
  // 先从配置数据查
  const model = (window.ALL_MODELS || []).find(m => m.id === state.currentModel);
  if (model) ctx = model.context_length || model.max_tokens || model.ctx || 0;
  // 再从上下文数据库查（子串匹配）
  if (!ctx) ctx = getContextLength(state.currentModel);
  state.maxContext = ctx;
  // 显示格式：0/128K
  if (ctxEl) ctxEl.textContent = ctx ? `0/${formatTokens(ctx)}` : '--/--';
}

// 更新已用token（发送消息后调用）
function updateTokenUsage(used) {
  const ctxEl = document.getElementById('token-context');
  const ctx = state.maxContext || 0;
  if (ctxEl && ctx) {
    ctxEl.textContent = `${formatTokens(used)}/${formatTokens(ctx)}`;
  }
}

// 上下文压缩信息
function updateCompressionInfo(promptTokens, contextLength) {
  if (!contextLength) return '';
  const ratio = promptTokens / contextLength;
  if (ratio > 0.9) return '⚠️ 接近上限';
  if (ratio > 0.7) return '已压缩';
  return '';
}

function showModelModal() {
  const content = document.getElementById('modal-content');
  const modal = document.getElementById('model-modal');
  const providers = CACHED_PROVIDERS || [];
  const withKey = providers.filter(p => p.api_key_configured);
  const noKey = providers.filter(p => !p.api_key_configured);

  let html = `<div class="modal-header"><h3>选择模型</h3><button class="btn-close" onclick="closeModal('model-modal')">&times;</button></div><div class="modal-body">`;

  // 有 key 的供应商 — 默认折叠
  withKey.forEach(p => {
    html += `<div class="model-group collapsed"><div class="model-group-header" onclick="toggleGroup(this)"><span class="arrow">▾</span> ${p.name} <span class="key-badge key-ok">已配置</span><span class="group-count">${p.models.length} 个模型</span></div><div class="model-group-items" style="max-height:0px">`;
    p.models.forEach(m => {
      html += `<div class="model-item ${m.id===state.currentModel?'active':''}" onclick="selectModel('${m.id}','${m.name}')"><span class="model-id">${m.name}</span><span class="model-ctx">${m.id}</span></div>`;
    });
    html += `</div></div>`;
  });

  if (noKey.length > 0) {
    html += `<div class="modal-divider"></div>`;
    html += `<div style="padding:6px 12px;font-size:11px;color:#555;">未配置 Key 的供应商请到「模型配置」中添加</div>`;
  }

  html += `</div><div class="modal-footer"><button class="btn-config" onclick="showConfigView()">模型配置</button></div>`;
  content.innerHTML = html;
  modal.classList.remove('hidden');
}

function toggleGroup(h) {
  const g = h.parentElement;
  const items = g.querySelector('.model-group-items');
  const isCollapsed = g.classList.contains('collapsed');
  g.classList.toggle('collapsed');
  if (isCollapsed) {
    // 展开：设置实际高度
    items.style.maxHeight = items.scrollHeight + 'px';
    // 延迟修正为精确高度
    setTimeout(() => { items.style.maxHeight = items.scrollHeight + 'px'; }, 300);
  } else {
    // 折叠
    items.style.maxHeight = '0px';
  }
}

async function selectModel(id, name) {
  if (id === state.currentModel) { showModelActionDialog(id, name); return; }
  await applyModelChange(id, name);
}

function showModelActionDialog(id, name) {
  const content = document.getElementById('modal-content');
  const cur = getModelName(state.currentModel);
  content.innerHTML = `<div class="modal-header"><h3>${name}</h3><button class="btn-close" onclick="showModelModal()">&times;</button></div>
  <div class="modal-body" style="display:flex;flex-direction:column;align-items:center;padding:32px 20px;">
    <div style="font-size:13px;color:var(--text-secondary);margin-bottom:24px;text-align:center;">当前已使用 <strong>${cur}</strong></div>
    <div style="display:flex;gap:12px;width:100%;">
      <button class="btn-action btn-keep" onclick="closeModal('model-modal')"><span class="btn-action-label">保持</span><span class="btn-action-desc">不改变</span></button>
      <button class="btn-action btn-replace" onclick="selectModel('${id}','${name}')"><span class="btn-action-label">替换</span><span class="btn-action-desc">切换到此模型</span></button>
      <button class="btn-action btn-clear" onclick="clearModelSelection()"><span class="btn-action-label">清除</span><span class="btn-action-desc">恢复默认</span></button>
    </div>
  </div>`;
}

async function applyModelChange(id, name) {
  // 找到这个模型属于哪个 provider
  let providerName = '';
  for (const p of (CACHED_PROVIDERS || [])) {
    if ((p.models || []).some(m => m.id === id)) {
      providerName = p.name;
      break;
    }
  }
  // 内置供应商名映射到 Gateway 识别的 provider 标识
  const providerMap = {
    '小米': 'xiaomi', 'DeepSeek': 'deepseek', 'MiniMax': 'minimax',
    'MiniMax 国内': 'minimax-cn', 'NVIDIA': 'nvidia',
  };
  const gatewayProvider = providerMap[providerName] || providerName;

  // 立刻更新界面（不等待 Gateway 重启）
  state.currentModel = id;
  document.querySelector('.model-name').textContent = name || id;
  CACHED_DEFAULT_MODEL = id;
  currentTab().sessionId = 'gui-session-' + Date.now().toString(36);
  closeModal('model-modal');
  showToast(`已切换到 ${name || id}，正在连接...`);
  updateTokenBar();

  // 后台异步更新配置 + 重启 Gateway（不阻塞界面）
  fetch(`${CONFIG_SERVER}/set_default`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ model_id: id, provider: gatewayProvider }),
  }).catch(e => console.error('模型切换失败:', e));
}

   async function addProvider(name, baseUrl, apiKey, model) {
     try {
       const resp = await fetch(`${CONFIG_SERVER}/add_provider`, {
         method: 'POST', headers: {'Content-Type': 'application/json'},
         body: JSON.stringify({ name, base_url: baseUrl, api_key: apiKey, model }),
       });
       const data = await resp.json();
       if (data.error) {
         showToast(data.error);
         return;
       }
       showToast(`已添加 ${name}`);
       await loadRealConfig();
       showConfigView();
     } catch (e) { showToast(`添加失败`); }
   }

   // ============================================
   // 工具函数
   // ============================================

function showToast(message) {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();
  const target = document.getElementById('current-model');
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  // Position below the model selector
  if (target) {
    const rect = target.getBoundingClientRect();
    toast.style.position = 'fixed';
    toast.style.left = rect.left + 'px';
    toast.style.top = (rect.bottom + 8) + 'px';
    toast.style.transform = 'none';
  }
  document.body.appendChild(toast);
  requestAnimationFrame(() => { toast.style.opacity = '1'; toast.style.transform = 'translateY(0)'; });
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-8px)';
    setTimeout(() => toast.remove(), 300);
  }, 2000);
}

function showToolbarToast(message) {
  const el = document.getElementById('toolbar-toast');
  if (!el) return;
  el.textContent = message;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 3000);
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add('hidden');
}

function openSettings() {
  const panel = document.getElementById('settings-panel');
  if (panel) {
    panel.classList.remove('hidden');
    switchSettingsTab('dashboard');
  }
}

function closeSettings() {
  const panel = document.getElementById('settings-panel');
  if (panel) panel.classList.add('hidden');
}

// 设置面板标签切换
function switchSettingsTab(tab) {
  document.querySelectorAll('.settings-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.settings-content').forEach(c => c.classList.add('hidden'));
  const tabs = document.querySelectorAll('.settings-tab');
  if (tab === 'dashboard') {
    tabs[0]?.classList.add('active');
    document.getElementById('settings-dashboard')?.classList.remove('hidden');
    const frame = document.getElementById('dashboard-frame');
    if (frame && !frame.src.includes('9119')) frame.src = 'http://127.0.0.1:9119';
  } else if (tab === 'platforms') {
    tabs[1]?.classList.add('active');
    document.getElementById('settings-platforms')?.classList.remove('hidden');
    loadPlatformStatus().then(() => renderPlatforms());
  }
}

// 通信平台配置 — 完整列表（匹配 Hermes 终端支持的所有平台）
const PLATFORMS = [
  // ── 即时通讯 ──
  { id: 'telegram', name: 'Telegram', icon: '📱', category: '即时通讯', type: 'token',
    envKey: 'TELEGRAM_BOT_TOKEN',
    fields: [{ name: 'token', label: 'Bot Token', placeholder: '123456:ABC-DEF...' }],
    guide: '在 Telegram 搜索 @BotFather → /newbot → 获取 Token' },
  { id: 'discord', name: 'Discord', icon: '💬', category: '即时通讯', type: 'token',
    envKey: 'DISCORD_BOT_TOKEN',
    fields: [{ name: 'token', label: 'Bot Token', placeholder: 'MTEx...' }],
    guide: '访问 discord.com/developers → 创建 Application → Bot → 获取 Token' },
  { id: 'slack', name: 'Slack', icon: '💼', category: '即时通讯', type: 'multi',
    envKeys: { bot_token: 'SLACK_BOT_TOKEN', app_token: 'SLACK_APP_TOKEN' },
    fields: [
      { name: 'bot_token', label: 'Bot Token', placeholder: 'xoxb-...' },
      { name: 'app_token', label: 'App Token', placeholder: 'xapp-...' },
    ],
    guide: '访问 api.slack.com/apps → 创建 App → Bot Token + App Token' },
  { id: 'whatsapp', name: 'WhatsApp', icon: '📲', category: '即时通讯', type: 'toggle',
    envKeys: { enabled: 'WHATSAPP_ENABLED', allowed_users: 'WHATSAPP_ALLOWED_USERS' },
    fields: [
      { name: 'enabled', label: '启用 WhatsApp', default: 'true' },
      { name: 'allowed_users', label: '允许的用户 (手机号)', placeholder: '15551234567' },
    ],
    guide: 'WhatsApp Business API → developers.facebook.com' },
  { id: 'signal', name: 'Signal', icon: '🔒', category: '即时通讯', type: 'multi',
    envKeys: { http_url: 'SIGNAL_HTTP_URL', account: 'SIGNAL_ACCOUNT' },
    fields: [
      { name: 'http_url', label: 'Signal API URL', placeholder: 'http://localhost:8080' },
      { name: 'account', label: 'Signal 账号', placeholder: '+861****8000' },
    ],
    guide: '部署 signal-cli-rest-api 容器 → 注册号码' },
  // ── 企业协作 ──
  { id: 'teams', name: 'Microsoft Teams', icon: '🟦', category: '企业协作', type: 'multi',
    envKeys: { client_id: 'TEAMS_CLIENT_ID', client_secret: 'TEAMS_CLIENT_SECRET', tenant_id: 'TEAMS_TENANT_ID' },
    fields: [
      { name: 'client_id', label: 'Client ID', placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx' },
      { name: 'client_secret', label: 'Client Secret', placeholder: '请输入密钥值' },
      { name: 'tenant_id', label: 'Tenant ID', placeholder: 'xxxxxxxx 或 common' },
    ],
    guide: 'portal.azure.com → Azure AD → 注册应用 → 获取凭证' },
  { id: 'google_chat', name: 'Google Chat', icon: '🔴', category: '企业协作', type: 'multi',
    envKeys: { project_id: 'GOOGLE_CHAT_PROJECT_ID', subscription: 'GOOGLE_CHAT_SUBSCRIPTION_NAME', sa_json: 'GOOGLE_CHAT_SERVICE_ACCOUNT_JSON' },
    fields: [
      { name: 'project_id', label: 'GCP Project ID', placeholder: 'my-project-id' },
      { name: 'subscription', label: 'Pub/Sub 订阅名', placeholder: 'projects/id/subscriptions/name' },
      { name: 'sa_json', label: 'Service Account JSON 路径', placeholder: '/path/to/sa.json' },
    ],
    guide: 'Google Cloud Console → 创建项目 → Service Account → Pub/Sub' },
  { id: 'matrix', name: 'Matrix', icon: '🟢', category: '企业协作', type: 'multi',
    envKeys: { access_token: 'MATRIX_ACCESS_TOKEN', home_room: 'MATRIX_HOME_ROOM' },
    fields: [
      { name: 'access_token', label: 'Access Token', placeholder: 'syt_xxx...' },
      { name: 'home_room', label: 'Home Room ID', placeholder: '!room:server.org' },
    ],
    guide: 'Matrix 客户端 → 设置 → 关于 → 高级 → 获取 Access Token' },
  // ── 中国平台 ──
  { id: 'weixin', name: '个人微信', icon: '💚', category: '中国平台', type: 'qr',
    envKeys: { account_id: 'WEIXIN_ACCOUNT_ID', token: 'WEIXIN_TOKEN' },
    qr_api: 'https://ilinkai.weixin.qq.com/ilink/bot/get_bot_qrcode',
    poll_api: 'https://ilinkai.weixin.qq.com/ilink/bot/get_qrcode_status',
    guide: '点击获取二维码 → 微信扫码 → 自动连接' },
  { id: 'qqbot', name: 'QQ Bot', icon: '🐧', category: '中国平台', type: 'multi',
    envKeys: { app_id: 'QQ_APP_ID', app_secret: 'QQ_APP_SECRET' },
    fields: [
      { name: 'app_id', label: 'App ID', placeholder: '100123456' },
      { name: 'app_secret', label: 'App Secret', placeholder: '请输入 App Secret' },
    ],
    guide: '访问 q.qq.com → 创建机器人 → 获取 App ID 和 Secret' },
  { id: 'yuanbao', name: '腾讯元宝', icon: '🟡', category: '中国平台', type: 'multi',
    envKeys: { app_id: 'YUANBAO_APP_ID', app_secret: 'YUANBAO_APP_SECRET' },
    fields: [
      { name: 'app_id', label: 'App ID', placeholder: '请输入 App ID' },
      { name: 'app_secret', label: 'App Secret', placeholder: '请输入 App Secret' },
    ],
    guide: '访问 yuanbao.tencent.com → 创建 Bot → 获取凭证' },
];

// 平台状态缓存
let platformStatus = {};
let qrPollTimer = null;

async function loadPlatformStatus() {
  try {
    const resp = await fetch(`${CONFIG_SERVER}/get_platforms`);
    const data = await resp.json();
    platformStatus = data.platforms || {};
  } catch (e) { console.error('加载平台状态失败:', e); }
}

function renderPlatforms() {
  const list = document.getElementById('platforms-list');
  if (!list) return;
  // 按分类分组
  const categories = {};
  PLATFORMS.forEach(p => {
    const cat = p.category || '其他';
    if (!categories[cat]) categories[cat] = [];
    categories[cat].push(p);
  });
  let html = '';
  for (const [cat, platforms] of Object.entries(categories)) {
    html += `<div class="platform-section-title">${cat}</div>`;
    platforms.forEach(p => {
      const status = platformStatus[p.id] || {};
      const connected = status.has_token;
      const typeLabel = { token: 'Token', multi: '多字段', toggle: '开关', qr: '扫码' }[p.type] || '';
      html += `<div class="platform-card">`;
      html += `<div class="platform-card-header">`;
      html += `  <span class="platform-card-icon">${p.icon}</span>`;
      html += `  <span class="platform-card-name">${p.name}</span>`;
      html += `  <span class="platform-card-type">${typeLabel}</span>`;
      html += `  <span class="platform-card-status ${connected ? 'connected' : 'disconnected'}">${connected ? '已连接' : '未配置'}</span>`;
      html += `</div>`;
      if (p.guide) html += `<div class="platform-card-guide">💡 ${p.guide}</div>`;
      // 根据类型渲染不同 UI
      if (p.type === 'token') {
        html += renderTokenInputs(p, connected);
      } else if (p.type === 'multi') {
        html += renderMultiInputs(p, connected);
      } else if (p.type === 'toggle') {
        html += renderToggleInputs(p, connected);
      } else if (p.type === 'qr') {
        html += renderQrArea(p, connected);
      }
      html += `</div>`;
    });
  }
  list.innerHTML = html;
}

function renderTokenInputs(p, connected) {
  let html = '<div class="platform-card-fields">';
  p.fields.forEach(f => {
    html += `<div class="platform-field">
      <label class="platform-field-label">${f.label}</label>
      <div class="platform-field-row">
        <input type="text" class="platform-input" id="pf-${p.id}-${f.name}"
               placeholder="${f.placeholder || ''}" value="${connected ? '••••••••' : ''}" autocomplete="off" spellcheck="false" />
      </div>
    </div>`;
  });
  html += `<div class="platform-card-actions">
    <button class="platform-btn save" onclick="savePlatformConfig('${p.id}')">保存</button>`;
  if (connected) {
    html += ` <button class="platform-btn danger" onclick="clearPlatformConfig('${p.id}')">断开</button>`;
  }
  html += '</div></div>';
  return html;
}

function renderMultiInputs(p, connected) {
  let html = '<div class="platform-card-fields">';
  p.fields.forEach(f => {
    html += `<div class="platform-field">
      <label class="platform-field-label">${f.label}</label>
      <div class="platform-field-row">
        <input type="text" class="platform-input" id="pf-${p.id}-${f.name}"
               placeholder="${f.placeholder || ''}" value="${connected ? '••••••••' : ''}" autocomplete="off" spellcheck="false" />
      </div>
    </div>`;
  });
  html += `<div class="platform-card-actions">
    <button class="platform-btn save" onclick="savePlatformConfig('${p.id}')">保存</button>`;
  if (connected) {
    html += ` <button class="platform-btn danger" onclick="clearPlatformConfig('${p.id}')">断开</button>`;
  }
  html += '</div></div>';
  return html;
}

function renderToggleInputs(p, connected) {
  let html = '<div class="platform-card-fields">';
  p.fields.forEach(f => {
    if (f.name === 'enabled') {
      const isActive = connected || (f.default === 'true');
      html += `<div class="platform-toggle-row">
        <div class="platform-toggle ${isActive ? 'active' : ''}" id="toggle-${p.id}-${f.name}"
             onclick="this.classList.toggle('active')"></div>
        <span class="platform-toggle-label">${f.label}</span>
      </div>`;
    } else {
      html += `<div class="platform-field">
        <label class="platform-field-label">${f.label}</label>
        <div class="platform-field-row">
          <input type="text" class="platform-input" id="pf-${p.id}-${f.name}"
                 placeholder="${f.placeholder || ''}" autocomplete="off" spellcheck="false" />
        </div>
      </div>`;
    }
  });
  html += `<div class="platform-card-actions">
    <button class="platform-btn save" onclick="savePlatformConfig('${p.id}')">保存</button>
  </div></div>`;
  return html;
}

function renderQrArea(p, connected) {
  let html = `<div class="platform-card-fields">
    <div class="platform-qr-area">
      <div class="platform-qr-image" id="qr-container-${p.id}">${connected ? '✅ 已连接' : '点击下方按钮获取二维码'}</div>
      <div class="platform-qr-status ${connected ? 'confirmed' : ''}" id="qr-status-${p.id}">${connected ? '已连接' : '等待操作'}</div>
      <button class="platform-btn save" id="btn-qr-${p.id}" onclick="startQrLogin('${p.id}')">${connected ? '重新连接' : '获取二维码'}</button>
    </div>
  </div>`;
  return html;
}

async function savePlatformConfig(platformId) {
  const p = PLATFORMS.find(x => x.id === platformId);
  if (!p) return;
  const config = {};
  if (p.type === 'token') {
    const val = document.getElementById(`pf-${platformId}-token`)?.value?.trim();
    if (!val || val === '••••••••') { showToast('请输入 Token'); return; }
    config.token = val;
  } else if (p.type === 'multi') {
    p.fields.forEach(f => {
      const val = document.getElementById(`pf-${platformId}-${f.name}`)?.value?.trim();
      if (val && val !== '••••••••') config[f.name] = val;
    });
    if (Object.keys(config).length === 0) { showToast('请至少填写一个字段'); return; }
  } else if (p.type === 'toggle') {
    p.fields.forEach(f => {
      if (f.name === 'enabled') {
        const el = document.getElementById(`toggle-${platformId}-enabled`);
        config.enabled = el?.classList.contains('active') ? 'true' : 'false';
      } else {
        const val = document.getElementById(`pf-${platformId}-${f.name}`)?.value?.trim();
        if (val) config[f.name] = val;
      }
    });
  }
  try {
    const resp = await fetch(`${CONFIG_SERVER}/set_platform`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ platform_id: platformId, config }),
    });
    const data = await resp.json();
    if (data.ok) {
      showToast(`${p.name} 已保存，Gateway 重启中...`);
      await loadPlatformStatus();
      renderPlatforms();
      fetch(`${CONFIG_SERVER}/restart_gateway`, { method: 'POST' }).catch(() => {});
    } else {
      showToast(data.error || '保存失败');
    }
  } catch (e) { showToast('保存失败: ' + e.message); }
}

async function clearPlatformConfig(platformId) {
  const p = PLATFORMS.find(x => x.id === platformId);
  if (!p || !confirm(`确定要断开 ${p.name} 连接吗？`)) return;
  try {
    await fetch(`${CONFIG_SERVER}/set_platform`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ platform_id: platformId, config: { __clear__: true } }),
    });
    showToast(`${p.name} 已断开`);
    await loadPlatformStatus();
    renderPlatforms();
    fetch(`${CONFIG_SERVER}/restart_gateway`, { method: 'POST' }).catch(() => {});
  } catch (e) { showToast('断开失败'); }
}

// ── 微信二维码 ──
let qrStates = {};
async function startQrLogin(platformId) {
  const p = PLATFORMS.find(x => x.id === platformId);
  if (!p) return;
  const btn = document.getElementById(`btn-qr-${platformId}`);
  const container = document.getElementById(`qr-container-${platformId}`);
  const status = document.getElementById(`qr-status-${platformId}`);
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> 获取中...';
  status.textContent = '正在获取二维码...'; status.className = 'platform-qr-status';
  try {
    const resp = await fetch(`${CONFIG_SERVER}/qr_start`);
    const data = await resp.json();
    if (data.ok && data.qr_url) {
      container.innerHTML = ''; container.style.background = '#fff'; container.style.padding = '10px';
      new QRCode(container, { text: data.qr_url, width: 160, height: 160, colorDark: '#000', colorLight: '#fff' });
      status.textContent = '请用微信扫描二维码'; btn.style.display = 'none';
      qrStates[platformId] = { id: data.qr_id };
      pollQrStatus(platformId);
    } else {
      status.textContent = '获取失败: ' + (data.error || '');
      status.className = 'platform-qr-status error';
      btn.disabled = false; btn.textContent = '重试';
    }
  } catch (e) {
    status.textContent = '网络错误'; status.className = 'platform-qr-status error';
    btn.disabled = false; btn.textContent = '重试';
  }
}

function pollQrStatus(platformId) {
  qrPollTimer = setTimeout(async () => {
    try {
      const resp = await fetch(`${CONFIG_SERVER}/qr_poll`);
      const data = await resp.json();
      const status = document.getElementById(`qr-status-${platformId}`);
      const container = document.getElementById(`qr-container-${platformId}`);
      const btn = document.getElementById(`btn-qr-${platformId}`);
      if (!status) return;
      if (data.status === 'wait') { status.textContent = '等待扫码...'; pollQrStatus(platformId); }
      else if (data.status === 'scaned') { status.textContent = '已扫码，请在手机上确认'; status.className = 'platform-qr-status scanned'; pollQrStatus(platformId); }
      else if (data.status === 'confirmed') {
        status.textContent = '✅ 连接成功！'; status.className = 'platform-qr-status confirmed';
        showToast('个人微信 连接成功！');
        await fetch(`${CONFIG_SERVER}/set_platform`, { method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ platform_id: platformId, config: { account_id: data.account_id } }) });
        await loadPlatformStatus(); renderPlatforms();
      } else if (data.status === 'expired') {
        status.textContent = '二维码已过期'; status.className = 'platform-qr-status error';
        container.innerHTML = '<div style="padding:16px;text-align:center"><div style="font-size:32px;margin-bottom:6px">⏰</div><div style="font-size:11px;color:#666">已过期</div></div>';
        container.style.background = 'rgba(255,255,255,0.03)'; container.style.border = '1px dashed rgba(255,255,255,0.1)';
        btn.style.display = ''; btn.disabled = false; btn.textContent = '重新获取';
      }
    } catch { pollQrStatus(platformId); }
  }, 3000);
}

function clearModelSelection() {
  state.currentModel = CACHED_DEFAULT_MODEL;
  document.querySelector('.model-name').textContent = getModelName(CACHED_DEFAULT_MODEL);
  closeModal('model-modal');
  showToast('已恢复默认模型');
  updateTokenBar();
}

// 文件上传处理
const pendingFiles = [];
function handleFileUpload(e) {
  const files = e.target?.files || [];
  for (const file of files) {
    pendingFiles.push(file);
  }
  renderAttachments();
  showToast(`已添加 ${files.length} 个附件`);
}

function renderAttachments() {
  const area = document.getElementById('attachment-area');
  const list = document.getElementById('attachment-list');
  if (!area || !list) return;
  if (pendingFiles.length === 0) {
    area.classList.add('hidden');
    return;
  }
  area.classList.remove('hidden');
  list.innerHTML = pendingFiles.map((file, i) => {
    const isImage = file.type.startsWith('image/');
    const icon = isImage ? '' : '📄';
    const size = file.size > 1024 ? (file.size/1024).toFixed(1) + 'KB' : file.size + 'B';
    return `<div class="attachment-item">
      ${icon ? `<span>${icon}</span>` : ''}
      <span class="att-name">${file.name}</span>
      <span style="color:var(--text-muted);font-size:10px;">${size}</span>
      <button class="att-remove" onclick="removeAttachment(${i})">×</button>
    </div>`;
  }).join('');
}

function removeAttachment(index) {
  pendingFiles.splice(index, 1);
  renderAttachments();
}

function insertPrompt(text) {
  const input = document.getElementById('message-input');
  if (input) {
    input.value = text;
    input.focus();
    autoResize();
  }
}

function autoResize() {
  const input = document.getElementById('message-input');
  if (input) {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 200) + 'px';
  }
}

// ============================================
// 会话管理
// ============================================

async function loadSessions() {
  // Gateway 暂无 sessions 端点，显示空列表
  state.sessions = [];
  renderSessions();
}

function renderSessions() {
  // 无侧边栏，暂不渲染
}

function filterSessions() {
  // 无侧边栏，暂不渲染
}

async function switchSession(id) {
  state.currentSession = id;
  renderSessions();
}

async function deleteSession(id) {
  try {
    await fetch(`${API_BASE}/api/sessions/${id}`, { method: 'DELETE' });
    state.sessions = state.sessions.filter(s => s.id !== id);
    if (state.currentSession === id) state.currentSession = null;
    renderSessions();
  } catch {}
}

function newChat() {
  // Save current tab state first
  const msgEl = document.getElementById('messages');
  if (msgEl) {
    tabs[currentTabIndex].messagesHtml = msgEl.innerHTML;
    tabs[currentTabIndex].chatHistory = [...(state.chatHistory || [])];
    tabs[currentTabIndex].totalPromptTokens = state.totalPromptTokens || 0;
  }

  // Create a new tab
  const newId = 'tab-' + Date.now();
  const newTab = { id: newId, name: '新对话', chatHistory: [], totalPromptTokens: 0, completedTokens: 0, messagesHtml: '', sessionId: 'gui-session-' + Date.now().toString(36) };
  tabs.push(newTab);
  currentTabIndex = tabs.length - 1;

  // Reset shared state
  state.currentSession = null;
  state.messages = [];
  state.chatHistory = [];
  state.totalPromptTokens = 0;

  // Update UI
  if (msgEl) {
    msgEl.innerHTML = getWelcomeHtml();
  }
  updateTokenBar();
  renderTabBar();
}

function getWelcomeHtml() {
  return `<div id="welcome-screen" class="welcome-screen splash">
    <div class="splash-logo-wrap">
      <div class="splash-glow"></div>
      <img src="hermes-logo.png" class="splash-logo" alt="Hermes">
    </div>
    <h1 class="splash-title">Hermes</h1>
    <div class="splash-tagline">AI 智能助手</div>
    <div class="splash-line"></div>
    <div class="splash-status">选择模型 · 开始对话</div>
  </div>`;
}

function switchTab(index) {
  if (index < 0 || index >= tabs.length) return;
  // Save current tab state
  const msgEl = document.getElementById('messages');
  tabs[currentTabIndex].messagesHtml = msgEl.innerHTML;
  tabs[currentTabIndex].chatHistory = [...(state.chatHistory || [])];
  tabs[currentTabIndex].totalPromptTokens = state.totalPromptTokens || 0;

  currentTabIndex = index;
  const tab = currentTab();

  // Restore messages
  msgEl.innerHTML = tab.messagesHtml || getWelcomeHtml();

  // Restore chat state
  state.chatHistory = [...(tab.chatHistory || [])];
  state.totalPromptTokens = tab.totalPromptTokens || 0;

  // Update token bar
  updateTokenUsage(tab.totalPromptTokens);
  const usageEl = document.getElementById('token-usage');
  if (usageEl) usageEl.textContent = formatTokens(tab.completedTokens || 0);

  // Re-render tab bar
  renderTabBar();

  // 切换标签后滚到底部
  const ca = document.getElementById('chat-area');
  if (ca) requestAnimationFrame(() => { ca.scrollTop = ca.scrollHeight; });
}

function closeTab(index) {
  if (tabs.length <= 1) return; // Don't close last tab
  tabs.splice(index, 1);
  if (currentTabIndex >= tabs.length) currentTabIndex = tabs.length - 1;
  switchTab(currentTabIndex);
}

function renderTabBar() {
  const bar = document.getElementById('toolbar-tabs');
  if (!bar) return;
  // 保留 btn-new-tab 按钮
  const btn = document.getElementById('btn-new-tab');
  bar.innerHTML = '';
  tabs.forEach((tab, i) => {
    const div = document.createElement('div');
    div.className = 'tab' + (i === currentTabIndex ? ' active' : '');
    div.dataset.index = i;
    div.onclick = () => switchTab(i);
    div.innerHTML = `<span class="tab-name">${tab.name}</span>`;
    if (tabs.length > 1) {
      const close = document.createElement('span');
      close.className = 'tab-close';
      close.textContent = '×';
      close.onclick = (e) => { e.stopPropagation(); closeTab(i); };
      div.appendChild(close);
    }
    bar.appendChild(div);
  });
  bar.appendChild(btn);
}

// ============================================
// 自定义确认对话框（替代原生 confirm）
// ============================================

function showCustomConfirm(title, message) {
  return new Promise(resolve => {
    const overlay = document.createElement('div');
    overlay.className = 'confirm-overlay';
    overlay.innerHTML = `
      <div class="confirm-dialog">
        <div class="confirm-title">${title}</div>
        <div class="confirm-message">${message}</div>
        <div class="confirm-actions">
          <button class="confirm-btn confirm-cancel">取消</button>
          <button class="confirm-btn confirm-ok">确认</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add('visible'));

    const cleanup = (result) => {
      overlay.classList.remove('visible');
      setTimeout(() => overlay.remove(), 200);
      resolve(result);
    };

    overlay.querySelector('.confirm-cancel').onclick = () => cleanup(false);
    overlay.querySelector('.confirm-ok').onclick = () => cleanup(true);
    overlay.onclick = (e) => { if (e.target === overlay) cleanup(false); };
  });
}

// ============================================
// 配置视图
// ============================================

function showConfigView() {
  const content = document.getElementById('modal-content');
  const providers = CACHED_PROVIDERS || [];
  const withKey = providers.filter(p => p.api_key_configured);

  let html = `<div class="modal-header"><h3>模型配置</h3><button class="btn-close" onclick="showModelModal()">&larr;</button></div><div class="modal-body config-body">`;

  // 只显示有 key 的供应商，只留编辑/删除按钮，不展开模型
  withKey.forEach((p, idx) => {
    html += `<div class="config-provider" id="cp-${idx}" style="display:flex;align-items:center;justify-content:space-between;padding:10px 12px;border-bottom:1px solid rgba(255,255,255,0.05);">
      <div style="display:flex;align-items:center;gap:8px;">
        <span class="config-provider-name" style="font-size:13px;">${p.name}</span>
        <span style="font-size:11px;color:var(--text-muted);">${(p.models||[]).length} 个模型</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;">
        <button class="btn-edit-provider" onclick="editProvider('${p.name}')" title="编辑">✎</button>
        <button class="btn-del-provider" onclick="confirmRemoveKey('${p.name}','${p.type || 'builtin'}')" title="删除">×</button>
      </div>
    </div>`;
  });

  if (withKey.length === 0) {
    html += `<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:12px;">还没有配置任何供应商<br>在下方「添加新供应商」中添加</div>`;
  }

  html += `<div class="config-provider collapsed" id="cp-add">
      <div class="config-provider-header" onclick="toggleConfigGroup('cp-add')" style="color:var(--text-secondary);">
        <div style="display:flex;align-items:center;gap:6px;">
          <span class="arrow">▾</span>
          <span class="config-provider-name">+ 添加新供应商</span>
        </div>
      </div>
      <div class="config-provider-models" style="max-height:0px;overflow:hidden;transition:max-height 0.3s ease">
        <div id="add-provider-form" style="padding:8px 12px;">
          <select id="ap-select" onchange="onProviderSelect()" style="width:100%;margin-bottom:6px;">
            <option value="">选择供应商...</option>
            <option value="custom">自定义 (手动填写)</option>
          </select>
          <input type="text" id="ap-name" placeholder="供应商名称" style="display:none;width:100%;margin-bottom:6px;" />
          <input type="text" id="ap-url" placeholder="API 地址" style="width:100%;margin-bottom:6px;" />
          <input type="text" id="ap-key" placeholder="API Key" style="width:100%;margin-bottom:6px;" />
          <div id="ap-model-section" style="display:none">
            <div style="display:flex;gap:6px;align-items:center;margin-bottom:6px;">
              <select id="ap-model-select" style="flex:1"><option value="">点击拉取模型列表...</option></select>
              <button class="btn-fetch-models" onclick="refetchModels()" title="用 Key 重新拉取">🔄</button>
            </div>
            <input type="text" id="ap-model" placeholder="或手动输入模型 ID" style="width:100%;margin-bottom:6px;" />
          </div>
          <button class="btn-add-provider" onclick="handleAddProvider()" style="width:100%;margin-top:4px;">保存配置</button>
        </div>
      </div>
    </div>
  </div>`;
  content.innerHTML = html;
  initProviderSelect();
  document.getElementById('model-modal')?.classList.remove('hidden');
}

function toggleConfigGroup(id) {
  const el = document.getElementById(id);
  if (!el) return;
  const models = el.querySelector('.config-provider-models');
  const arrow = el.querySelector('.arrow');
  if (!models) return;
  const isCollapsed = el.classList.contains('collapsed');
  if (isCollapsed) {
    el.classList.remove('collapsed');
    models.style.maxHeight = models.scrollHeight + 'px';
    if (arrow) arrow.style.transform = 'rotate(0deg)';
    // 展开后自动滚动到可见区域
    setTimeout(() => {
      const modalBody = el.closest('.modal-body');
      if (modalBody) {
        const elBottom = el.offsetTop + el.offsetHeight;
        const visibleBottom = modalBody.scrollTop + modalBody.clientHeight;
        if (elBottom > visibleBottom) {
          modalBody.scrollTo({ top: elBottom - modalBody.clientHeight + 20, behavior: 'smooth' });
        }
      }
    }, 50);
  } else {
    el.classList.add('collapsed');
    models.style.maxHeight = '0px';
    if (arrow) arrow.style.transform = 'rotate(-90deg)';
  }
}

function editProvider(name) {
  const p = (CACHED_PROVIDERS || []).find(x => x.name === name);
  if (!p) return;
  const content = document.getElementById('modal-content');
  content.innerHTML = `
    <div class="modal-header"><h3>编辑 ${name}</h3><button class="btn-close" onclick="showConfigView()">←</button></div>
    <div class="modal-body config-body">
      <div class="config-field">
        <label>API 地址</label>
        <input type="text" id="ep-url" value="${p.base_url || ''}" placeholder="API 地址" />
      </div>
      <div class="config-field">
        <label>API Key</label>
        <input type="password" id="ep-key" value="${p.api_key || ''}" placeholder="API Key" />
      </div>
      <div class="config-field">
        <label>默认模型</label>
        <input type="text" id="ep-model" value="${p.models?.[0]?.id || ''}" placeholder="模型 ID" />
      </div>
      <div style="display:flex;gap:8px;margin-top:16px;">
        <button class="btn-add-provider" onclick="saveProviderEdit('${name}')" style="flex:1">保存</button>
        <button class="btn-add-provider" onclick="showConfigView()" style="flex:1;background:var(--bg-hover);color:var(--text-secondary)">取消</button>
      </div>
    </div>`;
}

async function saveProviderEdit(name) {
  const url = document.getElementById('ep-url')?.value?.trim();
  const key = document.getElementById('ep-key')?.value?.trim();
  const model = document.getElementById('ep-model')?.value?.trim();
  if (!url) { showToast('请填写 API 地址'); return; }
  try {
    // 先清除旧 key，再重新添加
    await fetch(`${CONFIG_SERVER}/remove_env_key`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ provider: name }),
    });
    if (key) {
      await fetch(`${CONFIG_SERVER}/add_provider`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ name, base_url: url, api_key: key, model: model || '' }),
      });
    }
    showToast(`已更新 ${name}`);
    await loadRealConfig();
    showConfigView();
  } catch (e) {
    showToast('保存失败');
  }
}

function handleAddProvider() {
  const sel = document.getElementById('ap-select');
  const val = sel?.value || '';

  const name = document.getElementById('ap-name')?.value?.trim() || document.getElementById('ap-select')?.selectedOptions?.[0]?.text || '';
  const url = document.getElementById('ap-url')?.value?.trim();
  const key = document.getElementById('ap-key')?.value?.trim();
  const model = document.getElementById('ap-model-select')?.value || document.getElementById('ap-model')?.value?.trim() || '';
  if (!name || name === '选择供应商...' || name === '自定义 (手动填写)') { showToast('请选择供应商'); return; }
  if (!url) { showToast('请填写 API 地址'); return; }
  // 收集全部 fallback 模型，逗号分隔
  const preset = (CACHED_PRESETS || []).find(p => p.name === name);
  let allModels = model || '';
  if (preset && preset.fallback) {
    const ids = preset.fallback.map(m => m.id);
    // 把用户选的放第一个
    if (model && ids.includes(model)) {
      ids.splice(ids.indexOf(model), 1);
      ids.unshift(model);
    }
    allModels = ids.join(',');
  }
  addProvider(name, url, key || '', allModels);
}



// 预设供应商列表（含 fallback 模型，API 查不到时自动使用）
// 供应商预设 — 从后端 API 动态获取，不再硬编码
let CACHED_PRESETS = [];

// 页面加载时填充供应商下拉
function initProviderSelect() {
  const sel = document.getElementById('ap-select');
  if (!sel) return;
  // 清空除前两项（占位符+自定义）以外的选项
  while (sel.options.length > 2) sel.remove(2);
  // 从后端 API 获取的未配置供应商列表
  (CACHED_PRESETS || []).forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.name;
    opt.textContent = p.name;
    sel.appendChild(opt);
  });
}

function onProviderSelect() {
  const sel = document.getElementById('ap-select');
  const nameInput = document.getElementById('ap-name');
  const urlInput = document.getElementById('ap-url');
  const modelSection = document.getElementById('ap-model-section');
  const val = sel?.value;

  if (!val || val === '') {
    if (nameInput) nameInput.style.display = 'none';
    if (urlInput) { urlInput.value = ''; urlInput.placeholder = 'API 地址'; urlInput.readOnly = false; }
    if (modelSection) modelSection.style.display = 'none';
    _lastFetchUrl = '';
    return;
  }

  if (val === 'custom') {
    if (nameInput) nameInput.style.display = '';
    if (urlInput) { urlInput.value = ''; urlInput.readOnly = false; }
    if (modelSection) modelSection.style.display = 'none';
    _lastFetchUrl = '';
    return;
  }

  const preset = (CACHED_PRESETS || []).find(p => p.name === val);
  if (preset) {
    if (nameInput) nameInput.style.display = 'none';
    if (urlInput) { urlInput.value = preset.url; urlInput.readOnly = false; }
    if (modelSection) modelSection.style.display = '';
    _lastFetchUrl = '';
    recalcAddHeight();
    // 先尝试无key拉取，失败后等用户输入key再拉
    fetchProviderModels(preset.url);
  }
}

function refetchModels() {
  const url = document.getElementById('ap-url')?.value?.trim();
  const key = document.getElementById('ap-key')?.value?.trim();
  if (!url) { showToast('请先选择供应商'); return; }
  if (!key) { showToast('请输入 API Key 后再拉取'); return; }
  fetchProviderModels(url, key);
}
let _lastFetchUrl = '';
async function fetchProviderModels(apiUrl, apiKey) {
  if (apiKey) _lastFetchUrl = '';
  if (!apiKey && apiUrl === _lastFetchUrl) return;
  _lastFetchUrl = apiUrl;
  const modelSelect = document.getElementById('ap-model-select');
  if (!modelSelect) return;
  modelSelect.innerHTML = '<option value="">拉取中...</option>';
  modelSelect.disabled = true;

  // 查找当前选中的供应商预设（用于 fallback）
  const preset = (CACHED_PRESETS || []).find(p => p.url === apiUrl);

  try {
    let url = `${CONFIG_SERVER}/fetch_models?url=${encodeURIComponent(apiUrl)}`;
    if (apiKey) url += `&key=${encodeURIComponent(apiKey)}`;
    const resp = await fetch(url, { signal: AbortSignal.timeout(8000) });
    const data = await resp.json();
    if (data.models && data.models.length > 0) {
      modelSelect.innerHTML = '<option value="">选择模型...</option>';
      data.models.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m.id;
        opt.textContent = m.name || m.id;
        modelSelect.appendChild(opt);
      });
      modelSelect.value = data.models[0].id;
      modelSelect.disabled = false;
      return;
    }
  } catch {}

  // API 查询失败，使用 fallback 模型列表
  if (preset && preset.fallback && preset.fallback.length > 0) {
    modelSelect.innerHTML = '<option value="">选择模型...</option>';
    preset.fallback.forEach(m => {
      const opt = document.createElement('option');
      opt.value = m.id;
      opt.textContent = m.name || m.id;
      modelSelect.appendChild(opt);
    });
    modelSelect.value = preset.fallback[0].id;
  } else {
    modelSelect.innerHTML = '<option value="">未获取到模型，请手动输入下方</option>';
  }
  modelSelect.disabled = false;
  // 模型列表变化后重新计算折叠容器高度
  recalcAddHeight();
}

function recalcAddHeight() {
  setTimeout(() => {
    const cpAdd = document.getElementById('cp-add');
    const models = cpAdd?.querySelector('.config-provider-models');
    if (models && !cpAdd?.classList.contains('collapsed')) {
      models.style.maxHeight = models.scrollHeight + 'px';
    }
  }, 30);
}

async function confirmRemoveKey(name, type) {
  const confirmed = await showCustomConfirm('删除供应商', `确定要删除 ${name} 吗？删除后将不再显示，需要时可重新添加。`);
  if (!confirmed) return;

  // 立刻从界面移除（不等待后端）
  showToast(`已删除 ${name}`);
  showConfigView();

  // 后台异步删除
  fetch(`${CONFIG_SERVER}/delete_provider`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ name, type: type || 'builtin' }),
  }).then(() => loadRealConfig()).catch(e => console.error('删除失败:', e));
}

// ============================================
// 发送/停止
// ============================================

function sendMessage() {
  const input = document.getElementById('message-input');
  const text = input?.value?.trim();
  if (!text) return;
  if (!state.connected) {
    showToast(state.failReason ? `未连接 · ${state.failReason}不可用` : '未连接到网关');
    return;
  }

  state.isGenerating = true;
  updateSendButton();

  const messagesEl = document.getElementById('messages');
  const chatAreaEl = document.getElementById('chat-area');
  const welcome = document.getElementById('welcome-screen');
  if (welcome) welcome.remove();
  // 用户发消息时强制开启跟滚，确保新内容第一时间可见
  state.autoScroll = true;
  messagesEl.insertAdjacentHTML('beforeend', `<div class="message message-user"><div class="message-bubble"><div class="message-content">${text}</div></div></div>`);
  // 自动命名标签页：第一条消息时，用消息内容前15个字作为标签名
  const tab = currentTab();
  if (state.chatHistory.length === 0 && tab.name === '新对话') {
    const clean = text.replace(/\s+/g, ' ').trim();
    tab.name = clean.length > 15 ? clean.slice(0, 15) + '…' : clean;
    renderTabBar();
  }
  // 创建助手消息容器（含思考指示器 + 系统事件区 + 内容区）
  messagesEl.insertAdjacentHTML('beforeend', `<div class="message message-assistant">
    <div class="avatar"><img src="hermes-logo.png" alt="Hermes"></div>
    <div class="message-bubble">
      <div class="system-events"></div>
      <div class="thinking"><div class="thinking-dots"><span></span><span></span><span></span></div><span>思考中...</span></div>
      <div class="message-content"></div>
    </div>
  </div>`);
  // 等待 DOM 渲染完成后再滚动，确保用户消息可见
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      chatAreaEl.scrollTop = chatAreaEl.scrollHeight;
    });
  });

  // Use lastElementChild to get the just-added element (avoids duplicate ID issue)
  const streamingMsg = messagesEl.lastElementChild;
  state._streamingContentEl = streamingMsg.querySelector('.message-content');
  state._streamingEventsEl = streamingMsg.querySelector('.system-events');
  state._thinkingEl = streamingMsg.querySelector('.thinking');

  input.value = '';
  autoResize();
  renderAttachments(); // 清空附件显示

  state.abortController = new AbortController();

  // 使用 OpenAI 兼容格式 — 流式
  const chatMessages = [];
  if (state.chatHistory) {
    state.chatHistory.forEach(msg => chatMessages.push(msg));
  }
  // 构建消息内容（含附件信息）
  let content = text;
  if (pendingFiles.length > 0) {
    const fileNames = pendingFiles.map(f => f.name).join(', ');
    content += `\n\n[附件: ${fileNames}]`;
    pendingFiles.length = 0; // 清空
  }
  chatMessages.push({ role: 'user', content });

  fetch(`${API_BASE}/v1/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Hermes-Session-Id': currentTab().sessionId || state.sessionId,
      ...(state.gatewayApiKey ? { 'Authorization': `Bearer ${state.gatewayApiKey}` } : {}),
    },
    body: JSON.stringify({
      model: state.currentModel || 'hermes-agent',
      messages: chatMessages,
      stream: true,
    }),
    signal: state.abortController.signal,
  }).then(response => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullReply = '';

    function processChunk() {
      // 检查是否已取消
      if (state.abortController?.signal?.aborted) {
        state.isGenerating = false;
        updateSendButton();
        return;
      }
      reader.read().then(({ done, value }) => {
        if (done) {
          finishStream(fullReply);
          return;
        }
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // 保留不完整的行

        let currentEventType = '';
        for (const line of lines) {
          const trimmed = line.trim();
          // Bug 3: Detect SSE event type lines
          if (trimmed.startsWith('event:')) {
            currentEventType = trimmed.slice(6).trim();
            continue;
          }
          if (!trimmed || !trimmed.startsWith('data:')) continue;
          const data = trimmed.slice(5).trim();
          if (data === '[DONE]') {
            finishStream(fullReply);
            return;
          }
          try {
            const parsed = JSON.parse(data);
            // Bug 3: Pass SSE event type to handleStreamEvent
            if (currentEventType) {
              parsed._sseEvent = currentEventType;
              currentEventType = '';
            }
            handleStreamEvent(parsed);
            // 提取内容
            const delta = parsed.choices?.[0]?.delta;
            if (delta?.content) {
              fullReply += delta.content;
              updateStreamContent(fullReply);
            }
            // 提取 usage（最后一个 chunk 可能带）
            if (parsed.usage) {
              state._pendingUsage = parsed.usage;
            }
          } catch {}
        }
        processChunk();
      }).catch(err => {
        if (err.name !== 'AbortError') {
          showError(err.message);
        }
        state.isGenerating = false;
        updateSendButton();
      });
    }

    function handleStreamEvent(parsed) {
      const event = parsed._sseEvent || parsed.event || parsed.type;
      const systemEvents = state._streamingEventsEl;
      if (!systemEvents) return;

      // Gateway 的工具进度事件 (hermes.tool.progress)
      if (event === 'hermes.tool.progress' || event === 'tool.progress') {
        const toolName = parsed.tool || parsed.function_name || parsed.name || '工具';
        const status = parsed.status || 'running';
        const label = parsed.label || parsed.tool;
        const toolMap = {
          'web_search': '搜索网页', 'search': '搜索信息', 'read_file': '读取文件',
          'write_file': '写入文件', 'terminal': '执行命令', 'shell': '执行命令',
          'browser_navigate': '打开网页', 'browser_snapshot': '截图分析',
          'browser_click': '点击元素', 'browser_type': '输入文本',
          'delegate_task': '子任务调度', 'memory': '检索记忆',
          'patch': '修改文件', 'skill_view': '加载技能', 'skills_list': '查看技能',
        };
        const cnName = toolMap[toolName] || label || toolName;
        if (status === 'running') {
          addSystemEvent(systemEvents, '🔧', `调用 ${cnName}`);
        } else if (status === 'completed') {
          // 更新已有事件，停止计时
          if (!updateSystemEvent(systemEvents, cnName, '✅', `${cnName} 完成`)) {
            addSystemEvent(systemEvents, '✅', `${cnName} 完成`);
          }
        }
        return;
      }

      // Tool calls (legacy format)
      const toolName = parsed.tool_name || parsed.function_name || parsed.name || parsed.tool;
      if (event === 'tool_call' || event === 'tool_use' || toolName) {
        const name = toolName || '工具';
        const toolMap = {
          'web_search': '搜索网页', 'search': '搜索信息', 'read_file': '读取文件',
          'write_file': '写入文件', 'terminal': '执行命令', 'shell': '执行命令',
          'browser': '浏览器操作', 'delegate_task': '子任务调度', 'memory': '检索记忆',
          'patch': '修改文件', 'skill_view': '加载技能',
        };
        const cnName = toolMap[name] || name;
        addSystemEvent(systemEvents, '🔧', `调用 ${cnName}`);
        return;
      }
      if (event === 'thinking' || event === 'reasoning') {
        addSystemEvent(systemEvents, '🧠', '推理中...');
        return;
      }
      if (event === 'search' || event === 'web_search') {
        addSystemEvent(systemEvents, '🔍', '搜索网页中...');
        return;
      }
      if (event === 'compressing') {
        addSystemEvent(systemEvents, '📦', '压缩上下文...');
        return;
      }
      if (event === 'status' || event === 'info') {
        const msg = parsed.message || parsed.text || '';
        if (msg) addSystemEvent(systemEvents, 'ℹ️', msg);
        return;
      }
    }

    function addSystemEvent(container, icon, text) {
      const existing = container.querySelector('.sys-event:last-child');
      // 防重复：如果最后一个事件文本相同就跳过
      if (existing && existing.querySelector('.sys-event-text')?.textContent === text) return;
      const el = document.createElement('div');
      el.className = 'sys-event';
      const startTime = Date.now();
      el.innerHTML = `<span class="sys-event-icon">${icon}</span><span class="sys-event-text">${text}</span><span class="sys-event-timer">0s</span>`;
      container.appendChild(el);
      // 每秒更新计时
      const timer = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const timerEl = el.querySelector('.sys-event-timer');
        if (timerEl) timerEl.textContent = elapsed + 's';
      }, 1000);
      el._timer = timer;
      if (state.autoScroll) chatAreaEl.scrollTop = chatAreaEl.scrollHeight;
    }

    // 更新已有事件（工具完成时停止计时）
    function updateSystemEvent(container, textMatch, newIcon, newText) {
      const events = container.querySelectorAll('.sys-event');
      for (const el of events) {
        const textEl = el.querySelector('.sys-event-text');
        if (textEl && textEl.textContent.includes(textMatch)) {
          // 停止计时器
          if (el._timer) { clearInterval(el._timer); el._timer = null; }
          // 更新显示
          const iconEl = el.querySelector('.sys-event-icon');
          const timerEl = el.querySelector('.sys-event-timer');
          if (iconEl) iconEl.textContent = newIcon;
          if (textEl) textEl.textContent = newText;
          if (timerEl) timerEl.style.opacity = '0.5';
          return true;
        }
      }
      return false;
    }

    function updateThinkingIndicator(text) {
      const thinking = state._thinkingEl;
      if (thinking) {
        const span = thinking.querySelector('span:last-child');
        if (span) span.textContent = text;
      }
    }

    function updateStreamContent(text) {
      const contentEl = state._streamingContentEl;
      const thinking = state._thinkingEl;
      const systemEvents = state._streamingEventsEl;
      if (contentEl) {
        contentEl.innerHTML = text;
        // 有内容后隐藏思考指示器
        if (thinking && text.length > 0) thinking.style.display = 'none';
        // 处理文件路径链接
        processFileLinks(contentEl);
      }
      // Bug 2: Estimate tokens during streaming (rough: 1 token ≈ 3 chars)
      const prevTokens = tabs[currentTabIndex]?.completedTokens || 0;
      const estimatedNew = Math.ceil(text.length / 3);
      const totalEstimated = prevTokens + estimatedNew;
      const usageEl = document.getElementById('token-usage');
      if (usageEl && totalEstimated > 0) {
        usageEl.textContent = formatTokens(totalEstimated);
      }
      // 仅在用户未手动上滚时跟滚
      if (state.autoScroll) {
        chatAreaEl.scrollTop = chatAreaEl.scrollHeight;
      }
    }

    function finishStream(fullReply) {
      const thinking = state._thinkingEl;
      if (thinking) thinking.remove();
      const contentEl = state._streamingContentEl;
      if (contentEl && !fullReply) {
        contentEl.innerHTML = '<span style="color:var(--text-muted);">无回复</span>';
      }

      // 停止所有系统事件计时器
      const systemEvents = state._streamingEventsEl;
      if (systemEvents) {
        systemEvents.querySelectorAll('.sys-event').forEach(el => {
          if (el._timer) clearInterval(el._timer);
        });
        // 折叠工具/事件区：生成摘要行，然后折叠
        const toolEvents = systemEvents.querySelectorAll('.sys-event');
        if (toolEvents.length > 0) {
          // 统计工具调用次数
          const toolCount = [...toolEvents].filter(el => {
            const t = el.querySelector('.sys-event-text')?.textContent || '';
            return t.startsWith('调用 ');
          }).length;
          const summary = document.createElement('div');
          summary.className = 'sys-summary';
          summary.innerHTML = `<span class="sys-summary-icon">🔧</span><span>${toolCount > 0 ? `${toolCount} 个工具已使用` : `${toolEvents.length} 个事件`}</span>`;
          systemEvents.prepend(summary);
        }
        systemEvents.classList.add('collapsed');
      }

      // 保存历史
      if (!state.chatHistory) state.chatHistory = [];
      state.chatHistory.push({ role: 'user', content: text });
      state.chatHistory.push({ role: 'assistant', content: fullReply });

      // Bug 2: Update token usage - replace estimated value with real one
      const usage = state._pendingUsage;
      if (usage) {
        const prompt = usage.prompt_tokens || 0;
        const total = usage.total_tokens || 0;
        state.totalPromptTokens = prompt;
        const usageEl = document.getElementById('token-usage');
        if (usageEl) usageEl.textContent = formatTokens(total);
        updateTokenUsage(state.totalPromptTokens);
        const ctx = state.maxContext || 0;
        const compressEl = document.getElementById('token-compress');
        if (compressEl) compressEl.textContent = updateCompressionInfo(state.totalPromptTokens, ctx);
      }
      document.getElementById('token-bar')?.classList.add('visible');

      // Save tab state
      tabs[currentTabIndex].messagesHtml = messagesEl.innerHTML;
      tabs[currentTabIndex].chatHistory = [...state.chatHistory];
      tabs[currentTabIndex].totalPromptTokens = state.totalPromptTokens;
      tabs[currentTabIndex].completedTokens = state.totalPromptTokens;

      state.isGenerating = false;
      updateSendButton();
      delete state._pendingUsage;

      // 智能滚动：吐完字后滚回助手回复的开头，方便用户从头阅读
      if (state.autoScroll) {
        setTimeout(() => {
          const assistantMsgs = messagesEl.querySelectorAll('.message-assistant');
          const lastAssistantMsg = assistantMsgs[assistantMsgs.length - 1];
          if (lastAssistantMsg) {
            lastAssistantMsg.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
          // 滚动完成后重新检测（因为 scrollIntoView 可能改变了滚动位置）
          setTimeout(() => {
            const ca = document.getElementById('chat-area');
            if (ca) {
              const atBottom = ca.scrollHeight - ca.scrollTop - ca.clientHeight < 50;
              state.autoScroll = atBottom;
            }
          }, 400);
        }, 100);
      }
    }

    function showError(message) {
      const thinking = state._thinkingEl;
      if (thinking) thinking.remove();
      const contentEl = state._streamingContentEl;
      if (contentEl) {
        contentEl.innerHTML = `<span style="color:var(--text-muted);">发送失败: ${message}</span>`;
      }
    }

    processChunk();
  }).catch(e => {
    if (e.name !== 'AbortError') {
      // 显示错误（showError 在 .then 内部，这里直接处理）
      const thinking = state._thinkingEl;
      if (thinking) thinking.remove();
      const contentEl = state._streamingContentEl;
      if (contentEl) {
        contentEl.innerHTML = `<span style="color:var(--text-muted);">发送失败: ${e.message}</span>`;
      }
    } else {
      // 用户手动停止，移除思考指示器
      const thinking = state._thinkingEl;
      if (thinking) thinking.remove();
    }
    state.isGenerating = false;
    updateSendButton();
  });
}

function stopGeneration() {
  if (state.abortController) {
    state.abortController.abort();
    state.abortController = null;
  }
  // 移除思考指示器
  const thinking = state._thinkingEl;
  if (thinking) thinking.remove();
  // 停止所有系统事件计时器
  const events = state._streamingEventsEl;
  if (events) {
    events.querySelectorAll('.sys-event').forEach(el => {
      if (el._timer) clearInterval(el._timer);
    });
  }
  state.isGenerating = false;
  updateSendButton();
  showToast('已停止生成');
}

async function sendQueuedMessages() {
  if (state.messageQueue.length === 0) return;
  state.isProcessingQueue = true;
  while (state.messageQueue.length > 0) {
    const msg = state.messageQueue.shift();
    const input = document.getElementById('message-input');
    if (input) input.value = msg;
    sendMessage();
    await new Promise(r => setTimeout(r, 1000));
    while (state.isGenerating) await new Promise(r => setTimeout(r, 200));
  }
  state.isProcessingQueue = false;
  renderQueue();
}

function clearQueue() {
  state.messageQueue = [];
  renderQueue();
}

function renderQueue() {
  const area = document.getElementById('queue-area');
  const list = document.getElementById('queue-list');
  if (!area || !list) return;
  if (state.messageQueue.length === 0) {
    area.classList.add('hidden');
    return;
  }
  area.classList.remove('hidden');
  list.innerHTML = state.messageQueue.map((msg, i) => `
    <div class="queue-item">
      <span class="queue-item-index">${i + 1}</span>
      <span class="queue-item-text">${msg}</span>
      <button class="queue-item-remove" onclick="removeQueueItem(${i})">×</button>
    </div>
  `).join('');
}

function removeQueueItem(index) {
  state.messageQueue.splice(index, 1);
  renderQueue();
}

// ============================================
// 文件查看器（MD / TXT）
// ============================================

function openFileViewer(filename, content) {
  const viewer = document.getElementById('file-viewer');
  const titleEl = document.getElementById('file-viewer-title');
  const contentEl = document.getElementById('file-viewer-content');
  if (!viewer || !contentEl) return;

  titleEl.textContent = filename;
  const ext = filename.split('.').pop().toLowerCase();

  if (ext === 'md' || ext === 'markdown') {
    contentEl.innerHTML = renderMarkdown(content);
    contentEl.className = '';
  } else {
    contentEl.textContent = content;
    contentEl.className = 'file-viewer-text';
  }

  viewer.classList.remove('hidden');
}

function closeFileViewer() {
  const viewer = document.getElementById('file-viewer');
  if (viewer) viewer.classList.add('hidden');
}

// 点击遮罩关闭
document.addEventListener('DOMContentLoaded', () => {
  const viewer = document.getElementById('file-viewer');
  if (viewer) {
    viewer.addEventListener('click', (e) => {
      if (e.target === viewer) closeFileViewer();
    });
  }
});
// ESC 键关闭文件查看器
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeFileViewer();
});

// 通过路径打开远程文件（从 config_server 获取）
async function openFileByPath(filepath) {
  try {
    const resp = await fetch(`/read_file?path=${encodeURIComponent(filepath)}`);
    const data = await resp.json();
    if (data.error) { showFileToast('打开失败: ' + data.error); return; }
    openFileViewer(data.filename, data.content);
  } catch (e) {
    showFileToast('打开失败: ' + e.message);
  }
}
// 深色 Toast 通知（替代原生 alert）
function showFileToast(msg) {
  const existing = document.querySelector('.file-toast');
  if (existing) existing.remove();
  const t = document.createElement('div');
  t.className = 'file-toast';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.classList.add('show'), 10);
  setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, 3000);
}
// 处理消息中的文件路径，使其可点击打开
function processFileLinks(container) {
  const textNodes = [];
  const walk = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  while (walk.nextNode()) textNodes.push(walk.currentNode);

  textNodes.forEach(node => {
    const text = node.textContent;
    if (!text.match(/\.(md|txt|markdown)/i)) return;
    const parent = node.parentNode;
    if (parent.tagName === 'A' || parent.classList?.contains('file-link') || parent.tagName === 'CODE') return;

    // 匹配 file:// URL 和裸路径
    const combined = text.replace(
      /(?:file:\/\/\/|)([A-Za-z]:\/[^ \t<>"]+?\.(md|txt|markdown))/gi,
      (match, filepath) => {
        // 解码 URL 编码（%20 → 空格）
        const decoded = filepath.replace(/%20/g, ' ');
        return `<span class="file-link" onclick="openFileByPath('${decoded.replace(/'/g, "\\'")}')" title="点击查看: ${decoded}">${decoded}</span>`;
      }
    );
    if (combined !== text) {
      const span = document.createElement('span');
      span.innerHTML = combined;
      parent.replaceChild(span, node);
    }
  });
}

// 简易 Markdown → HTML 渲染器
function renderMarkdown(md) {
  let html = md
    // 代码块
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    // 行内代码
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // 标题
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // 粗体和斜体
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // 链接
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
    // 引用
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    // 水平线
    .replace(/^---$/gm, '<hr>')
    // 无序列表
    .replace(/^[*\-+] (.+)$/gm, '<li>$1</li>')
    // 换行
    .replace(/\n/g, '<br>');

  // 包裹连续的 <li> 为 <ul>
  html = html.replace(/(<li>.*?<\/li>(<br>)?)+/g, (match) => {
    return '<ul>' + match.replace(/<br>/g, '') + '</ul>';
  });

  // 清理多余的 <br>
  html = html.replace(/<br>(<\/?(h[1-3]|ul|ol|li|blockquote|pre|hr))/g, '$1');
  html = html.replace(/(<\/?(h[1-3]|ul|ol|li|blockquote|pre|hr)[^>]*>)<br>/g, '$1');

  return html;
}
