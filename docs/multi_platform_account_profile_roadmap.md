# 多平台账号真实昵称与免填登录优化规划文档 (Multi-Platform Profile & Auto-Login Roadmap)

## 一、 核心目标与规范

1. **零门槛免填登录（Zero-Input Login）**：
   - 用户在桌面端或 CLI 登录任何支持的自媒体平台时，账号唯一标识均为选填（默认 `auto`）。
   - 扫码授权完成后，系统自动通过 DOM 探测、API 查询或 Cookie 解析获取用户的**真实平台昵称**与**平台安全唯一 UID**。

2. **跨平台 Emoji 与字符安全隔离规范**：
   - **磁盘持久化安全（File Safety）**：磁盘 Cookie 文件名始终保持为安全 ASCII 格式，如 `cookies/{platform}_{safe_uid}.json`，防止 Windows / Linux 跨系统因 Emoji 产生乱码或读写异常。
   - **富文本无损展现（Lossless Display）**：在 Cookie JSON 内注入 `__account_meta__` 元数据对象，完整保留用户包含 Emoji、特殊符号的平台昵称。
   - **UI 与业务全链路**：前端卡片、矩阵选择、并发监控优先展示带 Emoji 的真实昵称并辅以 UID Tag。

---

## 二、 各平台昵称与 UID 提取方案

| 平台名称 | 平台标识 (`platform`) | 登录方式 | 真实昵称提取源 (DOM / API / Storage) | 唯一安全 UID 提取源 | 规划状态 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **微信视频号** | `tencent` | 扫码登录 | `h2.finder-nickname` / `.side-bar-footer span.name` / `div.account-info` | `span.finder-uniq-id` / `#finder-uid-copy` (`sph...`) | 🟢 核心已实现 & 持续强化 |
| **抖音创作者平台** | `douyin` | 扫码登录 | `.user-info-name` / `.semi-navigation-header-title` / `div[class*="account-name"]` | 登录 cookies 中 `user_id` / `unique_id` / DOM | 🟡 待完善 |
| **快手创作者服务** | `kuaishou` | 扫码登录 | `div.user-name` / `.user-info .name` / `div.header-user-info span` | 快手号 / 创作者 UID (`user_id`) | 🟡 待完善 |
| **小红书创作者平台** | `xiaohongshu` | 扫码登录 | `span.name` / `.user-info .name` / `.author-name` | 小红书号 / `red_id` / `user_id` | 🟡 待完善 |
| **哔哩哔哩 (B站)** | `bilibili` | 扫码/终端 (`biliup`) | B站导航接口 `https://api.bilibili.com/x/web-interface/nav` -> `uname` | `token_info.mid` | 🟡 待完善 |
| **百度百家号** | `baijiahao` | 扫码登录 | `.author-name` / `div.user-name` | 百家号作者 ID / 账号标识 | 🟡 待完善 |
| **支付宝生活号** | `alipay` | 扫码登录 | `span.user-name` / `div.account-name` | 生活号商户 ID / UID | 🟡 待完善 |
| **新浪微博** | `weibo` | 扫码登录 | `div.gn_name` / `div.username` / `span.name` | 微博 UID (`uid`) | 🟡 待完善 |
| **虎扑体育** | `hupu` | 扫码登录 | `.user-name` / 个人主页昵称节点 | 虎扑 UID (`puid`) | 🟡 待完善 |
| **YouTube Studio** | `youtube` | 浏览器授权 | `yt-formatted-string#channel-name` / `#avatar-btn` | YouTube Channel ID (`UC...`) | 🟡 待完善 |

---

## 三、 推进阶段与任务分解

- [x] **Phase 1: 微信视频号深度验证与全链路贯通**
  - 微信视频号 DOM 昵称与 `sph...` UID 提取。
  - 元数据注入、纯 ASCII 文件命名与前端无损展示。
- [ ] **Phase 2: 核心主流短视频平台适配 (抖音、快手、小红书、B站)**
  - 完善 `douyin_cookie_gen`、`ks_cookie_gen`、`xiaohongshu_cookie_gen` 的个人资料探测与元数据注入。
  - 完善 `bilibili` 凭证换取真实 `uname` 接口。
- [ ] **Phase 3: 图文与综合平台适配 (百家号、支付宝、微博、虎扑、YouTube)**
  - 统一全平台 `login` 输出 JSON 协议 (`{platform} login flow completed: {"nickname": "...", "finder_uid": "..."}`)。
- [ ] **Phase 4: 桌面端凭证扫描与自动同步能力**
  - 桌面端启动与刷新时，自动扫描 `cookies/` 目录并更新 Pinia Store 中的账号与昵称。
