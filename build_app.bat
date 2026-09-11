@echo off
chcp 65001 >nul
echo ======================================================================
echo 🚀 开始执行 Wails 桌面端一键全自动构建流程 (Windows)...
echo ======================================================================

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

:: 1. 确保 Wails CLI 可用
where wails >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
  for /f "tokens=*" %%i in ('go env GOPATH 2^>nul') do set "GOPATH_BIN=%%i\bin"
  if exist "%GOPATH_BIN%\wails.exe" (
    set "PATH=%PATH%;%GOPATH_BIN%"
  ) else (
    echo ⚠️ 未在系统 PATH 中找到 Wails，正在尝试自动安装 Wails CLI...
    go install github.com/wailsapp/wails/v2/cmd/wails@latest
    for /f "tokens=*" %%i in ('go env GOPATH 2^>nul') do set "PATH=%PATH%;%%i\bin"
  )
)

:: 2. 检查 Python 环境
set "PYTHON_EXE=%PROJECT_ROOT%.venv\Scripts\python.exe"
set "PYINSTALLER_BIN=%PROJECT_ROOT%.venv\Scripts\pyinstaller.exe"

if not exist "%PYTHON_EXE%" (
  echo 📦 正在创建 Python 虚拟环境...
  python -m venv "%PROJECT_ROOT%.venv"
)

if not exist "%PYINSTALLER_BIN%" (
  echo 📦 正在安装 PyInstaller 与项目核心依赖...
  "%PYTHON_EXE%" -m pip install -e ".[web]" xhs pyinstaller
  if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python 依赖安装失败，请检查上方错误提示！
    pause
    exit /b 1
  )
)

if not exist "%PROJECT_ROOT%conf.py" (
  echo ⚙️ 检测到缺失 conf.py，正在生成默认配置...
  (
    echo import os
    echo import sys
    echo from pathlib import Path
    echo def _get_base_dir^(^):
    echo     if getattr^(sys, "frozen", False^):
    echo         return Path^(sys.executable^).parent.resolve^(^)
    echo     return Path^(__file__^).parent.resolve^(^)
    echo BASE_DIR = _get_base_dir^(^)
    echo XHS_SERVER = "http://127.0.0.1:11901"
    echo LOCAL_CHROME_PATH = ""
    echo LOCAL_CHROME_HEADLESS = True
    echo DEBUG_MODE = True
    echo YT_PROXY = None
  ) > "%PROJECT_ROOT%conf.py"
)

:: 3. 执行 Python 引擎二进制编译
echo.
echo ▶ [Step 1/3] 打包 Python 发布引擎 (sau_engine.exe)...
"%PYINSTALLER_BIN%" --noconfirm --onedir ^
  --name "sau_engine" ^
  --paths "." ^
  --add-data "utils\stealth.min.js;utils" ^
  --add-data "conf.py;." ^
  --collect-all "uploader" ^
  --collect-all "utils" ^
  --collect-all "myUtils" ^
  --collect-all "patchright" ^
  --collect-all "playwright" ^
  --collect-all "loguru" ^
  sau_cli.py

if %ERRORLEVEL% NEQ 0 (
  echo ❌ Python 引擎打包失败!
  pause
  exit /b %ERRORLEVEL%
)

:: 4. 同步引擎产物与内置 Chromium 内核至 Wails bin 目录
echo.
echo ▶ [Step 2/3] 同步引擎产物与内置 Chromium 浏览器内核...
if exist "%PROJECT_ROOT%sau_desktop\bin\sau_engine" (
  rd /s /q "%PROJECT_ROOT%sau_desktop\bin\sau_engine"
)
mkdir "%PROJECT_ROOT%sau_desktop\bin\sau_engine"
xcopy /E /Y /I "%PROJECT_ROOT%dist\sau_engine\*" "%PROJECT_ROOT%sau_desktop\bin\sau_engine\" >nul

:: 内嵌 Windows 本地 Playwright Chromium 内核 (实现真正的开箱即用免安装)
set "SRC_PLAYWRIGHT=%LOCALAPPDATA%\ms-playwright"
set "DEST_PLAYWRIGHT=%PROJECT_ROOT%sau_desktop\bin\ms-playwright"

if not exist "%SRC_PLAYWRIGHT%\chromium-*" (
  echo 📦 正在拉取 Chromium 内核供打包内置...
  "%PYTHON_EXE%" -m patchright install chromium || "%PYTHON_EXE%" -m playwright install chromium
)

if exist "%SRC_PLAYWRIGHT%" (
  echo 📦 正在复制 Chromium 内核到应用内置资源目录: %DEST_PLAYWRIGHT%...
  if exist "%DEST_PLAYWRIGHT%" rd /s /q "%DEST_PLAYWRIGHT%"
  mkdir "%DEST_PLAYWRIGHT%"
  for /d %%d in ("%SRC_PLAYWRIGHT%\chromium-*" "%SRC_PLAYWRIGHT%\ffmpeg-*") do (
    echo   -^> 内嵌: %%~nxd
    xcopy /E /Y /I "%%d" "%DEST_PLAYWRIGHT%\%%~nxd\" >nul
  )
)

:: 5. 执行 Wails 桌面端编译
echo.
echo ▶ [Step 3/3] 执行 Wails 桌面端整合打包 (Go + Vue 3)...
cd /d "%PROJECT_ROOT%sau_desktop"

:: 编译 Windows 桌面端
echo 正在构建 Windows 桌面端程序...
wails build

if %ERRORLEVEL% NEQ 0 (
  echo [ERROR] Wails 桌面端打包失败!
  pause
  exit /b %ERRORLEVEL%
)

echo.
echo ======================================================================
echo Windows 桌面端全自动构建大功告成！已完全内置绿色 Chromium 浏览器内核！
echo 产物路径位于: %PROJECT_ROOT%sau_desktop\build\bin\
echo ======================================================================
explorer "%PROJECT_ROOT%sau_desktop\build\bin"
pause
