# ==============================================================================
# social-auto-upload 桌面端全自动一键调试启动脚本 (Windows PowerShell)
# 功能：自动环境检测 -> 自动补齐依赖 -> 自动编译引擎 -> 热重载启动 wails dev
# ==============================================================================

$ErrorActionPreference = "Stop"
$ROOT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ROOT_DIR

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "🚀 正在检查并初始化 social-auto-upload 桌面端开发环境..." -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. 检查基础环境
function Check-Command ($cmdName, $installUrl) {
    if (-not (Get-Command $cmdName -ErrorAction SilentlyContinue)) {
        Write-Host "❌ 错误: 未检测到系统安装 $cmdName ($installUrl)，请先安装后再运行本脚本。" -ForegroundColor Red
        exit 1
    }
}

Check-Command "git" "https://git-scm.com/"
Check-Command "go" "https://go.dev/dl/"
Check-Command "node" "https://nodejs.org/"
Check-Command "npm" "https://nodejs.org/"

# 检查 Python
$PYTHON_CMD = ""
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    $PYTHON_CMD = "python"
} elseif (Get-Command "python3" -ErrorAction SilentlyContinue) {
    $PYTHON_CMD = "python3"
} else {
    Write-Host "❌ 错误: 未检测到 Python 解释器，请先安装 Python 3.10+。" -ForegroundColor Red
    exit 1
}

Write-Host "✅ 基础环境检测通过: Go, Node.js, npm, $PYTHON_CMD, Git" -ForegroundColor Green

# 2. 检查 Wails CLI
$gopath = (go env GOPATH).Trim()
$env:PATH = "$gopath\bin;$env:PATH"

if (-not (Get-Command "wails" -ErrorAction SilentlyContinue)) {
    Write-Host "📦 检测到未安装 Wails CLI，正在自动通过 Go 安装..." -ForegroundColor Yellow
    go install github.com/wailsapp/wails/v2/cmd/wails@latest
    Write-Host "✅ Wails CLI 安装完成！" -ForegroundColor Green
} else {
    Write-Host "✅ Wails CLI 已就绪" -ForegroundColor Green
}

# 3. 配置文件初始化
if (-not (Test-Path "conf.py")) {
    Write-Host "⚙️  未检测到 conf.py，正在从 conf.example.py 自动复制初始化..." -ForegroundColor Yellow
    Copy-Item "conf.example.py" "conf.py"
    Write-Host "✅ conf.py 创建成功！" -ForegroundColor Green
}

# 4. Python 虚拟环境与依赖检测
$VENV_DIR = Join-Path $ROOT_DIR ".venv"
$VENV_PYTHON = Join-Path $VENV_DIR "Scripts\python.exe"
$VENV_PIP = Join-Path $VENV_DIR "Scripts\pip.exe"
$REQUIREMENTS_STAMP = Join-Path $VENV_DIR ".requirements_installed"

if (-not (Test-Path $VENV_DIR)) {
    Write-Host "📦 正在创建 Python 虚拟环境 (.venv)..." -ForegroundColor Yellow
    & $PYTHON_CMD -m venv $VENV_DIR
}

# 快速探测虚拟环境中是否已具备核心运行库
$hasCoreDeps = $false
try {
    & $VENV_PYTHON -c "import PyInstaller, loguru" 2>$null
    if ($LASTEXITCODE -eq 0) { $hasCoreDeps = $true }
} catch {}

if ($hasCoreDeps) {
    Write-Host "✅ Python 运行环境已就绪 (跳过重复安装)" -ForegroundColor Green
} else {
    Write-Host "📦 正在自动安装/更新 Python 自动化依赖库 (使用清华镜像加速)..." -ForegroundColor Yellow
    $PIP_INDEX = "https://pypi.tuna.tsinghua.edu.cn/simple"
    
    if (Test-Path "requirements.txt") {
        & $VENV_PIP install -r requirements.txt -i $PIP_INDEX --trusted-host pypi.tuna.tsinghua.edu.cn
    }
    & $VENV_PIP install pyinstaller -i $PIP_INDEX --trusted-host pypi.tuna.tsinghua.edu.cn

    Write-Host "🌐 正在安装 Playwright / Patchright 浏览器内核..." -ForegroundColor Yellow
    try {
        & $VENV_PYTHON -m patchright install chromium 2>$null
    } catch {
        & $VENV_PYTHON -m playwright install chromium 2>$null
    }

    Write-Host "✅ Python 依赖与浏览器内核准备就绪！" -ForegroundColor Green
}

# 5. 前端 node_modules 依赖检测
$FRONTEND_DIR = Join-Path $ROOT_DIR "sau_desktop\frontend"
$NODE_MODULES = Join-Path $FRONTEND_DIR "node_modules"

if (-not (Test-Path $NODE_MODULES)) {
    Write-Host "📦 正在为桌面端前端安装 npm 依赖..." -ForegroundColor Yellow
    Set-Location $FRONTEND_DIR
    npm install
    Set-Location $ROOT_DIR
    Write-Host "✅ 前端依赖安装完成！" -ForegroundColor Green
} else {
    Write-Host "✅ 前端 npm 依赖已就绪" -ForegroundColor Green
}

# 7. 启动热重载开发调试模式
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "🎉 所有环境与依赖检测完毕！正在启动 Wails 调试开发服务..." -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

Set-Location (Join-Path $ROOT_DIR "sau_desktop")
wails dev
