#!/usr/bin/env bash
set -e

# ==============================================================================
# social-auto-upload Wails 桌面端一键全自动打包脚本 (macOS / Linux)
# ==============================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# 参数解析: 允许指定产物类型，避免每次生成全部文件体积过大
# 支持: -dmg (默认), -upgrade, -zip, -all
BUILD_TARGET="dmg"

for arg in "$@"; do
  case "$arg" in
    -dmg|--dmg|-d)
      BUILD_TARGET="dmg"
      ;;
    -upgrade|--upgrade|-u)
      BUILD_TARGET="upgrade"
      ;;
    -zip|--zip|-z)
      BUILD_TARGET="zip"
      ;;
    -all|--all|-a)
      BUILD_TARGET="all"
      ;;
    -h|--help)
      echo "======================================================================"
      echo "🚀 social-auto-upload macOS 一键打包脚本"
      echo "用法: ./build_app.sh [选项]"
      echo ""
      echo "选项:"
      echo "  -dmg,     --dmg      (默认) 仅生成 macOS DMG 拖拽安装镜像 (~600MB)"
      echo "  -upgrade, --upgrade  仅生成在线增量热更新包 (upgrade_mac.zip，用于上传 OSS)"
      echo "  -zip,     --zip      仅生成测试用解压整包 ZIP"
      echo "  -all,     --all      生成所有产物 (DMG + ZIP + 在线升级包)"
      echo "======================================================================"
      exit 0
      ;;
    *)
      echo "⚠️ 未知参数: $arg (支持: -dmg / -upgrade / -zip / -all / --help)"
      exit 1
      ;;
  esac
done

echo "======================================================================"
echo "🚀 开始执行 Wails 桌面端一键构建流程... [目标: $BUILD_TARGET]"
echo "======================================================================"

# 1. Wails CLI：通过 go run 调用项目锁定版本，不依赖也不影响全局安装的 wails
#    ⚠️ 全局 wails（当前 v2.8.2）被小映批量助手等其他项目使用，绝不能升级
WAILS_CLI_VERSION="v2.11.0"
echo "✅ Wails CLI 使用项目锁定版本: $WAILS_CLI_VERSION（go run 调用，不影响全局 CLI）"

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

# 探测并智能内嵌 Chromium 内核 (实现真正的本地离线免安装、开箱即用，并剔除历史版本瘦身)
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
"$PYTHON_BIN" "$PROJECT_ROOT/utils/sync_browser_kernel.py" "$DEST_PLAYWRIGHT" "$SRC_PLAYWRIGHT"
if [ $? -ne 0 ]; then
  echo "⚠️ 智能瘦身同步未完全成功，尝试备用复制..."
  rm -rf "$DEST_PLAYWRIGHT"
  mkdir -p "$DEST_PLAYWRIGHT"
  for d in "$SRC_PLAYWRIGHT"/chromium-* "$SRC_PLAYWRIGHT"/chromium_headless_shell-* "$SRC_PLAYWRIGHT"/ffmpeg-*; do
    if [ -d "$d" ]; then
      cp -R "$d" "$DEST_PLAYWRIGHT/"
    fi
  done
fi

# 5. 执行 Wails 桌面端编译
echo ""
echo "▶ [Step 3/3] 执行 Wails 桌面端整合打包 (Go + Vue 3)..."
cd "$PROJECT_ROOT/sau_desktop"
go run "github.com/wailsapp/wails/v2/cmd/wails@${WAILS_CLI_VERSION}" build

# 对于 macOS，将内置内核直接注入 .app 的 Resources 目录中
APP_PATH="$PROJECT_ROOT/sau_desktop/build/bin/小映分发助手.app"
if [ ! -d "$APP_PATH" ]; then
  APP_PATH="$PROJECT_ROOT/sau_desktop/build/bin/sau_desktop.app"
fi

if [ -d "$APP_PATH/Contents/MacOS" ]; then
  echo "📦 正在将 sau_engine Python 发布引擎装配入 .app 安装包的 MacOS 目录..."
  rm -rf "$APP_PATH/Contents/MacOS/sau_engine"
  mkdir -p "$APP_PATH/Contents/MacOS/sau_engine"
  cp -R "$PROJECT_ROOT/dist/sau_engine/"* "$APP_PATH/Contents/MacOS/sau_engine/"
fi

if [ -d "$APP_PATH/Contents/Resources" ]; then
  echo "📦 正在将 ms-playwright 浏览器内核同步注入 .app 安装包的 Resources 目录..."
  cp -R "$DEST_PLAYWRIGHT" "$APP_PATH/Contents/Resources/"
