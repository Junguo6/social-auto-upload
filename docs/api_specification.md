# social-auto-upload 详细 API 接口规范文档

> **📌 接口选型指南**：
> - **CLI 命令行引擎接口（推荐 / 主线）**：通过直接执行 `sau_engine.exe <platform> <action> [flags]` 进程调用。**这是集成至 Wails / Electron / C# / Python 等桌面端程序最推荐的方式**（无端口冲突、按需启动释放内存、架构最解耦）。
> - **HTTP RESTful & SSE 接口（备选 / Web模式）**：基于 Flask HTTP 服务（端口 `5409`），适用于局域网/服务器远程 B/S 架构调用。

---

## 目录

- [一、 CLI 命令行引擎接口规范](#一-cli-命令行引擎接口规范)
  - [1. 账号授权登录接口 (`login`)](#1-账号授权登录接口-login)
  - [2. 账号状态检查接口 (`check`)](#2-账号状态检查接口-check)
  - [3. 视频发布接口 (`upload-video`)](#3-视频发布接口-upload-video)
  - [4. 图文/笔记发布接口 (`upload-note`)](#4-图文笔记发布接口-upload-note)
- [二、 HTTP RESTful & SSE 接口规范 (Web服务)](#二-http-restful--sse-接口规范-web服务)
  - [1. SSE 扫码登录数据流接口 (`GET /api/login`)](#1-sse-扫码登录数据流接口-get-apilogin)
  - [2. 账号状态查询接口 (`POST /api/check_login`)](#2-账号状态查询接口-post-apicheck_login)
  - [3. 视频文件上传暂存接口 (`POST /api/upload_video_file`)](#3-视频文件上传暂存接口-post-apiupload_video_file)
  - [4. 视频作品一键发布接口 (`POST /api/post_video`)](#4-视频作品一键发布接口-post-apipost_video)
  - [5. 账号及文件记录查询接口](#5-账号及文件记录查询接口)
- [三、 状态码与日志响应规范](#三-状态码与日志响应规范)

---

## 一、 CLI 命令行引擎接口规范

命令行调用的统一契约格式为：

```text
sau_engine.exe <platform> <action> [flags]
```

### 平台枚举定义 (`platform`)

| 枚举值 | 对应平台名称 | 视频发布支持 | 图文发布支持 | 登录方式 |
| --- | --- | :-: | :-: | --- |
| `douyin` | 抖音 | ✅ | ✅ | 扫码登录 |
| `xiaohongshu` | 小红书 | ✅ | ✅ | 扫码登录 |
| `kuaishou` | 快手 | ✅ | ✅ | 扫码登录 |
| `tencent` | 微信视频号 | ✅ | ⚠️ 待完善 | 扫码登录 |
| `bilibili` | Bilibili 弹幕网 | ✅ | ❌ | 扫码登录 |
| `youtube` | YouTube | ✅ | ❌ | 交互式 Google 登录 |
| `baijiahao` | 百家号 | ✅ | ❌ | 扫码登录 |
| `weibo` | 微博 | ✅ | ❌ | 扫码登录 |
| `hupu` | 虎扑 | ✅ | ❌ | 扫码登录 |
| `alipay` | 支付宝生活号 | ✅ | ❌ | 扫码登录 |
| `tiktok` *(内部模块)* | TikTok | ✅ | ❌ | 仅 Python SDK 支持 (CLI暂未暴露) |

---

### 1. 账号授权登录接口 (`login`)

发起指定平台的账号登录流程，自动保存凭证至 `cookies/<platform>_<account>.json`。

#### 命令行格式
```powershell
sau_engine.exe <platform> login --account <account_name> [--headed] [--debug]
```

#### 参数说明
| 参数名 | 必填 | 类型 | 默认值 | 约束 / 说明 |
| --- | :-: | :-: | --- | --- |
| `platform` | **是** | 字符串 | - | 平台枚举值，如 `douyin` |
| `action` | **是** | 字符串 | - | 固定值 `login` |
| `--account` | **是** | 字符串 | - | **账号唯一标识名称**。例如 `--account user_001`。用于隔离保存不同的 Cookie 文件（存储为 `cookies/<platform>_<account>.json`）。支持同平台多账号矩阵隔离。 |
| `--headed` | 可选 | 布尔开关 | `false` | **开启显示 Chrome 窗口**。添加此标记后会弹出 Chrome 窗口，适合首次扫码登录、处理验证码或直观观摩发布全过程。 |
| `--headless` | 可选 | 布尔开关 | `true` | **后台静默无头模式**（默认）。后台静默运行自动发布。 |
| `--debug` | 可选 | 布尔开关 | `false` | **开启调试日志模式**。打印详细的 DOM 查找日志，并在出错时自动截图存盘以便排查。 |

#### 输出结果
- **进程退出码**：`0` (成功) / `1` (失败)
- **stdout 关键字**：包含 `login flow completed` 标记登录成功。

---

### 2. 账号状态检查接口 (`check`)

快速检验指定账号的 Cookie 凭证是否仍然有效。

#### 命令行格式
```powershell
sau_engine.exe <platform> check --account <account_name>
```

#### 参数说明
| 参数名 | 必填 | 类型 | 说明 |
| --- | :-: | :-: | --- |
| `platform` | **是** | 字符串 | 平台枚举值 |
| `action` | **是** | 字符串 | 固定值 `check` |
| `--account` | **是** | 字符串 | 待校验的账号唯一标识 |

#### 输出结果
- **标准输出 (stdout)**：
  - `valid`：凭证有效，可后台静默发布（退出码 `0`）
  - `invalid`：凭证已失效或不存在（退出码 `1`）

---

### 3. 视频发布接口 (`upload-video`)

自动将指定的本地视频文件发布到目标平台。

#### 命令行格式
```powershell
sau_engine.exe <platform> upload-video `
  --account <account_name> `
  --file "<video_path>" `
  --title "<title>" `
  [--desc "<description>"] `
  [--tags "<tags>"] `
  [--thumbnail "<thumbnail_path>"] `
  [--thumbnail-landscape "<landscape_path>"] `
  [--thumbnail-portrait "<portrait_path>"] `
  [--schedule "YYYY-MM-DD HH:mm"] `
  [--declaration "<declaration>"] `
  [--collection "<collection_name>"] `
  [--product-link "<url>"] [--product-title "<name>"] `
  [--visibility "<visibility>"] [--playlist "<playlist>"] `
  [--headed] [--debug]
```

#### 参数详细说明
| 参数标志 | 必填 | 数据类型 | 默认值 | 说明与约束 |
| --- | :-: | :-: | --- | --- |
| `--account` | **是** | 字符串 | - | 账号唯一标识 |
| `--file` | **是** | 文件路径 | - | 本地视频绝对路径（支持 `.mp4`, `.mov`） |
| `--title` | **是** | 字符串 | - | 视频标题（**抖音/小红书≤30字，微博≤30字，虎扑4-40字，快手/视频号≤50字，B站/百家号≤80字，YouTube≤100字**） |
| `--desc` | 否 | 字符串 | `""` | 视频正文详细描述/简介（**注：B站发布时该项为必填**） |
| `--tags` | 否 | 字符串 | `""` | 英文逗号分隔的话题，如 `"AI,自动化,教程"` |
| `--thumbnail` | 否 | 文件路径 | `None` | 自定义主封面图片路径（`.png/.jpg`） |
| `--thumbnail-landscape` | 否 | 文件路径 | `None` | 推荐横版封面路径（抖音/视频号） |
| `--thumbnail-portrait` | 否 | 文件路径 | `None` | 推荐竖版封面路径（抖音/视频号） |
| `--tid` | **B站必填** | 整数 (int) | `None` | **Bilibili 分区分类 ID**（如 `171`: 电子竞技, `230`: 科技, `21`: 日常）。**上传B站时必填** |
| `--short-title` | 否 | 字符串 | `None` | **视频号短标题**（微信视频号特有短标题） |
| `--category` | 否 | 字符串 | `None` | 原创内容分类名称（微信视频号支持） |
| `--draft` | 否 | 布尔开关 | `false` | **存为草稿**（微信视频号支持，只上传保存至草稿箱而不直接发布） |
| `--schedule` | 否 | 时间格式 | `None` | 定时发布时间，格式 `"YYYY-MM-DD HH:mm"` |
| `--declaration` | 否 | 字符串 | `None` | 内容声明，如 `"内容由AI生成"` |
| `--collection` | 否 | 字符串 | `None` | 归集到的合集/专栏名称（抖音/视频号/快手/百家号/支付宝/微博支持） |
| `--product-link` | 否 | URL字符串 | `None` | 带货商品/小黄车链接（抖音带货支持） |
| `--product-title` | 否 | 字符串 | `None` | 带货商品短标题（抖音带货支持） |
| `--visibility` | 否 | 枚举 | `public` | 可见性范围：`public`/`unlisted`/`private` （B站/YouTube支持） |
| `--playlist` | 否 | 字符串 | `None` | 自动加入的 YouTube Playlist 名字 |

---

### 4. 图文/笔记发布接口 (`upload-note`)

自动将本地图片发布为图文笔记（抖音/小红书/快手支持）。

#### 命令行格式
```powershell
sau_engine.exe <platform> upload-note `
  --account <account_name> `
  --images "<img1_path>" "<img2_path>" `
  --title "<title>" `
  [--note "<note_text>"] `
  [--notef "<note_file_path>"] `
  [--tags "<tags>"] `
  [--bgm "<music_name>"] `
  [--schedule "YYYY-MM-DD HH:mm"] `
  [--headed] [--debug]
```

#### 参数详细说明
| 参数标志 | 必填 | 数据类型 | 说明 |
| --- | :-: | :-: | --- |
| `--account` | **是** | 字符串 | 账号唯一标识 |
| `--images` | **是** | 路径列表 | 多张图片的绝对路径（空格隔开） |
| `--title` | **是** | 字符串 | 图文标题（小红书≤20字，抖音≤30字） |
| `--note` | 否 | 字符串 | 图文正文文本内容 |
| `--notef` | 否 | 文件路径 | 读取长正文的本地 `.txt/.md` 文件路径 |
| `--tags` | 否 | 字符串 | 英文逗号分隔的话题列表 |
| `--bgm` | 否 | 字符串 | 配乐 BGM 搜索名称 |

---

## 二、 HTTP RESTful & SSE 接口规范 (Web服务模式)

基准服务地址：`http://localhost:5409` （由 `sau_backend.py` 启动）

> ⚠️ **注意**：网页后端接口直接映射 `sau_backend.py` 中的原生路由，无 `/api/` 前缀，区分大小写。

### 1. SSE 扫码登录数据流接口 (`GET /login`)

通过 Server-Sent Events (SSE) 协议推送实时登录扫码状态及二维码 Base64 图像。

- **请求路径**：`/login`
- **请求方法**：`GET`
- **查询参数**：
  - `type` (字符串，必填)：平台类型，可选 `douyin`, `xiaohongshu`, `kuaishou`, `tencent`
  - `userName` (字符串，必填)：用于保存 Cookie 的自定义账号标识名称

#### SSE 消息事件推送到前端格式
```text
event: message
data: {"type": "qrcode", "url": "data:image/png;base64,iVBORw0KGgoAAAAN..."}

event: message
data: {"type": "success", "msg": "登录成功！", "filePath": "cookies/douyin_user01.json"}

event: message
data: {"type": "error", "msg": "登录超时，请重试"}
```

---

### 2. 账号状态校验与更新接口 (`POST /updateUserinfo`)

触发底层对数据库中保存的指定账号 Cookie 凭证进行校验并更新状态。

- **请求路径**：`/updateUserinfo`
- **请求方法**：`POST`
- **Content-Type**：`application/json`

#### Request Body
```json
{
  "id": 1
}
```

#### Response Body
```json
{
  "code": 200,
  "msg": "更新成功",
  "status": true
}
```

---

### 3. 视频文件上传暂存接口 (`POST /upload`)

上传待发布的视频/图片文件到后端暂存目录。

- **请求路径**：`/upload`
- **请求方法**：`POST`
- **Content-Type**：`multipart/form-data`

#### Form Data
- `file` (File，必填)：二进制文件

#### Response Body
```json
{
  "code": 200,
  "msg": "上传成功",
  "data": {
    "id": 5,
    "filename": "demo.mp4",
    "filesize": 15420100,
    "file_path": "c:\\Users\\...\\videos\\1724215900_demo.mp4"
  }
}
```

---

### 4. 视频作品一键发布接口 (`POST /postVideo`)

根据传入的文件 ID 与账号 ID 列表，异步触发底层 Playwright/Patchright 进行全自动发布。

- **请求路径**：`/postVideo`
- **请求方法**：`POST`
- **Content-Type**：`application/json`

#### Request Body Schema
```json
{
  "type": 3,
  "fileList": [5],
  "accountList": [1],
  "title": "爆款自动化测试标题",
  "tags": "AI工具,自动化",
  "category": 0,
  "thumbnail": "",
  "productLink": "",
  "productTitle": "",
  "isDraft": false,
  "enableTimer": false
}
```
- **字段说明**：
  - `type`: 平台类型ID (1:小红书, 2:微信视频号, 3:抖音, 4:快手)
  - `fileList`: 上传暂存文件 ID 数组
  - `accountList`: 关联选择的账号 ID 数组
  - `isDraft`: 是否只保存为草稿

#### Response Body
```json
{
  "code": 200,
  "msg": "发布任务提交成功！"
}
```

---

### 5. 账号及文件记录查询接口

#### 获取用户账号列表
- **路径**：`GET /getAccounts`
- **返回**：数据库中存储的所有平台与账号列表信息。

#### 获取有效用户账号列表
- **路径**：`GET /getValidAccounts`
- **返回**：过滤后凭证有效的账号列表。

#### 获取文件记录列表
- **路径**：`GET /getFiles`
- **返回**：数据库暂存的历史视频文件列表。

---

## 三、 状态码与日志响应规范

### CLI 进程状态码说明

| 退出码 (Exit Code) | 含义类型 | 说明 |
| :-: | --- | --- |
| `0` | **成功 (Success)** | 任务执行完毕（登录已保存、凭证有效、视频/图文发布成功提交）。 |
| `1` | **失败 (Error / Invalid)** | 凭证无效、缺少必填参数、文件不存在、页面 DOM 选择器查找超时或网路异常。 |

### Loguru 日志输出格式
包含时间戳、日志等级、组件标识与图标：
```text
2026-08-21 14:30:15 | INFO: 🥹 cookie 失效了，准备打开浏览器重新登录
2026-08-21 14:30:20 | INFO: 🥳 扫码成功，已经跳转到登录后页面...
2026-08-21 14:30:35 | SUCCESS: 🎉 视频发布提交成功！
```
