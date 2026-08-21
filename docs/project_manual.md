# social-auto-upload 完整运行、调试、打包与 Wails 集成指南

> **项目定位**：`social-auto-upload` 是一个强大的自媒体多平台一键/定时自动发布工具。支持抖音、Bilibili、小红书、快手、微信视频号、YouTube 等 11 个平台的视频与图文发布，具备防封爬虫防护、多账号隔离、CLI 命令行以及 AI Agent Skill 化接口。

---

## 目录

- [一、环境准备与初始化](#一环境准备与初始化)
- [二、运行与调试模式 1：CLI 命令行主线 (推荐)](#二运行与调试模式-1cli-命令行主线-推荐)
- [三、运行与调试模式 2：Web 模式 (Flask + Vue3)](#三运行与调试模式-2web-模式-flask--vue3)
- [四、引擎二进制打包流程 (PyInstaller)](#四引擎二进制打包流程-pyinstaller)
- [五、集成至 Wails (Go + Vue) 桌面端架构指南](#五集成至-wails-go--vue-桌面端架构指南)
- [六、常见问题与踩坑排查](#六常见问题与踩坑排查)

---

## 一、环境准备与初始化

在 Windows 环境（PowerShell）中，执行以下命令完成底层运行环境搭建：

### 1. 复制配置文件模板
```powershell
if (!(Test-Path conf.py)) { Copy-Item conf.example.py conf.py }
```

### 2. 创建 Python 3.12 虚拟环境并激活
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### 3. 安装项目全量依赖（包含 CLI 与 Web 扩展）
```powershell
uv pip install -e .[web] xhs pyinstaller
# 若未安装 uv，亦可使用: pip install -e .[web] xhs pyinstaller
```

### 4. 安装 Patchright 浏览器自动化内核
```powershell
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright"
.\.venv\Scripts\patchright install chromium
```

### 5. 初始化 SQLite 本地数据库
```powershell
.\.venv\Scripts\python.exe db/createTable.py
```

---

## 二、运行与调试模式 1：CLI 命令行主线 (推荐)

项目以 `sau` 为统一 CLI 入口，所有账号凭证自动保存在 `cookies/<platform>_<account>.json` 中，天然支持**多账号隔离**与**多账号并发矩阵发布**。

### 1. 账号授权登录 (`login`)
> **💡 关键提示**：首次扫码登录时，**强烈建议加上 `--headed` 参数**唤起可见浏览器窗口。因为扫码后往往会触发手机短信二次验证 (2FA) 或人机拼图滑块，在弹出的窗口中手动完成验证后，程序会自动保存 Cookie 并关闭。

```powershell
# 抖音扫码登录
sau douyin login --account test_user --headed

# 小红书扫码登录
sau xiaohongshu login --account xhs_user --headed

# 快手扫码登录
sau kuaishou login --account ks_user --headed
```

### 2. 校验 Cookie 有效性 (`check`)
```powershell
sau douyin check --account test_user
# 返回 valid 表示凭证有效，可全自动后台发布
```

### 3. 自动发布视频 (`upload-video`)
```powershell
sau douyin upload-video --account test_user `
  --file "videos/demo.mp4" `
  --title "自动化测试视频标题" `
  --desc "这是视频正文描述" `
  --tags "AI工具,自动化"
```

### 4. 自动发布图文/笔记 (`upload-note`)
```powershell
sau xiaohongshu upload-note --account xhs_user `
  --images "videos/1.png" "videos/2.png" `
  --title "小红书图文笔记标题" `
  --note "笔记详细正文" `
  --tags "干货,图文分享"
```

### 5. 高级发布选项
- **定时发布**：`--schedule "2026-08-22 10:00"`
- **AI生成/自主声明**：`--declaration "内容由AI生成"`
- **作品归集**：`--collection "教程系列"`
- **调试观摩模式**：追加 `--headed` 与 `--debug` 参数观察浏览器交互

---

## 三、运行与调试模式 2：Web 模式 (Flask + Vue3)

如果你需要可视化网页管理界面，使用项目自带的批处理启动：

### 启动服务
```powershell
.\start-win.bat
```
会自动启动两个窗口：
1. **SAU Backend**：基于 Flask 的 RESTful API 接口与 SSE 实时扫码数据流（端口 `5409`）。
2. **SAU Frontend**：基于 Vite 的 Vue 3 前端界面（访问 `http://localhost:5173`）。

---

## 四、引擎二进制打包流程 (PyInstaller)

为方便将自动化发布能力嵌入到无 Python 环境的桌面端（如 Wails），需将其打包为独立可执行文件夹。

### 1. 打包命令

在已激活环境的 PowerShell 中执行：

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

### 2. 打包参数详解

| 参数标志 | 作用说明 |
| --- | --- |
| `--onedir` | 打包为独立目录（包含 `sau_engine.exe` 及 `_internal/` 依赖库），启动速度比单文件快 5~10 倍 |
| `--paths "."` | 将根目录加入 Python 搜索路径，确保 `conf.py`、`uploader` 模块被正常引入 |
| `--add-data` | 复制防爬 Hook 脚本 `stealth.min.js` 与配置文件到产物中 |
| `--collect-all` | 强行全量收集 `uploader`、`patchright` 等包的所有子模块与资源文件 |

### 3. 产物校验
打包完成后，产物位于 `dist/sau_engine/`。测试运行：
```powershell
.\dist\sau_engine\sau_engine.exe douyin --help
```
成功输出帮助信息即表示编译成功。

---

## 五、集成至 Wails (Go + Vue) 桌面端架构指南

### 1. 目录嵌入结构

将打包好的 `dist/sau_engine/` 整个拷贝到 Wails 工程的 `bin/` 目录下：

```text
my-wails-app/                # Wails 项目根目录
├── bin/
│   └── sau_engine/          # 👈 复制打包产物至此
│       ├── sau_engine.exe
│       └── _internal/
├── app.go                   # Go 后端
├── main.go                  # 入口
└── frontend/                # Vue 3 源码
```

### 2. Go 后端进程调度与日志推送 (`app.go`)

```go
package main

import (
	"bufio"
	"context"
	"fmt"
	"os/exec"
	"path/filepath"
	"syscall"

	"github.com/wailsapp/wails/v2/pkg/runtime"
)

type App struct {
	ctx context.Context
}

type UploadParam struct {
	Platform string `json:"platform"`
	Account  string `json:"account"`
	FilePath string `json:"filePath"`
	Title    string `json:"title"`
	Headless bool   `json:"headless"`
}

// 供 Vue 前端调用的发布方法
func (a *App) PublishMedia(param UploadParam) (string, error) {
	execPath, _ := filepath.Abs("./bin/sau_engine/sau_engine.exe")

	args := []string{
		param.Platform, "upload-video",
		"--account", param.Account,
		"--file", param.FilePath,
		"--title", param.Title,
	}
	if param.Headless {
		args = append(args, "--headless")
	} else {
		args = append(args, "--headed")
	}

	cmd := exec.CommandContext(a.ctx, execPath, args...)
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true} // 隐藏 CMD 黑框

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return "", err
	}

	if err := cmd.Start(); err != nil {
		return "", err
	}

	// 实时读取控制台日志并推送到 Vue
	go func() {
		scanner := bufio.NewScanner(stdout)
		for scanner.Scan() {
			runtime.EventsEmit(a.ctx, "sau-log", scanner.Text())
		}
	}()

	if err := cmd.Wait(); err != nil {
		return "", fmt.Errorf("任务失败: %w", err)
	}

	return "发布成功", nil
}
```

### 3. Vue 3 前端绑定与日志显示 (`Publisher.vue`)

```vue
<script setup>
import { ref, onMounted } from 'vue'
import { PublishMedia } from '../../wailsjs/go/main/App'
import { EventsOn } from '../../wailsjs/runtime/runtime'

const logs = ref([])

onMounted(() => {
  // 监听 Go 推送的 Python 实时日志
  EventsOn('sau-log', (msg) => { logs.value.push(msg) })
})

const handlePublish = async () => {
  await PublishMedia({
    platform: 'douyin',
    account: 'test_user',
    filePath: 'D:/demo.mp4',
    title: 'Wails集成测试',
    headless: true
  })
}
</script>
```

---

## 六、常见问题与踩坑排查

1. **扫码后卡住无响应**：
   - **原因**：无头模式下触发了手机短信 2FA 或拼图滑块验证。
   - **解决**：第一次登录时加入 `--headed` 参数在可见浏览器窗口中手动完成验证。
2. **打包后报 `BrowserType.launch: Executable doesn't exist`**：
   - **原因**：PyInstaller 运行时钩子重写了 `PLAYWRIGHT_BROWSERS_PATH` 环境变量。
   - **解决**：在 [sau_cli.py](file:///c:/Users/huijing/Desktop/小工具/自动发布/social-auto-upload/sau_cli.py) 最顶部加入动态读取 `%LOCALAPPDATA%\ms-playwright` 的环境注入代码。
3. **Web 方式提示 `'vite' is not recognized`**：
   - **原因**：`sau_frontend` 目录缺失 `node_modules`。
   - **解决**：在 `sau_frontend` 目录下运行 `npm install`。
