#!/bin/bash
# Hermes Pulse 安装程序 (Linux)
# 运行: bash 安装.sh

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

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$HOME/.local/share/hermes-pulse"
mkdir -p "$INSTALL_DIR"

echo "  [1/3] 复制文件..."
cp -f "$SRC_DIR/hermes_gui.py" "$INSTALL_DIR/"
cp -f "$SRC_DIR/config_server.py" "$INSTALL_DIR/"
cp -f "$SRC_DIR/index.html" "$INSTALL_DIR/"
cp -f "$SRC_DIR/styles.css" "$INSTALL_DIR/"
cp -f "$SRC_DIR/app.js" "$INSTALL_DIR/"
cp -f "$SRC_DIR/hermes-logo.png" "$INSTALL_DIR/"
cp -f "$SRC_DIR/hermes.ico" "$INSTALL_DIR/" 2>/dev/null
echo "      完成 ✓"
echo ""

echo "  [2/3] 安装运行环境..."
python3 -m pip install --user pywebview pystray Pillow --quiet 2>/dev/null
echo "      完成 ✓"
echo ""

echo "  [3/3] 创建启动命令..."
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/hermes-pulse" << EOF
#!/bin/bash
exec python3 "$INSTALL_DIR/hermes_gui.py" "\$@"
EOF
chmod +x "$BIN_DIR/hermes-pulse"
echo "      完成 ✓"
echo ""

# 检查 PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "  ! 请将 $BIN_DIR 添加到 PATH:"
    echo "    echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
    echo ""
fi

echo "  ╔══════════════════════════════════════════╗"
echo "  ║                                          ║"
echo "  ║         ✓  安装成功！                    ║"
echo "  ║                                          ║"
echo "  ║   终端输入 hermes-pulse 即可启动         ║"
echo "  ║                                          ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""
