@echo off
chcp 65001 >nul
echo ======================================================================
echo 🚀 开始执行 Wails 桌面端一键全自动构建流程 (Windows)...
echo ======================================================================

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

:: 1. Wails CLI：通过 go run 调用项目锁定版本，不依赖也不影响全局安装的 wails
::    ⚠️ 全局 wails（当前 v2.8.2）被小映批量助手等其他项目使用，绝不能升级
set "GOTOOLCHAIN=go1.23.6"
set "WAILS_CLI_VERSION=v2.11.0"
echo Wails CLI 使用项目锁定版本: %WAILS_CLI_VERSION%（go run 调用，不影响全局 CLI）

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
  --collect-all "qrcode" ^
  --collect-all "segno" ^
  --hidden-import "asyncio" ^
  --hidden-import "tempfile" ^
  --hidden-import "traceback" ^
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

:: 5. 确保并智能内嵌当前所需单一版本 Chromium 内核 (开箱即用绿色版，自动剔除历史多余版本瘦身)
echo.
echo ▶ [Step 3/4] 检查并智能内嵌 Chromium 浏览器内核 (精准瘦身模式)...
"%PYTHON_EXE%" -m patchright install chromium
if %ERRORLEVEL% NEQ 0 (
  "%PYTHON_EXE%" -m playwright install chromium
)

set "DEV_PLAYWRIGHT=%PROJECT_ROOT%sau_desktop\bin\ms-playwright"
"%PYTHON_EXE%" "%PROJECT_ROOT%utils\sync_browser_kernel.py" "%DEV_PLAYWRIGHT%"
if %ERRORLEVEL% NEQ 0 (
  echo ⚠️ 内核自动瘦身同步失败，正在以备用模式尝试复制...
  set "SRC_PLAYWRIGHT=%LOCALAPPDATA%\ms-playwright"
  if not exist "%SRC_PLAYWRIGHT%" set "SRC_PLAYWRIGHT=%USERPROFILE%\AppData\Local\ms-playwright"
  if exist "%SRC_PLAYWRIGHT%" (
    for /d %%d in ("%SRC_PLAYWRIGHT%\chromium-*" "%SRC_PLAYWRIGHT%\chromium_headless_shell-*" "%SRC_PLAYWRIGHT%\ffmpeg-*") do (
      xcopy /E /Y /I "%%d" "%DEV_PLAYWRIGHT%\%%~nxd\" >nul
    )
  )
)

:: 6. 执行 Wails 桌面端整合编译
echo.
echo ▶ [Step 4/4] 正在编译 Wails 桌面客户端程序...
cd /d "%PROJECT_ROOT%sau_desktop"
go run "github.com/wailsapp/wails/v2/cmd/wails@%WAILS_CLI_VERSION%" build

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

:: 8. 编译并装配专属独立升级工具 updater.exe
echo.
echo 🔧 正在装配专属独立在线升级工具 (updater.exe)...
set "UPDATER_DIR=%PROJECT_ROOT%..\sau_updater"
set "UPDATER_REPO=https://gitee.com/shenzhen-feifan-e-commerce/updater.git"

:: 8.1 若本地未找到源码目录，自动从 Git 仓库拉取克隆
if not exist "%UPDATER_DIR%" (
  echo 🌐 未检测到本地升级工具源码，正在从远程仓库克隆 (%UPDATER_REPO%)...
  git clone "%UPDATER_REPO%" "%UPDATER_DIR%"
  if %ERRORLEVEL% NEQ 0 (
    echo ⚠️ 远程克隆失败或未联网，将尝试使用本地备用二进制...
  )
) else (
  :: 若已存在且为 Git 仓库，同步最新代码
  if exist "%UPDATER_DIR%\.git" (
    echo 🔄 检测到本地升级程序仓库，正在同步最新源码...
    pushd "%UPDATER_DIR%"
    git pull --quiet --rebase >nul 2>&1
    popd
  )
)

:: 8.2 编译最新版 updater.exe
if exist "%UPDATER_DIR%" (
  pushd "%UPDATER_DIR%"
  if exist "build.bat" (
    call build.bat >nul 2>&1
  ) else (
    go build -ldflags "-s -w -H windowsgui" -o updater.exe . >nul 2>&1
  )
  if exist "updater.exe" (
    copy /Y "updater.exe" "%FINAL_BIN%\updater.exe" >nul
    copy /Y "updater.exe" "%PROJECT_ROOT%sau_desktop\build\windows\updater.exe" >nul
    echo ✅ 最新独立升级工具编译装配成功！
  )
  popd
)

