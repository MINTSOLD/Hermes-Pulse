#!/usr/bin/env python3
"""Hermes GUI 配置服务 - 实时查询供应商 API 获取真实模型列表"""
import json, os, re, sys, urllib.request, urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor, as_completed

qr_states = {}

HERMES_DIR = Path.home() / "AppData" / "Local" / "hermes"
PORT = 18765

# ── 从 models.dev 动态加载全部供应商（与终端同步）──
def _load_providers_from_models_dev():
    """从 models_dev_cache.json 加载全部供应商，与 Hermes 终端完全同步"""
    cache_path = HERMES_DIR / "models_dev_cache.json"
    # 额外的手动覆盖（models.dev 没有的供应商）
    manual_overrides = {
        "xiaomi": {"name": "MiMo", "env_key": "XIAOMI_API_KEY", "api": "https://token-plan-cn.xiaomimimo.com/v1"},
        "minimax-cn": {"name": "MiniMax 国内", "env_key": "MINIMAX_CN_API_KEY", "api": "https://api.minimax.chat/v1"},
        "ark": {"name": "火山引擎 Ark", "env_key": "ARK_API_KEY", "api": "https://ark.cn-beijing.volces.com/api/coding/v1"},
    }
    providers = []
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
            raw = cache.get("providers", cache) if isinstance(cache, dict) else {}
            for pid, info in raw.items():
                if not isinstance(info, dict):
                    continue
                # 跳过 OAuth 类型的供应商（需要特殊登录流程）
                if pid in ("nous", "openai-codex", "xai-oauth", "qwen-oauth", "google-gemini-cli",
                           "copilot-acp", "github-copilot", "minimax-oauth", "bedrock"):
                    continue
                name = info.get("name", pid)
                api = info.get("api", "")
                # 从 env 字段提取 API key 环境变量
                env_field = info.get("env", info.get("api_key_env", ""))
                if isinstance(env_field, list):
                    env_key = env_field[0] if env_field else ""
                elif isinstance(env_field, str):
                    env_key = env_field
                else:
                    env_key = str(env_field) if env_field else ""
                # 手动覆盖
                override = manual_overrides.get(pid, {})
                providers.append({
                    "name": override.get("name", name),
                    "env_key": override.get("env_key", env_key),
                    "api": override.get("api", api),
                    "fallback": [],
                })
        except Exception as e:
            print(f"[ConfigServer] 加载 models.dev 缓存失败: {e}")
    # 手动覆盖：替换 models.dev 中同名条目，或追加新的
    for pid, ov in manual_overrides.items():
        replaced = False
        for i, p in enumerate(providers):
            # 按 env_key 匹配替换（如 xiaomi → MiMo）
            if p.get("env_key") == ov["env_key"]:
                providers[i] = {"name": ov["name"], "env_key": ov["env_key"], "api": ov["api"], "fallback": []}
                replaced = True
                break
        if not replaced:
            providers.append({"name": ov["name"], "env_key": ov["env_key"], "api": ov["api"], "fallback": []})
    # 去重：同 env_key 只保留第一个
    seen_keys = set()
    deduped = []
    for p in providers:
        ek = p.get("env_key", "")
        if ek and ek in seen_keys:
            continue
        if ek:
            seen_keys.add(ek)
        deduped.append(p)
    providers = deduped
    # 用 .env 的 BASE_URL 覆盖（如 XIAOMI_BASE_URL, DEEPSEEK_BASE_URL 等）
    env_keys = read_env()
    for p in providers:
        ek = p.get("env_key", "")
        if ek:
            # XIAOMI_API_KEY → XIAOMI_BASE_URL
            prefix = ek.replace("_API_KEY", "").replace("_TOKEN", "")
            base_url = env_keys.get(f"{prefix}_BASE_URL", "")
            if base_url:
                p["api"] = base_url
    # 排序：有 key 的在前，按名称排序
    providers.sort(key=lambda p: (not bool(env_keys.get(p.get("env_key", ""), "")), p["name"]))
    return providers


def read_env():
    p = HERMES_DIR / ".env"
    if not p.exists(): return {}
    keys = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line: continue
        k, v = line.split("=", 1)
        keys[k.strip()] = v.strip()
    return keys

