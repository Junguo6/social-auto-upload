package engine

// TargetAccount 矩阵目标账号
type TargetAccount struct {
	Platform string `json:"platform"`
	Account  string `json:"account"`
}

// PublishParam 单账号发布参数
type PublishParam struct {
	Platform           string   `json:"platform"`
	Action             string   `json:"action"` // upload-video / upload-note
	Account            string   `json:"account"`
	FilePath           string   `json:"filePath"`
	Images             []string `json:"images"`
	Title              string   `json:"title"`
	Desc               string   `json:"desc"`
	Tags               string   `json:"tags"`
	Thumbnail          string   `json:"thumbnail"`          // 自定义主封面路径
	ThumbnailLandscape string   `json:"thumbnailLandscape"` // 推荐横版封面路径
	ThumbnailPortrait  string   `json:"thumbnailPortrait"`  // 推荐竖版封面路径
	Tid                int      `json:"tid"`                // B站分区分类ID
	ShortTitle         string   `json:"shortTitle"`         // 视频号短标题
	Category           string   `json:"category"`           // 视频号原创内容分类
	Draft              bool     `json:"draft"`              // 视频号存为草稿
	Schedule           string   `json:"schedule"`           // 定时发布时间 (YYYY-MM-DD HH:mm)
	Declaration        string   `json:"declaration"`        // 内容声明 (如 内容由AI生成)
	Collection         string   `json:"collection"`         // 合集/专栏名称
	ProductLink        string   `json:"productLink"`        // 抖音小黄车商品链接
	ProductTitle       string   `json:"productTitle"`       // 抖音小黄车商品短标题
	Visibility         string   `json:"visibility"`         // 可见性范围: public / unlisted / private
	Playlist           string   `json:"playlist"`           // YouTube 播放列表
	Bgm                string   `json:"bgm"`                // 图文配乐搜索名
	Note               string   `json:"note"`               // 图文正文
	Notef              string   `json:"notef"`              // 长正文文件路径
	Headless           bool     `json:"headless"`
}

// AccountPublishTask 单个账号的独立发布执行参数 (支持通用继承或专属独立覆盖)
type AccountPublishTask struct {
	TaskId             string   `json:"taskId"`             // 前端任务唯一 ID (用于日志与状态严格绑定)
	Platform           string   `json:"platform"`           // 目标平台标识
	Account            string   `json:"account"`            // 目标账号磁盘标识
	Nickname           string   `json:"nickname"`           // 展示昵称 (用于日志打印)
	Action             string   `json:"action"`             // upload-video / upload-note
	FilePath           string   `json:"filePath"`           // 视频或主媒体文件路径
	Images             []string `json:"images"`             // 图文模式下的图片路径数组
	Title              string   `json:"title"`              // 该平台/账号专属标题
	Desc               string   `json:"desc"`               // 该平台/账号专属描述
	Tags               string   `json:"tags"`               // 该平台/账号专属标签
	Thumbnail          string   `json:"thumbnail"`          // 专属主封面
	ThumbnailLandscape string   `json:"thumbnailLandscape"` // 专属横版封面
	ThumbnailPortrait  string   `json:"thumbnailPortrait"`  // 专属竖版封面
	Tid                int      `json:"tid"`                // B站分区 ID
	ShortTitle         string   `json:"shortTitle"`         // 短标题
	Category           string   `json:"category"`           // 视频号分类
	Draft              bool     `json:"draft"`              // 存为草稿
	Schedule           string   `json:"schedule"`           // 定时发布
	Declaration        string   `json:"declaration"`        // 合规/原创/AI声明
	Collection         string   `json:"collection"`         // 专栏合集
	ProductLink        string   `json:"productLink"`        // 带货商品链接
	ProductTitle       string   `json:"productTitle"`       // 带货商品短标题
	Visibility         string   `json:"visibility"`         // 可见性
	Playlist           string   `json:"playlist"`           // 播放列表
	Bgm                string   `json:"bgm"`                // 背景音乐
	Note               string   `json:"note"`               // 图文正文
	Notef              string   `json:"notef"`              // 长正文文件路径
	InitialDelaySeconds int     `json:"initialDelaySeconds"` // 任务执行前的前置防风控延时(秒)
	DelaySeconds       int      `json:"delaySeconds"`       // 单步骤特定防风控延时(秒)，<=0时回退使用通道默认延时
	Headless           bool     `json:"headless"`           // 静默无头模式
}

// MatrixPublishParam 矩阵全景差异化发布主请求参数
type MatrixPublishParam struct {
	Concurrency int                  `json:"concurrency"` // 最大并发 Goroutine 数 (默认 3)
	Tasks       []AccountPublishTask `json:"tasks"`       // 各账号差异化发布任务列表
}

