package auth

import "time"

// SeedInfo 随机种子持久化结构
type SeedInfo struct {
	RandomSeed   string `json:"random_seed"`
	Checksum     string `json:"checksum"`
	CreatedAt    string `json:"created_at"`
	LastBackupAt string `json:"last_backup_at"`
}

type seedTargetKind int

const (
	seedTargetFile seedTargetKind = iota
	seedTargetRegistry
)

type seedTarget struct {
	Path string
	Kind seedTargetKind
}

// DeviceIdentity 设备标识信息
type DeviceIdentity struct {
	MachineID string `json:"machine_id"`
	NewSN     string `json:"new_sn"`
}

// AuthOverview 统一对外的鉴权与授权状态模型 (供前端展示)
type AuthOverview struct {
	NewSN          string     `json:"new_sn"`
	MachineID      string     `json:"machine_id"`
	IsActivated    bool       `json:"is_activated"`
	IsExpired      bool       `json:"is_expired"`
	DaysRemaining  int        `json:"days_remaining"`
	Deadline       string     `json:"deadline"`
	UserId         string     `json:"user_id"`
	Version        string     `json:"version"`
	Announcement   string     `json:"announcement"`
	HelpUrl        string     `json:"help_url"`
	AgentNotice    string     `json:"agent_notice"`
	AgentWebsite   string     `json:"agent_website"`
	M100Activated  bool       `json:"m100_activated"`
	M122Activated   bool       `json:"m122_activated"`
	M122TrialTimes  int        `json:"m122_trial_times"` // 剩余试用次数（0 = 已用尽）
	LastCheckTime   time.Time  `json:"last_check_time"`
}

// TrialConsumeResult 试用次数消费结果（供前端决定 放行 / 引导激活）
type TrialConsumeResult struct {
	OK       bool          `json:"ok"`       // 是否允许本次使用
	Message  string        `json:"message"`  // 拒绝原因（服务端原文透传给用户）
	Overview *AuthOverview `json:"overview"` // 消费后的最新授权状态
}

// ServerResponse 服务端统一响应结构
type ServerResponse struct {
	Code    int                    `json:"code"`
	Message string                 `json:"message"`
	Msg     string                 `json:"msg"`
	Result  map[string]interface{} `json:"result"`
}