fi

# 6. 根据命令行参数按需生成制品 (避免全部生成占用过多磁盘空间)
RELEASE_DIR="$PROJECT_ROOT/dist_release"
mkdir -p "$RELEASE_DIR"
cd "$PROJECT_ROOT/sau_desktop/build/bin"
TARGET_APP_NAME="$(basename "$APP_PATH")"

APP_VER=$(grep -o '"productVersion": *"[^"]*"' "$PROJECT_ROOT/sau_desktop/wails.json" 2>/dev/null | cut -d'"' -f4)
if [ -z "$APP_VER" ]; then APP_VER="1.0.0"; fi

echo ""
echo "======================================================================"
echo "📦 正在按需归档产物 [目标模式: $BUILD_TARGET]..."

# 6.1 生成测试整包 ZIP (-zip 或 -all)
ZIP_FILE=""
if [ "$BUILD_TARGET" = "zip" ] || [ "$BUILD_TARGET" = "all" ]; then
  echo "▶ 正在生成测试用整包 ZIP..."
  ZIP_NAME="${TARGET_APP_NAME%.app}_mac.zip"
  rm -f "$ZIP_NAME" "$RELEASE_DIR/$ZIP_NAME"
  zip -r -q -y "$RELEASE_DIR/$ZIP_NAME" "$TARGET_APP_NAME"
  ZIP_FILE="$RELEASE_DIR/$ZIP_NAME"
  echo "  ✅ 测试整包已生成: $ZIP_FILE"
fi

# 6.2 生成在线热更新包 (-upgrade 或 -all)
UPGRADE_FILE=""
if [ "$BUILD_TARGET" = "upgrade" ] || [ "$BUILD_TARGET" = "all" ]; then
  echo "▶ 正在生成在线增量热更新包 (传至 OSS)..."
  UP_NAME="upgrade_mac_${APP_VER}.zip"
  rm -f "$RELEASE_DIR/$UP_NAME" "$RELEASE_DIR/upgrade_mac.zip"
  zip -r -q -y "$RELEASE_DIR/$UP_NAME" "$TARGET_APP_NAME"
  cp "$RELEASE_DIR/$UP_NAME" "$RELEASE_DIR/upgrade_mac.zip"
  UPGRADE_FILE="$RELEASE_DIR/$UP_NAME"
  echo "  ✅ 在线热更新包已生成: $UPGRADE_FILE (及 upgrade_mac.zip)"
fi

# 6.3 生成 macOS 标准 DMG 拖拽安装镜像 (-dmg 或 -all)
DMG_FILE=""
if [ "$BUILD_TARGET" = "dmg" ] || [ "$BUILD_TARGET" = "all" ]; then
  if [ "$(uname)" = "Darwin" ]; then
    echo "▶ 正在生成 macOS 标准 DMG 拖拽安装镜像..."
    DMG_STAGING="$PROJECT_ROOT/sau_desktop/build/bin/dmg_staging"
    rm -rf "$DMG_STAGING"
    mkdir -p "$DMG_STAGING"
    cp -R "$APP_PATH" "$DMG_STAGING/"
    ln -s /Applications "$DMG_STAGING/Applications"
    
    EULA_SRC="$PROJECT_ROOT/sau_desktop/build/windows/installer/resources/eula.txt"
    if [ -f "$EULA_SRC" ]; then
      cp "$EULA_SRC" "$DMG_STAGING/用户许可及服务协议.txt"
    fi

    DMG_FILE="$RELEASE_DIR/${TARGET_APP_NAME%.app}_macOS.dmg"
    rm -f "$DMG_FILE"
    hdiutil create -volname "${TARGET_APP_NAME%.app}" -srcfolder "$DMG_STAGING" -ov -format UDZO "$DMG_FILE" >/dev/null
    rm -rf "$DMG_STAGING"
    echo "  ✅ macOS DMG 安装镜像已生成: $DMG_FILE"
  fi
fi

echo ""
echo "======================================================================"
echo "🎉 全自动构建大功告成！"
echo "应用源目录: $APP_PATH"
if [ -n "$DMG_FILE" ]; then
  echo "1. DMG 主安装镜像: $DMG_FILE"
fi
if [ -n "$UPGRADE_FILE" ]; then
  echo "2. 在线热更新包:   $UPGRADE_FILE"
fi
if [ -n "$ZIP_FILE" ]; then
  echo "3. 测试整包 ZIP:   $ZIP_FILE"
fi
echo "======================================================================"

