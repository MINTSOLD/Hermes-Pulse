#!/bin/bash
# Hermes Pulse 安装程序 (macOS)
# 双击此文件即可安装

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║                                          ║"
echo "  ║      ✦  Hermes Pulse  安装程序  ✦       ║"
echo "  ║          轻于形 · 智于心                 ║"
echo "  ║                                          ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""
echo "  正在安装，请稍候..."
echo ""

# 获取脚本所在目录
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

# 安装目录
INSTALL_DIR="$HOME/Library/Application Support/Hermes Pulse"
mkdir -p "$INSTALL_DIR"

# 复制文件
echo "  [1/3] 复制文件..."
cp -f "$SRC_DIR/hermes_gui.py" "$INSTALL_DIR/" 2>/dev/null
cp -f "$SRC_DIR/config_server.py" "$INSTALL_DIR/" 2>/dev/null
cp -f "$SRC_DIR/index.html" "$INSTALL_DIR/" 2>/dev/null
cp -f "$SRC_DIR/styles.css" "$INSTALL_DIR/" 2>/dev/null
cp -f "$SRC_DIR/app.js" "$INSTALL_DIR/" 2>/dev/null
cp -f "$SRC_DIR/hermes-logo.png" "$INSTALL_DIR/" 2>/dev/null
cp -f "$SRC_DIR/hermes.ico" "$INSTALL_DIR/" 2>/dev/null
echo "      完成 ✓"
echo ""

# 安装依赖
echo "  [2/3] 安装运行环境..."
python3 -m pip install pywebview pystray Pillow --quiet 2>/dev/null
echo "      完成 ✓"
echo ""

# 创建启动脚本
echo "  [3/3] 创建启动脚本..."
cat > "$INSTALL_DIR/Hermes.command" << EOF
#!/bin/bash
exec python3 "$INSTALL_DIR/hermes_gui.py" "\$@"
EOF
chmod +x "$INSTALL_DIR/Hermes.command"

# 桌面快捷方式
ln -sf "$INSTALL_DIR/Hermes.command" "$HOME/Desktop/Hermes Pulse.command" 2>/dev/null
echo "      完成 ✓"
echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║                                          ║"
echo "  ║         ✓  安装成功！                    ║"
echo "  ║                                          ║"
echo "  ║   双击桌面 "Hermes Pulse" 即可启动       ║"
echo "  ║                                          ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

read -p "是否立即启动？(y/n): " START
if [ "$START" = "y" ] || [ "$START" = "Y" ]; then
    echo "正在启动 Hermes Pulse..."
    python3 "$INSTALL_DIR/hermes_gui.py" &
fi
