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
	NewSN             string    `json:"new_sn"`
	MachineID         string    `json:"machine_id"`
	IsActivated       bool      `json:"is_activated"`
	IsExpired         bool      `json:"is_expired"`
	DaysRemaining     int       `json:"days_remaining"`
	Deadline          string    `json:"deadline"`
	UserId            string    `json:"user_id"`
	Version           string    `json:"version"`
	Announcement      string    `json:"announcement"`
	HelpUrl           string    `json:"help_url"`
	AgentNotice       string    `json:"agent_notice"`
	AgentWebsite      string    `json:"agent_website"`
	M100Activated     bool      `json:"m100_activated"`
	M122Activated     bool      `json:"m122_activated"`
	M122TrialTimes    int       `json:"m122_trial_times"` // 剩余试用次数（0 = 已用尽）
	// 各档套餐价格（单位：元；服务端以字符串返回，如 "9999.00"）
	M122MonthPrice     string `json:"m122_month_price"`
	M122SeasonPrice    string `json:"m122_season_price"`
	M122YearPrice      string `json:"m122_year_price"`
	M122PermanentPrice string `json:"m122_permanent_price"`
	LastCheckTime      time.Time `json:"last_check_time"`
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

// OrderCreateResult 下单结果（code_url 供前端生成微信支付二维码）
type OrderCreateResult struct {
	Success    bool   `json:"success"`
	OutTradeNo string `json:"out_trade_no"`
	CodeURL    string `json:"code_url"`
	Message    string `json:"message"`
}

// OrderQueryResult 订单支付状态
// TradeState 取值：SUCCESS(已支付) / NOTFOUND / NOTPAY / CLOSED ...
type OrderQueryResult struct {
	Success        bool   `json:"success"`
	TradeState     string `json:"trade_state"`
	TradeStateDesc string `json:"trade_state_desc"`
}

// OrderPackage 套餐档位（供前端展示与下单）
type OrderPackage struct {
	PackageType string  `json:"package_type"` // monthly / seasonal / yearly / permanent
	Label       string  `json:"label"`        // 月度 / 季度 / 年度 / 永久
	PriceYuan   float64 `json:"price_yuan"`
	AmountCent  int     `json:"amount_cent"`
	Purchasable bool    `json:"purchasable"` // 价格 <= 0 时不可购买（服务端也会拒）
}
