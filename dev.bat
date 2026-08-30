@echo off
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev.ps1"
if %errorlevel% neq 0 (
    echo.
    echo ❌ 调试启动失败，请检查上方错误提示。
    pause
)
