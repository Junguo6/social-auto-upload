#!/usr/bin/env bash
set -e

# ==============================================================================
# social-auto-upload Wails 桌面端一键全自动打包脚本 (macOS / Linux)
# ==============================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "======================================================================"
echo "🚀 开始执行 Wails 桌面端一键全自动构建流程..."
echo "======================================================================"

# 1. 确保 Wails CLI 可用
export PATH="$PATH:$(go env GOPATH)/bin"
if ! command -v wails >/dev/null 2>&1; then
  echo "⚠️ 未在系统 PATH 中找到 Wails，正在自动安装 Wails CLI (v2.8.2)..."
  go install github.com/wailsapp/wails/v2/cmd/wails@v2.8.2
fi

# 2. 检查 Python 虚拟环境与 PyInstaller
PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
PYINSTALLER_BIN="$PROJECT_ROOT/.venv/bin/pyinstaller"

if [ ! -f "$PYINSTALLER_BIN" ]; then
  echo "📦 正在安装 PyInstaller 打包工具..."
  "$PYTHON_BIN" -m pip install pyinstaller
fi

# 3. 执行 Python 引擎二进制编译
echo ""
echo "▶ [Step 1/3] 打包 Python 发布引擎 (sau_engine)..."
"$PYINSTALLER_BIN" --noconfirm --onedir \
  --name "sau_engine" \
  --paths "." \
  --add-data "utils/stealth.min.js:utils" \
  --add-data "conf.py:." \
  --collect-all "uploader" \
  --collect-all "utils" \
  --collect-all "myUtils" \
  --collect-all "patchright" \
  --collect-all "playwright" \
  --collect-all "loguru" \
  sau_cli.py

# 4. 同步引擎产物与内置 Chromium 内核至 Wails bin 目录
echo ""
echo "▶ [Step 2/3] 同步引擎产物与内置 Chromium 浏览器内核..."
rm -rf "$PROJECT_ROOT/sau_desktop/bin/sau_engine"
mkdir -p "$PROJECT_ROOT/sau_desktop/bin/sau_engine"
cp -r "$PROJECT_ROOT/dist/sau_engine/"* "$PROJECT_ROOT/sau_desktop/bin/sau_engine/"

# 探测并内嵌 Playwright Chromium 内核 (实现真正的本地离线免安装、开箱即用)
SRC_PLAYWRIGHT=""
if [ "$(uname)" = "Darwin" ]; then
  SRC_PLAYWRIGHT="$HOME/Library/Caches/ms-playwright"
else
  SRC_PLAYWRIGHT="$HOME/.cache/ms-playwright"
fi

if [ ! -d "$SRC_PLAYWRIGHT" ] || ! ls "$SRC_PLAYWRIGHT"/chromium-* >/dev/null 2>&1; then
  echo "📦 本机尚未缓存 Chromium 内核，正在自动拉取供打包内置..."
  "$PYTHON_BIN" -m patchright install chromium || "$PYTHON_BIN" -m playwright install chromium
fi

DEST_PLAYWRIGHT="$PROJECT_ROOT/sau_desktop/bin/ms-playwright"
rm -rf "$DEST_PLAYWRIGHT"
mkdir -p "$DEST_PLAYWRIGHT"
echo "📦 正在复制 Chromium 内核到应用内置资源目录: $DEST_PLAYWRIGHT..."
for d in "$SRC_PLAYWRIGHT"/chromium-* "$SRC_PLAYWRIGHT"/chromium_headless_shell-* "$SRC_PLAYWRIGHT"/ffmpeg-*; do
  if [ -d "$d" ]; then
    echo "  -> 内嵌: $(basename "$d")"
    cp -R "$d" "$DEST_PLAYWRIGHT/"
  fi
done

# 5. 执行 Wails 桌面端编译
echo ""
echo "▶ [Step 3/3] 执行 Wails 桌面端整合打包 (Go + Vue 3)..."
cd "$PROJECT_ROOT/sau_desktop"
wails build

# 对于 macOS，将内置内核直接注入 .app 的 Resources 目录中
APP_RESOURCES="$PROJECT_ROOT/sau_desktop/build/bin/sau_desktop.app/Contents/Resources"
if [ -d "$APP_RESOURCES" ]; then
  echo "📦 正在将 ms-playwright 浏览器内核同步注入 .app 安装包的 Resources 目录..."
  cp -R "$DEST_PLAYWRIGHT" "$APP_RESOURCES/"
fi

# 6. 为用户打包成开箱即用的 zip 归档包 (保留 macOS 执行权限，防止传输损坏)
echo ""
echo "▶ [Step 4/4] 正在生成便于发给客户测试的整包压缩归档..."
cd "$PROJECT_ROOT/sau_desktop/build/bin"
rm -f "sau_desktop_mac.zip"
zip -r -q -y "sau_desktop_mac.zip" "sau_desktop.app"

echo ""
echo "======================================================================"
echo "🎉 全自动构建大功告成！已完全内置绿色 Chromium 浏览器内核 (开箱即用免安装)！"
echo "应用包路径: $PROJECT_ROOT/sau_desktop/build/bin/sau_desktop.app"
echo "测试整包 ZIP: $PROJECT_ROOT/sau_desktop/build/bin/sau_desktop_mac.zip"
echo "您可以在 Finder 中打开："
echo "open $PROJECT_ROOT/sau_desktop/build/bin"
echo "======================================================================"