// BatchPublishParam 矩阵批量发布参数 (向前兼容)
type BatchPublishParam struct {
	Targets            []TargetAccount `json:"targets"`     // 批量目标账号列表
	Concurrency        int             `json:"concurrency"` // 最大并发 Goroutine 数
	Action             string          `json:"action"`      // upload-video / upload-note
	FilePath           string          `json:"filePath"`
	Images             []string        `json:"images"`
	Title              string          `json:"title"`
	Desc               string          `json:"desc"`
	Tags               string          `json:"tags"`
	Thumbnail          string          `json:"thumbnail"`
	ThumbnailLandscape string          `json:"thumbnailLandscape"`
	ThumbnailPortrait  string          `json:"thumbnailPortrait"`
	Tid                int             `json:"tid"`
	ShortTitle         string          `json:"shortTitle"`
	Category           string          `json:"category"`
	Draft              bool            `json:"draft"`
	Schedule           string          `json:"schedule"`
	Declaration        string          `json:"declaration"`
	Collection         string          `json:"collection"`
	ProductLink        string          `json:"productLink"`
	ProductTitle       string          `json:"productTitle"`
	Visibility         string          `json:"visibility"`
	Playlist           string          `json:"playlist"`
	Bgm                string          `json:"bgm"`
	Note               string          `json:"note"`
	Notef              string          `json:"notef"`
	Headless           bool            `json:"headless"`
}

// AccountPublishResult 单个账号发布执行结果
type AccountPublishResult struct {
	TaskId   string `json:"taskId"`
	Platform string `json:"platform"`
	Account  string `json:"account"`
	Success  bool   `json:"success"`
	ErrorMsg string `json:"errorMsg"`
}

// ScreencastFrame 实时浏览器渲染画面帧
type ScreencastFrame struct {
	TaskId          string  `json:"taskId"`
	Data            string  `json:"data"` // JPEG base64 字符串
	Width           int     `json:"width"`
	Height          int     `json:"height"`
	OffsetTop       float64 `json:"offsetTop"`
	PageScaleFactor float64 `json:"pageScaleFactor"`
}

// EngineEvent 引擎日志与状态事件
type EngineEvent struct {
	Type     string `json:"type"` // "log" | "task_start" | "task_success" | "task_error"
	TaskId   string `json:"taskId,omitempty"`
	Platform string `json:"platform,omitempty"`
	Account  string `json:"account,omitempty"`
	Message  string `json:"message"`
}

// VideoFileInfo 扫描到的视频文件元数据
type VideoFileInfo struct {
	Name string `json:"name"`
	Path string `json:"path"`
	Size int64  `json:"size"`
	Ext  string `json:"ext"`
}

// DirectoryBatchParam 目录批量分发任务参数
type DirectoryBatchParam struct {
	Files              []VideoFileInfo `json:"files"`              // 待发布的视频文件列表
	Targets            []TargetAccount `json:"targets"`            // 目标账号列表
	Concurrency        int             `json:"concurrency"`        // 每个视频分发时的并发数
	TitleTemplate      string          `json:"titleTemplate"`      // 标题模板 (支持 {filename} 占位符)
	Desc               string          `json:"desc"`               // 正文描述
	Tags               string          `json:"tags"`               // 标签
	Thumbnail          string          `json:"thumbnail"`          // 统一封面
	ThumbnailLandscape string          `json:"thumbnailLandscape"` // 横版封面
	ThumbnailPortrait  string          `json:"thumbnailPortrait"`  // 竖版封面
	Tid                int             `json:"tid"`                // B站分区
	ShortTitle         string          `json:"shortTitle"`         // 视频号短标题
	Category           string          `json:"category"`           // 视频号分类
	Draft              bool            `json:"draft"`              // 存为草稿
	Schedule           string          `json:"schedule"`           // 定时发布
	Declaration        string          `json:"declaration"`        // 合规声明
	Collection         string          `json:"collection"`         // 专栏合集
	ProductLink        string          `json:"productLink"`        // 带货商品链接
	ProductTitle       string          `json:"productTitle"`       // 带货商品短标题
	Visibility         string          `json:"visibility"`         // 可见性
	Playlist           string          `json:"playlist"`           // 播放列表
	Headless           bool            `json:"headless"`           // 静默运行
}

// DirectoryPublishResult 单个视频文件的矩阵发布执行结果汇总
type DirectoryPublishResult struct {
	FileName       string                 `json:"fileName"`
	FilePath       string                 `json:"filePath"`
	AccountResults []AccountPublishResult `json:"accountResults"`
	AllSuccess     bool                   `json:"allSuccess"`
}

// AccountStatus 账号状态
type AccountStatus struct {
	Platform string `json:"platform"`
	Account  string `json:"account"`
	IsValid  bool   `json:"isValid"`
	Msg      string `json:"msg"`
}

// LoginResult 账号授权登录返回结果
type LoginResult struct {
	Success   bool   `json:"success"`
	Platform  string `json:"platform"`
	Account   string `json:"account"`   // 磁盘安全存储标识（如 account_01 或 user_001）
	Nickname  string `json:"nickname"`  // 真实展示昵称（完整保留 Emoji 和特殊字符）
	FinderUid string `json:"finderUid"` // 平台唯一 UID
	Msg       string `json:"msg"`
}

// PipelineTaskLane 单个工作流并发协程通道 (泳道)
type PipelineTaskLane struct {
	LaneID            string               `json:"laneId"`
	LaneName          string               `json:"laneName"`
	Tasks             []AccountPublishTask `json:"tasks"`
	DelayBetweenTasks int                  `json:"delayBetweenTasks"` // 串行任务间防风控延时(秒)
	ScheduledAt       string               `json:"scheduledAt"`       // 通道计划执行时间
}

// PipelinePublishParam 多线程工作流发布参数
type PipelinePublishParam struct {
	Lanes []PipelineTaskLane `json:"lanes"`
}
