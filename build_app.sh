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
  echo "⚠️ 未在系统 PATH 中找到 Wails，正在自动安装最新版 Wails CLI..."
  go install github.com/wailsapp/wails/v2/cmd/wails@latest
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

# 4. 同步产物至 Wails bin 目录
echo ""
echo "▶ [Step 2/3] 同步引擎产物至 sau_desktop/bin/sau_engine/..."
mkdir -p "$PROJECT_ROOT/sau_desktop/bin/sau_engine"
rm -rf "$PROJECT_ROOT/sau_desktop/bin/sau_engine/*"
cp -r "$PROJECT_ROOT/dist/sau_engine/"* "$PROJECT_ROOT/sau_desktop/bin/sau_engine/"

# 5. 执行 Wails 桌面端编译
echo ""
echo "▶ [Step 3/3] 执行 Wails 桌面端整合打包 (Go + Vue 3)..."
cd "$PROJECT_ROOT/sau_desktop"
wails build

echo ""
echo "======================================================================"
echo "🎉 全自动构建大功告成！"
echo "产物路径: $PROJECT_ROOT/sau_desktop/build/bin/sau_desktop.app"
echo "您可以在 Finder 中打开或双击运行："
echo "open $PROJECT_ROOT/sau_desktop/build/bin"
echo "======================================================================"
