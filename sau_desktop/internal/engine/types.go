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

// BatchPublishParam 矩阵批量发布参数
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
	Platform string `json:"platform"`
	Account  string `json:"account"`
	Success  bool   `json:"success"`
	ErrorMsg string `json:"errorMsg"`
}

// EngineEvent 引擎日志与状态事件
type EngineEvent struct {
	Type     string `json:"type"` // "log" | "error" | "success" | "progress"
	Platform string `json:"platform,omitempty"`
	Account  string `json:"account,omitempty"`
	Message  string `json:"message"`
}

// AccountStatus 账号状态
type AccountStatus struct {
	Platform string `json:"platform"`
	Account  string `json:"account"`
	IsValid  bool   `json:"isValid"`
	Msg      string `json:"msg"`
}
