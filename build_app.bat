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

:: 4. 同步引擎产物至开发与产物发布目录
echo.
echo ▶ [Step 2/4] 同步 Python 引擎产物...
if exist "%PROJECT_ROOT%sau_desktop\bin\sau_engine" rd /s /q "%PROJECT_ROOT%sau_desktop\bin\sau_engine"
mkdir "%PROJECT_ROOT%sau_desktop\bin\sau_engine"
xcopy /E /Y /I "%PROJECT_ROOT%dist\sau_engine\*" "%PROJECT_ROOT%sau_desktop\bin\sau_engine\" >nul

:: 5. 确保并内嵌 Chromium 浏览器内核 (开箱即用绿色版)
echo.
echo ▶ [Step 3/4] 检查并内嵌自动化 Chromium 浏览器内核...
"%PYTHON_EXE%" -m patchright install chromium
if %ERRORLEVEL% NEQ 0 (
  "%PYTHON_EXE%" -m playwright install chromium
)

set "SRC_PLAYWRIGHT=%LOCALAPPDATA%\ms-playwright"
if not exist "%SRC_PLAYWRIGHT%" (
  set "SRC_PLAYWRIGHT=%USERPROFILE%\AppData\Local\ms-playwright"
)

set "DEV_PLAYWRIGHT=%PROJECT_ROOT%sau_desktop\bin\ms-playwright"
if exist "%DEV_PLAYWRIGHT%" rd /s /q "%DEV_PLAYWRIGHT%"
mkdir "%DEV_PLAYWRIGHT%"
if exist "%SRC_PLAYWRIGHT%" (
  echo 正在同步 Chromium 内核至应用资源库...
  for /d %%d in ("%SRC_PLAYWRIGHT%\chromium-*" "%SRC_PLAYWRIGHT%\ffmpeg-*") do (
    echo   -^> 内嵌: %%~nxd
    xcopy /E /Y /I "%%d" "%DEV_PLAYWRIGHT%\%%~nxd\" >nul
  )
)

:: 6. 执行 Wails 桌面端整合编译
echo.
echo ▶ [Step 4/4] 正在编译 Wails 桌面客户端程序...
cd /d "%PROJECT_ROOT%sau_desktop"
wails build

if %ERRORLEVEL% NEQ 0 (
  echo [ERROR] Wails 桌面端打包失败!
  pause
  exit /b %ERRORLEVEL%
)

:: 7. 将引擎与绿色浏览器内核同步注入至最终发布目录 build\bin
echo.
echo 📦 正在将运行引擎与绿色浏览器内核装配入发布目录 (sau_desktop\build\bin)...
set "FINAL_BIN=%PROJECT_ROOT%sau_desktop\build\bin"

if exist "%FINAL_BIN%\sau_engine" rd /s /q "%FINAL_BIN%\sau_engine"
mkdir "%FINAL_BIN%\sau_engine"
xcopy /E /Y /I "%PROJECT_ROOT%dist\sau_engine\*" "%FINAL_BIN%\sau_engine\" >nul

if exist "%FINAL_BIN%\ms-playwright" rd /s /q "%FINAL_BIN%\ms-playwright"
mkdir "%FINAL_BIN%\ms-playwright"
if exist "%DEV_PLAYWRIGHT%" (
  xcopy /E /Y /I "%DEV_PLAYWRIGHT%\*" "%FINAL_BIN%\ms-playwright\" >nul
)

echo.
echo ======================================================================
echo Windows 桌面端全自动构建大功告成！已完全内置绿色 Chromium 浏览器内核！
echo 产物路径位于: %FINAL_BIN%\
echo 包含: sau_desktop.exe, sau_engine (Python 引擎), ms-playwright (绿色浏览器)
echo ======================================================================
explorer "%FINAL_BIN%"
pause
