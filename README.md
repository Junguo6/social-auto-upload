# social-auto-upload (定制二次开发版)

> 本仓库为基于原开源项目 [dreammis/social-auto-upload](https://github.com/dreammis/social-auto-upload) 进行定制重构与功能增强的二次开发版本。

`social-auto-upload` 是一个面向自媒体创作者与矩阵运营者的**多平台自动化发布引擎**。支持对**抖音、Bilibili、小红书、快手、微信视频号、YouTube、TikTok、百家号、支付宝生活号、微博、虎扑** 等 11 个主流平台进行视频与图文笔记的一键发布与定时发布。

---

## 🌟 二次开发主要特性与修护

本分支（`pr-jg`）针对桌面端集成与工程打包进行了深度优化与修复：

1. 🛠️ **修复 PyInstaller 引擎打包 BUG**：
   - 解决打包为二进制 `sau_engine.exe` 后运行找不到 Chrome 浏览器的致命异常（`BrowserType.launch: Executable doesn't exist`）。
   - 实现跨平台（Windows / macOS / Linux）及跨用户路径动态解析 `ms-playwright` 内核。
2. 🔌 **Wails 桌面端原生集成支持**：
   - 支持将 Python 发布引擎一键打包为可被 **Wails (Go + Vue)** 侧边进程（Sidecar）调用的可执行包，提供控制台 stdout 实时日志推送到 Vue 界面。
3. ⚡ **双运行模式修护与环境全自动化**：
   - **CLI 模式**：通过统一命令 `sau <platform> <action>` 实现多账号矩阵隔离与并发无头发布。
   - **Web 模式**：修护环境依赖与数据库建表脚本，支持 Flask + Vue3 可视化网页管理。

---

## 🚀 快速开始

详细的技术架构、测试调试与 Wails 集成文档请参阅：👉 **[完整运行、调试与打包指南](./docs/project_manual.md)**

### 1. 基础环境初始化

```powershell
# 复制配置文件模板
if (!(Test-Path conf.py)) { Copy-Item conf.example.py conf.py }

# 创建 Python 3.12 虚拟环境并激活
python -m venv .venv
.\.venv\Scripts\activate

# 一键安装主线与 Web 依赖
uv pip install -e .[web] xhs pyinstaller

# 下载 Patchright 浏览器自动化内核
.\.venv\Scripts\patchright install chromium
```

---

### 2. 方式 1：CLI 命令行快速使用 (推荐)

```powershell
# 1. 账号首次授权登录（强烈建议带上 --headed 弹窗扫码/处理验证码）
sau douyin login --account test_user --headed

# 2. 检查账号 Cookie 有效性
sau douyin check --account test_user

# 3. 一键自动发布视频
sau douyin upload-video --account test_user --file "videos/demo.mp4" --title "测试视频" --desc "视频描述" --tags "AI,自动化"

# 4. 一键自动发布图文
sau xiaohongshu upload-note --account xhs_user --images "1.png" "2.png" --title "图文标题" --note "正文内容"
```

---

### 3. 方式 2：Web 可视化模式

```powershell
# 启动 Flask API (端口 5409) 与 Vue3 前端 (端口 5173)
.\start-win.bat
```
浏览器访问：`http://localhost:5173`

---

### 4. 引擎二进制打包 (用于 Wails 桌面端)

```powershell
pyinstaller --noconfirm --onedir `
  --name "sau_engine" `
  --paths "." `
  --add-data "utils/stealth.min.js;utils" `
  --add-data "conf.py;." `
  --collect-all "uploader" `
  --collect-all "utils" `
  --collect-all "myUtils" `
  --collect-all "patchright" `
  --collect-all "playwright" `
  --collect-all "loguru" `
  sau_cli.py
```
打包产物为 `dist/sau_engine/`，直接复制到 Wails 工程的 `bin/` 目录下即可供 Go 侧调用。

---

## 📜 开源协议与致谢

- 上游开源仓库：[dreammis/social-auto-upload](https://github.com/dreammis/social-auto-upload)
- Bilibili 核心基于开源项目 [biliup](https://github.com/biliup/biliup) 接入。
- 本二次开发仓库遵从 [MIT License](LICENSE) 开源许可证。
