@echo off
chcp 65001 >nul
echo ======================================================================
echo 🚀 开始执行 Wails 桌面端一键全自动构建流程 (Windows)...
echo ======================================================================

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

:: 1. 检查 Python 虚拟环境与 PyInstaller
set "PYINSTALLER_BIN=%PROJECT_ROOT%.venv\Scripts\pyinstaller.exe"

if not exist "%PYINSTALLER_BIN%" (
  echo 📦 正在安装 PyInstaller 打包工具...
  "%PROJECT_ROOT%.venv\Scripts\python.exe" -m pip install pyinstaller
)

:: 2. 执行 Python 引擎二进制编译
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

:: 3. 同步产物至 Wails bin 目录
echo.
echo ▶ [Step 2/3] 同步引擎产物至 sau_desktop\bin\sau_engine\...
if not exist "%PROJECT_ROOT%sau_desktop\bin\sau_engine" (
  mkdir "%PROJECT_ROOT%sau_desktop\bin\sau_engine"
)
xcopy /E /Y /I "%PROJECT_ROOT%dist\sau_engine\*" "%PROJECT_ROOT%sau_desktop\bin\sau_engine\"

:: 4. 执行 Wails 桌面端编译
echo.
echo ▶ [Step 3/3] 执行 Wails 桌面端整合打包 (Go + Vue 3)...
cd /d "%PROJECT_ROOT%sau_desktop"
wails build -nsis

if %ERRORLEVEL% NEQ 0 (
  echo ❌ Wails 打包失败!
  pause
  exit /b %ERRORLEVEL%
)

echo.
echo ======================================================================
echo 🎉 Windows 桌面安装包全自动构建大功告成！
echo 产物路径位于: %PROJECT_ROOT%sau_desktop\build\bin\
echo ======================================================================
pause
