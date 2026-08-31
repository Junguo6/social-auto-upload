#!/usr/bin/env bash

# ==============================================================================
# social-auto-upload 桌面端全自动一键调试启动脚本 (macOS / Linux)
# 功能：自动环境检测 -> 自动补齐依赖 -> 自动编译引擎 -> 热重载启动 wails dev
# ==============================================================================

set -e

# 定位脚本所在的项目根目录
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "========================================================"
echo "🚀 正在检查并初始化 social-auto-upload 桌面端开发环境..."
echo "========================================================"

# 1. 检查基础环境命令行工具
check_cmd() {
    if ! command -v "$1" &> /dev/null; then
        echo "❌ 错误: 未检测到系统安装 $1 ($2)，请先安装后再运行本脚本。"
        exit 1
    fi
}

check_cmd "git" "https://git-scm.com/"
check_cmd "go" "https://go.dev/dl/"
check_cmd "node" "https://nodejs.org/"
check_cmd "npm" "https://nodejs.org/"

# 检查 Python 解释器
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ 错误: 未检测到 Python 解释器，请先安装 Python 3.10+。"
    exit 1
fi

echo "✅ 基础环境检测通过: Go, Node.js, npm, $PYTHON_CMD, Git"

# 2. 检查并确保 Wails CLI 脚手架 (完全尊重用户系统已有版本，绝不擅自全局升级)
GOPATH_BIN="$(go env GOPATH)/bin"
export PATH="$GOPATH_BIN:$PATH"

if ! command -v wails &> /dev/null; then
    echo "📦 检测到未安装 Wails CLI，正在协助安装 (v2.8.2)..."
    go install github.com/wailsapp/wails/v2/cmd/wails@v2.8.2
    echo "✅ Wails CLI 安装完成！"
else
    WAILS_RAW=$(wails version 2>/dev/null | head -n 1)
    echo "✅ Wails CLI 已就绪 ($WAILS_RAW)"
fi

# 3. 配置文件初始化
if [ ! -f "conf.py" ]; then
    echo "⚙️  未检测到 conf.py，正在从 conf.example.py 自动复制初始化..."
    cp conf.example.py conf.py
    echo "✅ conf.py 创建成功！"
fi

# 4. Python 虚拟环境与依赖检测
VENV_DIR="$ROOT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"
REQUIREMENTS_STAMP="$VENV_DIR/.requirements_installed"

if [ ! -d "$VENV_DIR" ]; then
    echo "📦 正在创建 Python 虚拟环境 (.venv)..."
    $PYTHON_CMD -m venv "$VENV_DIR"
fi

# 快速探测虚拟环境中是否已具备核心运行库
if "$VENV_PYTHON" -c "import PyInstaller, loguru" &> /dev/null; then
    echo "✅ Python 运行环境已就绪 (跳过重复安装)"
else
    echo "📦 正在配置 Python 自动化依赖库 (使用清华镜像加速)..."
    PIP_INDEX="https://pypi.tuna.tsinghua.edu.cn/simple"
    
    echo "📦 正在更新 pip..."
    "$VENV_PIP" install --upgrade pip -i "$PIP_INDEX" --trusted-host pypi.tuna.tsinghua.edu.cn -q
    
    if [ -f "requirements.txt" ]; then
        "$VENV_PIP" install -r requirements.txt -i "$PIP_INDEX" --trusted-host pypi.tuna.tsinghua.edu.cn
    fi
    "$VENV_PIP" install pyinstaller -i "$PIP_INDEX" --trusted-host pypi.tuna.tsinghua.edu.cn

    echo "🌐 正在检查 Playwright / Patchright 浏览器内核..."
    "$VENV_PYTHON" -m patchright install chromium 2>/dev/null || "$VENV_PYTHON" -m playwright install chromium 2>/dev/null || true
    
    echo "✅ Python 依赖与浏览器内核准备就绪！"
fi

# 5. 前端 node_modules 依赖检测
FRONTEND_DIR="$ROOT_DIR/sau_desktop/frontend"
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "📦 正在为桌面端前端安装 npm 依赖..."
    cd "$FRONTEND_DIR"
    npm install
    cd "$ROOT_DIR"
    echo "✅ 前端依赖安装完成！"
else
    echo "✅ 前端 npm 依赖已就绪"
fi

# 6. 启动热重载开发调试模式
echo "========================================================"
echo "🎉 所有环境与依赖检测完毕！正在启动 Wails 调试开发服务..."
echo "========================================================"

cd "$ROOT_DIR/sau_desktop"

# 如果当前是 Wails 2.8.x，自动加上 -skipbindings 跳过生成器错误
DEV_FLAGS=""
WAILS_RAW=$(wails version 2>/dev/null | head -n 1)
if echo "$WAILS_RAW" | grep -qE "v2\.[0-8]\."; then
    echo "💡 检测到 Wails 2.8.x，已自动启用 -skipbindings 兼容模式..."
    DEV_FLAGS="-skipbindings"
fi

wails dev $DEV_FLAGS