# ── 加载全部供应商（read_env 之后才能调用）──
PROVIDERS = _load_providers_from_models_dev()

def read_config():
    p = HERMES_DIR / "config.yaml"
    return p.read_text(encoding="utf-8") if p.exists() else ""

def get_hidden_providers(env_keys):
    hidden = env_keys.get("HIDDEN_PROVIDERS", "")
    return [h.strip() for h in hidden.split(",") if h.strip()]

def set_hidden_providers(hidden_list):
    env_path = HERMES_DIR / ".env"
    env = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    if hidden_list:
        hidden_str = ",".join(hidden_list)
        if "HIDDEN_PROVIDERS=" in env:
            env = re.sub(r"^HIDDEN_PROVIDERS=.*$", f"HIDDEN_PROVIDERS={hidden_str}", env, flags=re.MULTILINE)
        else:
            env += f"\nHIDDEN_PROVIDERS={hidden_str}"
    else:
        # 列表为空时删除整行，保持 .env 干净
        env = re.sub(r"^HIDDEN_PROVIDERS=.*\n?", "", env, flags=re.MULTILINE)
    env_path.write_text(env.strip() + "\n", encoding="utf-8")

def fetch_models_from_api(api_url, api_key):
    if not api_url or not api_key: return None
    try:
        req = urllib.request.Request(f"{api_url}/models", headers={"Authorization": f"Bearer {api_key}"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = []
            for m in data.get("data", []):
                mid = m.get("id", "")
                if mid and not mid.endswith(("-tts", "-tts-voiceclone", "-tts-voicedesign")):
                    ctx = m.get("context_length") or m.get("max_context_len") or m.get("max_tokens") or 0
                    if not ctx:
                        km = re.search(r'(\d+)k', mid, re.IGNORECASE)
                        if km: ctx = int(km.group(1)) * 1024
                    entry = {"id": mid, "name": mid}
                    if ctx: entry["context_length"] = ctx
                    models.append(entry)
            return models if models else None
    except urllib.error.HTTPError as e:
        if e.code in (401, 403): return None  # 需要key/禁止访问，静默
        print(f"[ConfigServer] {api_url} 查询失败: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[ConfigServer] {api_url} 查询异常: {e}", file=sys.stderr)
        return None

def build_providers(env_keys, hidden_providers=None):
    if hidden_providers is None:
        hidden_providers = set()
    providers = []
    def query_provider(p):
        if p["name"] in hidden_providers:
            return None
        key = env_keys.get(p["env_key"], "")
        if not key:
            return {"name": p["name"], "type": "builtin", "api_key_configured": False, "models": p["fallback"]}
        real_models = fetch_models_from_api(p["api"], key)
        if real_models:
            fallback_ctx = {m["id"]: m.get("context_length", 0) for m in p["fallback"] if isinstance(m, dict)}
            for m in real_models:
                if not m.get("context_length") and m["id"] in fallback_ctx:
                    m["context_length"] = fallback_ctx[m["id"]]
            models = real_models
        else:
            models = p["fallback"]
        return {"name": p["name"], "type": "builtin", "api_key_configured": True, "models": models}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(query_provider, p): p["name"] for p in PROVIDERS}
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                providers.append(result)
    name_order = {p["name"]: i for i, p in enumerate(PROVIDERS)}
    providers.sort(key=lambda x: name_order.get(x["name"], 999))
    return providers

def parse_custom_providers(config_text):
    providers = []
    m = re.search(r"custom_providers:([\s\S]*?)(?=\n\w|\Z)", config_text)
    if not m: return providers
    for block in re.split(r"^- ", m.group(1), flags=re.MULTILINE):
        if not block.strip(): continue
        def get(key):
            match = re.search(rf"{key}:\s*['\"]?([^'\"]*?)['\"]?\s*$", block, re.MULTILINE)
            return match.group(1).strip() if match else ""
        name, model_str, base_url, api_key = get("name"), get("model"), get("base_url"), get("api_key")
        if model_str:
            # 支持逗号分隔的多模型: "kimi-k2.6,kimi-k2.5,kimi-for-coding"
            model_ids = [m.strip() for m in model_str.split(",") if m.strip()]
            real_models = fetch_models_from_api(base_url, api_key) if base_url and api_key else None
            if real_models:
                models = real_models
            elif len(model_ids) > 1:
                # 逗号分隔的多模型，全部作为 fallback
                models = [{"id": mid, "name": mid} for mid in model_ids]
            else:
                models = [{"id": model_ids[0], "name": model_ids[0]}] if model_ids else []
            providers.append({"name": name or model_str, "type": "custom", "api_key_configured": bool(api_key), "models": models})
    return providers

def build_response():
    env_keys = read_env()
    hidden = set(get_hidden_providers(env_keys))
    config = read_config()
    providers = build_providers(env_keys, hidden)
    providers.extend(parse_custom_providers(config))
    def_match = re.search(r"default:\s*['\"]?([^'\s\"]+)", config)
    # 未配置的供应商预设（供前端"添加新供应商"下拉框用）
    unconfigured = []
    configured_names = {p["name"] for p in providers if p.get("api_key_configured")}
    for preset in PROVIDERS:
        if preset["name"] not in configured_names:
            unconfigured.append({"name": preset["name"], "url": preset["api"], "env_key": preset["env_key"], "fallback": preset.get("fallback", [])})
    # Gateway API key for session continuity
    api_key = env_keys.get("API_SERVER_KEY", "")
    return json.dumps({"providers": providers, "unconfigured_presets": unconfigured, "default_model": def_match.group(1) if def_match else "mimo-v2.5", "hermes_dir": str(HERMES_DIR), "api_key": api_key}, ensure_ascii=False)

class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_GET(self):
        # 静态文件服务 — GUI 资源 (同源，无 CORS 问题)
        GUI_DIR = Path(__file__).parent
        static_map = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/app.js": ("app.js", "application/javascript; charset=utf-8"),
            "/styles.css": ("styles.css", "text/css; charset=utf-8"),
            "/hermes-logo.png": ("hermes-logo.png", "image/png"),
        }
        # 去掉查询参数 (?v=6 等)
        clean_path = self.path.split("?")[0]
        if clean_path in static_map:
            fname, ctype = static_map[clean_path]
            fpath = GUI_DIR / fname
            if fpath.exists():
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Cache-Control", "no-cache")
                self._cors()
                self.end_headers()
                self.wfile.write(fpath.read_bytes())
                return

        if self.path == "/config":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.end_headers()
            self.wfile.write(build_response().encode("utf-8"))
        elif self.path == "/health":
            # 同时检查 Gateway 和 Dashboard 是否可达
            gateway_ok = False
            dashboard_ok = False
            try:
                req = urllib.request.Request("http://127.0.0.1:8642/health")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read())
                    gateway_ok = data.get("status") == "ok"
            except:
                pass
            try:
                req = urllib.request.Request("http://127.0.0.1:9119/")
                urllib.request.urlopen(req, timeout=2)
                dashboard_ok = True
            except:
                pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "dashboard": dashboard_ok, "gateway": gateway_ok}).encode())
        elif self.path.startswith("/gateway/"):
            # 代理 Gateway GET 请求
            real_path = self.path[len("/gateway"):]
            self._proxy_to_gateway(real_path, method="GET")
            return
        elif self.path.startswith("/fetch_models"):
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            url = params.get("url", [""])[0]
            api_key = params.get("key", [""])[0]
            models = []
            try:
                req = urllib.request.Request(f"{url}/models")
                if api_key:
                    req.add_header("Authorization", f"Bearer {api_key}")
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    for m in data.get("data", []):
                        mid = m.get("id", "")
                        if mid:
                            models.append({"id": mid, "name": mid})
            except urllib.error.HTTPError as e:
                if e.code not in (401, 403):  # 需要key/禁止访问，静默处理
                    print(f"[ConfigServer] {url} 查询失败: {e}")
            except Exception as e:
                print(f"[ConfigServer] {url} 查询异常: {e}")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps({"models": models}, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/get_platforms":
            # 读取所有平台的配置状态（支持多字段）
            env_keys = read_env()
            platform_env_map = {
                'telegram': ['TELEGRAM_BOT_TOKEN'],
                'discord': ['DISCORD_BOT_TOKEN'],
                'slack': ['SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN'],
                'whatsapp': ['WHATSAPP_ENABLED', 'WHATSAPP_ALLOWED_USERS'],
                'signal': ['SIGNAL_HTTP_URL', 'SIGNAL_ACCOUNT'],
                'teams': ['TEAMS_CLIENT_ID', 'TEAMS_CLIENT_SECRET', 'TEAMS_TENANT_ID'],
                'google_chat': ['GOOGLE_CHAT_PROJECT_ID', 'GOOGLE_CHAT_SUBSCRIPTION_NAME', 'GOOGLE_CHAT_SERVICE_ACCOUNT_JSON'],
                'matrix': ['MATRIX_ACCESS_TOKEN', 'MATRIX_HOME_ROOM'],
                'weixin': ['WEIXIN_ACCOUNT_ID', 'WEIXIN_TOKEN'],
                'qqbot': ['QQ_APP_ID', 'QQ_APP_SECRET'],
                'yuanbao': ['YUANBAO_APP_ID', 'YUANBAO_APP_SECRET'],
            }
            platforms = {}
            for pid, keys in platform_env_map.items():
                has_token = any(bool(env_keys.get(k, '')) for k in keys)
                platforms[pid] = {"has_token": has_token, "env_keys": keys}
            self._json_response({"platforms": platforms})

        elif self.path == "/qr_start":
            try:
                req = urllib.request.Request('https://ilinkai.weixin.qq.com/ilink/bot/get_bot_qrcode?bot_type=3')
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read())
                    qr_id = data.get('qrcode', '')
                    qr_url = data.get('qrcode_img_content', '')
                    qr_states['weixin'] = {'id': qr_id, 'status': 'waiting', 'url': qr_url}
                    self._json_response({'ok': True, 'qr_url': qr_url, 'qr_id': qr_id})
            except Exception as e:
                self._json_response({'ok': False, 'error': str(e)})

        elif self.path == "/qr_poll":
            state = qr_states.get('weixin', {})
            if state.get('status') == 'waiting':
                try:
                    req = urllib.request.Request(f'https://ilinkai.weixin.qq.com/ilink/bot/get_qrcode_status?qrcode={state["id"]}')
                    with urllib.request.urlopen(req, timeout=35) as resp:
                        data = json.loads(resp.read())
                        status = data.get('status', 'wait')
                        if status == 'confirmed':
                            state['status'] = 'confirmed'
                            state['account_id'] = data.get('ilink_bot_id', '')
                            state['token'] = data.get('bot_token', '')
                            self._json_response({'status': 'confirmed', 'account_id': state['account_id']})
                        else:
                            self._json_response({'status': status})
                except Exception:
                    self._json_response({'status': 'wait'})
            else:
                self._json_response({'status': state.get('status', 'idle')})
        elif self.path.startswith("/read_file"):
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            filepath = params.get("path", [""])[0]
            if not filepath:
                self._json_response({"error": "missing path parameter"}, 400)
                return
            try:
                p = Path(filepath)
                if not p.exists():
                    self._json_response({"error": "file not found"}, 404)
                    return
                if p.stat().st_size > 1_000_000:
                    self._json_response({"error": "file too large (>1MB)"}, 413)
                    return
                content = p.read_text(encoding="utf-8", errors="replace")
                self._json_response({"filename": p.name, "content": content})
            except Exception as e:
                self._json_response({"error": str(e)}, 500)

        else:
            self.send_response(404)
            self._cors()
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if self.path.startswith("/gateway/"):
            # 代理 Gateway POST 请求（含 Authorization 头转发）
            real_path = self.path[len("/gateway"):]
            auth = self.headers.get("Authorization", "")
            self._proxy_to_gateway(real_path, method="POST", body=body,
                                   headers={"Authorization": auth} if auth else None)
            return

        if self.path == "/add_provider":
            name, base_url, api_key, model = body.get("name",""), body.get("base_url",""), body.get("api_key",""), body.get("model","")
            config_path, env_path = HERMES_DIR / "config.yaml", HERMES_DIR / ".env"
            config = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
            # 检查是否与内置供应商重复
            builtin_names = {p["name"] for p in PROVIDERS}
            if name in builtin_names:
                self._json_response({"ok": False, "error": f"供应商 '{name}' 已存在（内置）"})
                return
            # 检查是否与自定义供应商重复
            existing_custom = re.findall(r"- name:\s*['\"]?([^'\"\n]+)", config)
            if name in existing_custom:
                self._json_response({"ok": False, "error": f"供应商 '{name}' 已存在（自定义）"})
                return
            new_block = f"\n- name: '{name}'\n  base_url: '{base_url}'\n  api_key: '{api_key}'\n  model: '{model}'"
            if "custom_providers:" in config:
                idx = config.index("custom_providers:") + len("custom_providers:")
                config = config[:idx] + new_block + config[idx:]
            else:
                config += f"\ncustom_providers:{new_block}"
            config_path.write_text(config, encoding="utf-8")
            if api_key:
                env_key = f"{name.upper().replace(' ', '_').replace('-', '_')}_API_KEY"
                env = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
                if f"{env_key}=" not in env:
                    env += f"\n{env_key}={api_key}"
                    env_path.write_text(env, encoding="utf-8")
            self._json_response({"ok": True})

        elif self.path == "/remove_provider":
            name = body.get("name", "")
            config_path = HERMES_DIR / "config.yaml"
            if config_path.exists():
                config = config_path.read_text(encoding="utf-8")
                lines, new_lines, skip = config.split("\n"), [], False
                for line in lines:
                    if line.strip().startswith("- name:") and name in line: skip = True
                    elif line.strip().startswith("- ") and skip: skip = False
                    if not skip: new_lines.append(line)
                config_path.write_text("\n".join(new_lines), encoding="utf-8")
            self._json_response({"ok": True})

        elif self.path == "/set_default":
            model_id = body.get("model_id", "")
            provider = body.get("provider", "")
            config_path = HERMES_DIR / "config.yaml"
            if config_path.exists():
                config = config_path.read_text(encoding="utf-8")
                config = re.sub(r"(default:\s*['\"]?)[^'\s\"']+", rf"\g<1>{model_id}", config)
                # 同时更新 provider
                if provider:
                    if re.search(r"provider:\s*['\"]?\w", config[:300]):
                        # 有 provider，替换（兼容有/无 base_url）
                        config = re.sub(r"(default:\s*['\"]?[^'\s\\\"]+\n\s*)provider:\s*['\"]?[^'\s\\\"]+", rf"\g<1>provider: {provider}", config)
                    else:
                        # model 段没有 provider，插入
                        config = re.sub(r"(default:\s*['\"]?[^'\s\"']+)", rf"\g<1>\n  provider: {provider}", config)
                config_path.write_text(config, encoding="utf-8")
            # 重启 Gateway 让配置生效
            import subprocess, time
            try:
                subprocess.run(["sc", "stop", "HermesGateway"], capture_output=True, timeout=10)
                time.sleep(2)
                # 杀掉残留进程
                result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=5)
                for line in result.stdout.split("\n"):
                    if ":8642" in line and "LISTENING" in line:
                        pid = line.split()[-1]
                        subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=5)
                        break
                time.sleep(1)
                subprocess.run(["sc", "start", "HermesGateway"], capture_output=True, timeout=10)
            except Exception:
                pass
            self._json_response({"ok": True})

        elif self.path == "/set_env_key":
            key, value = body.get("key", ""), body.get("value", "")
            if key and value:
                env_path = HERMES_DIR / ".env"
                env = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
                if f"{key}=" in env:
                    env = re.sub(rf"^{re.escape(key)}=.*$", f"{key}={value}", env, flags=re.MULTILINE)
                else:
                    env += f"\n{key}={value}"
                env_path.write_text(env, encoding="utf-8")
            self._json_response({"ok": True})

        elif self.path == "/remove_env_key":
            # 支持两种参数：key（env变量名）或 provider（显示名）
            key = body.get("key", "")
            provider_name = body.get("provider", "")
            # 如果传的是 provider 显示名，映射到 env_key
            if provider_name and not key:
                for p in PROVIDERS:
                    if p["name"] == provider_name:
                        key = p["env_key"]
                        break
            if key:
                env_path = HERMES_DIR / ".env"
                if env_path.exists():
                    env = env_path.read_text(encoding="utf-8")
                    env = re.sub(rf"^{re.escape(key)}=.*\n?", "", env, flags=re.MULTILINE)
                    env_path.write_text(env, encoding="utf-8")
            self._json_response({"ok": True})

        elif self.path == "/delete_provider":
            name = body.get("name", "")
            provider_type = body.get("type", "builtin")
            env_keys = read_env()
            if provider_type == "builtin":
                # 内置供应商：加入隐藏列表
                hidden = get_hidden_providers(env_keys)
                if name not in hidden:
                    hidden.append(name)
                set_hidden_providers(hidden)
                # 同时清除 API key
                for p in PROVIDERS:
                    if p["name"] == name:
                        env_path = HERMES_DIR / ".env"
                        if env_path.exists():
                            env = env_path.read_text(encoding="utf-8")
                            env = re.sub(rf"^{re.escape(p['env_key'])}=.*\n?", "", env, flags=re.MULTILINE)
                            env_path.write_text(env, encoding="utf-8")
                        break
            else:
                # 自定义供应商：从 config.yaml 删除 + 清除 API key
                config_path = HERMES_DIR / "config.yaml"
                if config_path.exists():
                    config = config_path.read_text(encoding="utf-8")
                    lines, new_lines, skip = config.split("\n"), [], False
                    for line in lines:
                        if line.strip().startswith("- name:") and name in line:
                            skip = True
                        elif line.strip().startswith("- ") and skip:
                            skip = False
                        if not skip:
                            new_lines.append(line)
                    config_path.write_text("\n".join(new_lines), encoding="utf-8")
                # 清除自定义供应商的 API key
                env_path = HERMES_DIR / ".env"
                if env_path.exists():
                    env = env_path.read_text(encoding="utf-8")
                    env_key = f"{name.upper().replace(' ', '_').replace('-', '_')}_API_KEY"
                    env = re.sub(rf"^{re.escape(env_key)}=.*\n?", "", env, flags=re.MULTILINE)
                    env_path.write_text(env, encoding="utf-8")
            self._json_response({"ok": True})

        elif self.path == "/unhide_provider":
            name = body.get("name", "")
            env_keys = read_env()
            hidden = get_hidden_providers(env_keys)
            hidden = [h for h in hidden if h != name]
            set_hidden_providers(hidden)
            self._json_response({"ok": True})

        elif self.path == "/fetch_models":
            # 从供应商 API 拉取模型列表
            url = body.get("url", "")
            if not url:
                self._json_response({"models": [], "error": "no url"})
                return
            models = []
            try:
                req = urllib.request.Request(f"{url}/models")
                api_key = body.get("key", "")
                if api_key:
                    req.add_header("Authorization", f"Bearer {api_key}")
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    for m in data.get("data", []):
                        mid = m.get("id", "")
                        if mid:
                            models.append({"id": mid, "name": mid})
            except urllib.error.HTTPError as e:
                if e.code != 401:  # 401=需要key，静默处理
                    print(f"[ConfigServer] {url} 查询失败: {e}")
            except Exception as e:
                print(f"[ConfigServer] {url} 查询异常: {e}")
            self._json_response({"models": models})

        elif self.path == "/restart_gateway":
            import subprocess
            try:
                # 用 pythonw + 完整路径避免弹黑窗口
                hermes_main = os.path.join(str(HERMES_DIR), "hermes-agent", "venv", "Scripts", "pythonw.exe")
                script = os.path.join(str(HERMES_DIR), "hermes-agent", "hermes_cli", "main.py")
                subprocess.Popen(
                    [hermes_main, script, "gateway", "restart"],
                    creationflags=0x08000000,  # CREATE_NO_WINDOW
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                self._json_response({"ok": True})
            except Exception as e:
                self._json_response({"ok": False, "error": str(e)})

        elif self.path == "/start_dashboard":
            import subprocess
            try:
                hermes_main = os.path.join(str(HERMES_DIR), "hermes-agent", "venv", "Scripts", "pythonw.exe")
                script = os.path.join(str(HERMES_DIR), "hermes-agent", "hermes_cli", "main.py")
                subprocess.Popen(
                    [hermes_main, script, "dashboard"],
                    creationflags=0x08000000,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                self._json_response({"ok": True})
            except Exception as e:
                self._json_response({"ok": False, "error": str(e)})

        elif self.path == "/set_platform":
            # 保存平台配置（支持多字段 + 清除）
            platform_id = body.get("platform_id", "")
            config = body.get("config", {})
            env_path = HERMES_DIR / ".env"
            env = env_path.read_text(encoding="utf-8") if env_path.exists() else ""

            if config.get("__clear__"):
                # 清除：注释掉该平台所有 env key
                platform_clear_map = {
                    'telegram': ['TELEGRAM_BOT_TOKEN'],
                    'discord': ['DISCORD_BOT_TOKEN'],
                    'slack': ['SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN'],
                    'whatsapp': ['WHATSAPP_ENABLED', 'WHATSAPP_ALLOWED_USERS'],
                    'signal': ['SIGNAL_HTTP_URL', 'SIGNAL_ACCOUNT'],
                    'teams': ['TEAMS_CLIENT_ID', 'TEAMS_CLIENT_SECRET', 'TEAMS_TENANT_ID'],
                    'google_chat': ['GOOGLE_CHAT_PROJECT_ID', 'GOOGLE_CHAT_SUBSCRIPTION_NAME', 'GOOGLE_CHAT_SERVICE_ACCOUNT_JSON'],
                    'matrix': ['MATRIX_ACCESS_TOKEN', 'MATRIX_HOME_ROOM'],
                    'weixin': ['WEIXIN_ACCOUNT_ID', 'WEIXIN_TOKEN'],
                    'qqbot': ['QQ_APP_ID', 'QQ_APP_SECRET'],
                    'yuanbao': ['YUANBAO_APP_ID', 'YUANBAO_APP_SECRET'],
                }
                for key in platform_clear_map.get(platform_id, []):
                    env = re.sub(rf"^{re.escape(key)}=.*$", f"# {key}=", env, flags=re.MULTILINE)
                env_path.write_text(env, encoding="utf-8")
                self._json_response({"ok": True})
                return

            # 写入各字段
            for field_name, value in config.items():
                if not value:
                    continue
                # 映射字段名到 env key
                env_key_map = {
                    'token': {'telegram': 'TELEGRAM_BOT_TOKEN', 'discord': 'DISCORD_BOT_TOKEN'},
                    'bot_token': 'SLACK_BOT_TOKEN', 'app_token': 'SLACK_APP_TOKEN',
                    'enabled': 'WHATSAPP_ENABLED', 'allowed_users': 'WHATSAPP_ALLOWED_USERS',
                    'http_url': 'SIGNAL_HTTP_URL', 'account': 'SIGNAL_ACCOUNT',
                    'client_id': 'TEAMS_CLIENT_ID', 'client_secret': 'TEAMS_CLIENT_SECRET', 'tenant_id': 'TEAMS_TENANT_ID',
                    'project_id': 'GOOGLE_CHAT_PROJECT_ID', 'subscription': 'GOOGLE_CHAT_SUBSCRIPTION_NAME', 'sa_json': 'GOOGLE_CHAT_SERVICE_ACCOUNT_JSON',
                    'access_token': 'MATRIX_ACCESS_TOKEN', 'home_room': 'MATRIX_HOME_ROOM',
                    'account_id': 'WEIXIN_ACCOUNT_ID',
                    'app_id_map': {'qqbot': 'QQ_APP_ID', 'yuanbao': 'YUANBAO_APP_ID'},
                    'app_secret_map': {'qqbot': 'QQ_APP_SECRET', 'yuanbao': 'YUANBAO_APP_SECRET'},
                }
                # 解析 env key
                if field_name == 'token' and isinstance(env_key_map.get('token'), dict):
                    env_key = env_key_map['token'].get(platform_id, '')
                elif field_name == 'app_id':
                    m = env_key_map.get('app_id_map', {})
                    env_key = m.get(platform_id, '')
                elif field_name == 'app_secret':
                    m = env_key_map.get('app_secret_map', {})
                    env_key = m.get(platform_id, '')
                else:
                    env_key = env_key_map.get(field_name, '')

                if not env_key:
                    continue

                # 写入 .env
                if re.search(rf"^{re.escape(env_key)}=", env, re.MULTILINE):
                    env = re.sub(rf"^{re.escape(env_key)}=.*$", f"{env_key}={value}", env, flags=re.MULTILINE)
                elif re.search(rf"^#\s*{re.escape(env_key)}=", env, re.MULTILINE):
                    env = re.sub(rf"^#\s*{re.escape(env_key)}=.*$", f"{env_key}={value}", env, flags=re.MULTILINE)
                else:
                    env = env.rstrip() + f"\n{env_key}={value}\n"

            env_path.write_text(env, encoding="utf-8")
            self._json_response({"ok": True})

        else:
            self.send_response(404)
            self._cors()
            self.end_headers()

    def _json_response(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _proxy_to_gateway(self, path, method="GET", body=None, headers=None):
        """代理请求到 Gateway API 服务器"""
        gateway_url = f"http://127.0.0.1:8642{path}"
        try:
            req_headers = {"Content-Type": "application/json"}
            if headers:
                req_headers.update(headers)
            if method == "POST":
                data = json.dumps(body).encode("utf-8") if body else b""
                req = urllib.request.Request(gateway_url, data=data, headers=req_headers, method="POST")
            else:
                req = urllib.request.Request(gateway_url, headers=req_headers)

            # 对 SSE 流式请求特殊处理
            if "/v1/chat/completions" in path and body and body.get("stream"):
                resp = urllib.request.urlopen(req, timeout=300)
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self._cors()
                self.end_headers()
                while True:
                    line = resp.readline()
                    if not line:
                        break
                    self.wfile.write(line)
                    self.wfile.flush()
                return

            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self._cors()
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            error_body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(error_body)
        except Exception as e:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def log_message(self, format, *args):
        pass

# ── Gateway 自动启动 & 看门狗 ──
import subprocess, threading, time as _time

HERMES_VEXE = HERMES_DIR / "hermes-agent" / "venv" / "Scripts" / "hermes.exe"
GATEWAY_CHECK_INTERVAL = 30  # 秒
_gateway_restart_count = 0
_gateway_last_restart = 0

def _gateway_alive():
    """快速检测 Gateway 端口是否在监听"""
    import socket as _soc
    s = _soc.socket(_soc.AF_INET, _soc.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect(("127.0.0.1", 8642))
        return True
    except:
        return False
    finally:
        s.close()

def _start_gateway():
    """通过 hermes CLI 启动 Gateway（无黑窗口）"""
    global _gateway_restart_count, _gateway_last_restart
    if not HERMES_VEXE.exists():
        print("[ConfigServer] hermes.exe 未找到，跳过 Gateway 启动")
        return False
    # 防抖：60秒内不重复重启
    now = _time.time()
    if now - _gateway_last_restart < 60:
        return False
    _gateway_last_restart = now
    _gateway_restart_count += 1
    print(f"[ConfigServer] 第 {_gateway_restart_count} 次自动启动 Gateway...")
    try:
        subprocess.Popen(
            [str(HERMES_VEXE), "gateway", "start"],
            creationflags=0x08000000,  # CREATE_NO_WINDOW
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print(f"[ConfigServer] 启动 Gateway 失败: {e}")
        return False
    # 等待就绪（最多 15 秒）
    for _ in range(15):
        _time.sleep(1)
        if _gateway_alive():
            print("[ConfigServer] ✓ Gateway 已恢复")
            return True
    print("[ConfigServer] ✗ Gateway 启动超时")
    return False

def _gateway_watchdog():
    """后台线程：每 30 秒检测 Gateway，挂了就自动重启"""
    while True:
        _time.sleep(GATEWAY_CHECK_INTERVAL)
        if not _gateway_alive():
            print("[ConfigServer] ⚠ Gateway 离线，自动重启中...")
            _start_gateway()

def ensure_gateway_on_startup():
    """config_server 启动时确保 Gateway 在线"""
    if _gateway_alive():
        print("[ConfigServer] ✓ Gateway 已在线")
        return
    print("[ConfigServer] Gateway 未运行，启动中...")
    _start_gateway()

if __name__ == "__main__":
    # 启动时确保 Gateway 在线
    ensure_gateway_on_startup()
    # 启动看门狗后台线程
    watchdog = threading.Thread(target=_gateway_watchdog, daemon=True)
    watchdog.start()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Hermes Config Server on http://127.0.0.1:{PORT}", flush=True)
    server.serve_forever()