:: 8.3 兜底机制：若无 Go 环境或克隆编译失败，使用项目中已有的备用二进制
if not exist "%FINAL_BIN%\updater.exe" (
  if exist "%PROJECT_ROOT%sau_desktop\build\windows\updater.exe" (
    echo ⚠️ 采用项目内置备用 updater.exe...
    copy /Y "%PROJECT_ROOT%sau_desktop\build\windows\updater.exe" "%FINAL_BIN%\updater.exe" >nul
  ) else (
    echo ❌ 警告: 未找到任何可用 updater.exe 升级程序！
  )
)

:: 9. 自动化提炼标准发行包 (支持按需指定参数: -upgrade / -green / -all)
echo.
set "BUILD_TARGET=green"
if "%~1"=="-upgrade" set "BUILD_TARGET=upgrade"
if "%~1"=="--upgrade" set "BUILD_TARGET=upgrade"
if "%~1"=="-u" set "BUILD_TARGET=upgrade"
if "%~1"=="-green" set "BUILD_TARGET=green"
if "%~1"=="--green" set "BUILD_TARGET=green"
if "%~1"=="-g" set "BUILD_TARGET=green"
if "%~1"=="-all" set "BUILD_TARGET=all"
if "%~1"=="--all" set "BUILD_TARGET=all"
if "%~1"=="-a" set "BUILD_TARGET=all"

echo 📦 [Step 5/5] 正在按需归档发行包 [目标: %BUILD_TARGET%]...
set "RELEASE_DIR=%PROJECT_ROOT%dist_release"
if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"

:: 获取版本号 (从 wails.json 提取，若失败默认 1.0.0)
for /f "tokens=2 delims=:, " %%a in ('findstr /i "\"productVersion\"" "%PROJECT_ROOT%sau_desktop\wails.json" 2^>nul') do (
  set "APP_VER=%%~a"
)
if "%APP_VER%"=="" set "APP_VER=1.0.0"
echo 当前发布版本号: v%APP_VER%

:: 9.1 生成供 OSS 在线热更新的增量升级包 (-upgrade 或 -all)
if "%BUILD_TARGET%"=="upgrade" goto MAKE_UPGRADE
if "%BUILD_TARGET%"=="all" goto MAKE_UPGRADE
goto CHECK_GREEN

:MAKE_UPGRADE
echo 🚀 正在生成在线热更新包 (upgrade_win_%APP_VER%.zip，体积小)...
powershell -NoProfile -Command "Compress-Archive -Path '%FINAL_BIN%\小映分发助手.exe', '%FINAL_BIN%\sau_engine', '%FINAL_BIN%\updater.exe' -DestinationPath '%RELEASE_DIR%\upgrade_win_%APP_VER%.zip' -Force"
copy /Y "%RELEASE_DIR%\upgrade_win_%APP_VER%.zip" "%RELEASE_DIR%\upgrade_win.zip" >nul
if "%BUILD_TARGET%"=="upgrade" goto FINISH_BUILD

:CHECK_GREEN
:: 9.2 生成供新用户下载解压即用的完整绿色包 (-green 或 -all)
if "%BUILD_TARGET%"=="green" goto MAKE_GREEN
if "%BUILD_TARGET%"=="all" goto MAKE_GREEN
goto FINISH_BUILD

:MAKE_GREEN
echo 🚀 正在生成新用户完整开箱即用绿色包 (小映分发助手_v%APP_VER%_完整绿色版.zip)...
powershell -NoProfile -Command "Compress-Archive -Path '%FINAL_BIN%\*' -DestinationPath '%RELEASE_DIR%\小映分发助手_v%APP_VER%_完整绿色版.zip' -Force"

:FINISH_BUILD
echo.
echo ======================================================================
echo 🎉 构建与发行包归档全部完成！
echo.
echo 1. 本地可执行目录: %FINAL_BIN%\
if exist "%RELEASE_DIR%\小映分发助手_v%APP_VER%_完整绿色版.zip" (
  echo 2. 新用户完整包:   %RELEASE_DIR%\小映分发助手_v%APP_VER%_完整绿色版.zip
)
if exist "%RELEASE_DIR%\upgrade_win_%APP_VER%.zip" (
  echo 3. 在线增量升级包: %RELEASE_DIR%\upgrade_win_%APP_VER%.zip (传至 OSS)
)
echo ======================================================================
explorer "%RELEASE_DIR%"
pause
