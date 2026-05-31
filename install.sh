#!/usr/bin/env bash
set -e

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║     ✦ Hermes Pulse Installer ✦       ║"
echo "  ║        轻于形 · 智于心               ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Detect Python ──
echo "[1/5] Detecting Python ..."
PYTHON_CMD=""
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    # Check if 'python' is Python 3
    PY_VER=$(python --version 2>&1 | grep -oP '\d+\.\d+')
    PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
    if [ "$PY_MAJOR" = "3" ]; then
        PYTHON_CMD="python"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "  ✗ Python 3 not found. Please install Python 3.11+"
    echo "    macOS: brew install python@3.11"
    echo "    Ubuntu/Debian: sudo apt install python3.11 python3.11-venv"
    echo "    Fedora: sudo dnf install python3.11"
    exit 1
fi

PY_VER=$($PYTHON_CMD --version 2>&1 | grep -oP '\d+\.\d+\.\d+')
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
echo "  ✓ Python $PY_VER"

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
    echo "  ✗ Python 3.11+ required (found $PY_VER)"
    echo "    Please upgrade Python."
    exit 1
fi

# ── Detect pip ──
echo "[2/5] Detecting pip ..."
if ! $PYTHON_CMD -m pip --version &>/dev/null; then
    echo "  ◌ pip not found, installing..."
    $PYTHON_CMD -m ensurepip --upgrade 2>/dev/null || {
        echo "  ✗ Could not install pip. Please install python3-pip or python3.11-venv"
        exit 1
    }
fi
echo "  ✓ pip ready"

# ── Install dependencies ──
echo "[3/5] Installing dependencies ..."
$PYTHON_CMD -m pip install pywebview pystray Pillow --quiet 2>/dev/null || {
    echo "  ✗ Failed to install dependencies"
    exit 1
}
echo "  ✓ Dependencies installed"

# ── Detect / install Hermes Agent ──
echo "[4/5] Detecting Hermes Agent ..."
if command -v hermes &>/dev/null; then
    echo "  ✓ Hermes Agent already installed"
else
    echo "  ◌ Hermes Agent not found, installing..."
    $PYTHON_CMD -m pip install hermes-agent --quiet 2>/dev/null || {
        echo "  ✗ Installation failed. Please run: pip install hermes-agent"
        exit 1
    }
    echo "  ✓ Hermes Agent installed"
fi

# ── Deploy files ──
echo "[5/5] Deploying Hermes Pulse ..."

INSTALL_DIR="$HOME/.local/share/hermes-pulse"
mkdir -p "$INSTALL_DIR"

# Copy files
for f in hermes_gui.py config_server.py index.html styles.css app.js; do
    if [ -f "$SCRIPT_DIR/$f" ]; then
        cp -f "$SCRIPT_DIR/$f" "$INSTALL_DIR/$f"
    fi
done

# Copy optional assets (icons, logo)
for f in hermes-logo.png hermes.ico hermes-titlebar.ico; do
    if [ -f "$SCRIPT_DIR/$f" ]; then
        cp -f "$SCRIPT_DIR/$f" "$INSTALL_DIR/$f"
    fi
done

# ── Create wrapper script in /usr/local/bin (or ~/.local/bin) ──
WRAPPER_DIR="/usr/local/bin"
WRAPPER_PATH="$WRAPPER_DIR/hermes-pulse"

# Try /usr/local/bin first, fall back to ~/.local/bin
if [ ! -w "$WRAPPER_DIR" ]; then
    WRAPPER_DIR="$HOME/.local/bin"
    mkdir -p "$WRAPPER_DIR"
    WRAPPER_PATH="$WRAPPER_DIR/hermes-pulse"

    # Ensure ~/.local/bin is on PATH
    SHELL_RC=""
    if [ -f "$HOME/.bashrc" ]; then
        SHELL_RC="$HOME/.bashrc"
    elif [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
    fi
    if [ -n "$SHELL_RC" ] && ! grep -q '\.local/bin' "$SHELL_RC" 2>/dev/null; then
        echo '' >> "$SHELL_RC"
        echo '# Added by Hermes Pulse installer' >> "$SHELL_RC"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
        echo "  ✓ Added ~/.local/bin to PATH in $SHELL_RC"
    fi
fi

cat > "$WRAPPER_PATH" << WRAPPER_EOF
#!/usr/bin/env bash
# Hermes Pulse launcher
exec $PYTHON_CMD "$INSTALL_DIR/hermes_gui.py" "\$@"
WRAPPER_EOF
chmod +x "$WRAPPER_PATH"

echo "  ✓ Installed launcher: $WRAPPER_PATH"

# ── Done ──
echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║   ✓ Installation complete!           ║"
echo "  ║   Run: hermes-pulse                  ║"
echo "  ╚══════════════════════════════════════╝"
echo ""
