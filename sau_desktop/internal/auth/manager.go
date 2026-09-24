package auth

import (
	"fmt"
	"math"
	"strconv"
	"strings"
	"sync"
	"time"
)

type AuthManager struct {
	client         *Client
	identity       *DeviceIdentity
	cachedOverview *AuthOverview
	mu             sync.RWMutex
}

func NewManager() (*AuthManager, error) {
	identity, err := GetDeviceIdentity()
	if err != nil {
		return nil, fmt.Errorf("初始化设备识别码失败: %w", err)
	}

	client := NewClient()
	mgr := &AuthManager{
		client:   client,
		identity: identity,
		cachedOverview: &AuthOverview{
			NewSN:         identity.NewSN,
			MachineID:     identity.MachineID,
			Version:       CurrentAppVersion,
			IsActivated:   false,
			DaysRemaining: 0,
			LastCheckTime: time.Now(),
		},
	}

	// 启动时后台异步预取一次服务器 Overview
	go func() {
		_, _ = mgr.RefreshOverview()
	}()

	return mgr, nil
}

// GetDeviceID 获取设备识别码 (16位)
func (m *AuthManager) GetDeviceID() string {
	if m.identity != nil {
		return m.identity.NewSN
	}
	return ""
}

// GetOverview 获取鉴权概要信息 (如过期则自动刷新)
func (m *AuthManager) GetOverview() *AuthOverview {
	m.mu.RLock()
	cached := m.cachedOverview
	m.mu.RUnlock()

	// 若 5 分钟未刷新过，且已不是首次默认状态，在后台触发一次静默刷新
	if cached != nil && time.Since(cached.LastCheckTime) > 5*time.Minute {
		go func() {
			_, _ = m.RefreshOverview()
		}()
	}

	return cached
}

// RefreshOverview 强制向云端服务器请求最新状态
func (m *AuthManager) RefreshOverview() (*AuthOverview, error) {
	if m.identity == nil {
		return nil, fmt.Errorf("设备标识未初始化")
	}

	overview, err := m.client.FetchOverview(m.identity, "")
	if err != nil {
		// 网络异常时，保留本地已知状态，仅更新时间
		m.mu.Lock()
		if m.cachedOverview != nil {
			m.cachedOverview.LastCheckTime = time.Now()
		}
		m.mu.Unlock()
		return m.cachedOverview, err
	}

	m.mu.Lock()
	m.cachedOverview = overview
	m.mu.Unlock()

	return overview, nil
}

// ApplyActiveCode 提交激活码卡密进行在线核销
func (m *AuthManager) ApplyActiveCode(code string) (*AuthOverview, error) {
	if m.identity == nil {
		return nil, fmt.Errorf("设备标识未初始化")
	}

	m.mu.RLock()
	userId := ""
	if m.cachedOverview != nil {
		userId = m.cachedOverview.UserId
	}
	m.mu.RUnlock()

	newOverview, err := m.client.ApplyActiveCode(m.identity, code, userId)
	if err != nil {
		return nil, err
	}

	m.mu.Lock()
	m.cachedOverview = newOverview
	m.mu.Unlock()

	return newOverview, nil
}

// RequirePublishAuth 核心发布动作鉴权守卫拦截器
func (m *AuthManager) RequirePublishAuth() error {
	m.mu.RLock()
	overview := m.cachedOverview
	m.mu.RUnlock()

	if overview == nil {
		// 尝试同步刷新一次
		var err error
		overview, err = m.RefreshOverview()
		if err != nil {
			return fmt.Errorf("未能连接授权服务器，请检查网络连接: %w", err)
		}
	}

	// 检查全局套餐 m100 或自动发布主模块 m122
	if overview.M100Activated || overview.M122Activated || overview.DaysRemaining > 0 {
		return nil
	}

	return fmt.Errorf("当前软件尚未激活或授权已到期，请在软件界面右上角点击【激活】或将设备识别码 (%s) 发送给管理员开通", overview.NewSN)
}

// ConsumeTrial 消费一次试用配额。
// · 已授权 → 直接放行（不扣次）
// · 未授权 → 请求服务端扣次：成功放行，失败/次数用尽 → 拒绝并透传服务端原因
// · 网络异常 → 保守拒绝（不降级放行，避免断网绕过授权）
func (m *AuthManager) ConsumeTrial() *TrialConsumeResult {
	m.mu.RLock()
	overview := m.cachedOverview
	m.mu.RUnlock()

	// 已授权 → 直接放行（不扣次）
	if overview != nil &&
		(overview.M100Activated || overview.M122Activated || overview.DaysRemaining > 0) {
		return &TrialConsumeResult{OK: true, Overview: overview}
	}

	// 未取到 userId → 设备尚未注册
	userId := ""
	if overview != nil {
		userId = overview.UserId
	}
	if userId == "" {
		return &TrialConsumeResult{OK: false, Message: "设备尚未完成注册，请稍后重试"}
	}

	// 请求服务端扣次
	if err := m.client.IncTrialTimes(userId, TrialFunctionID); err != nil {
		return &TrialConsumeResult{OK: false, Message: err.Error()}
	}

	// 扣次成功后刷新一次授权状态，带回最新剩余次数
	if ov, err := m.RefreshOverview(); err == nil && ov != nil {
		return &TrialConsumeResult{OK: true, Overview: ov}
	}
	// 刷新失败时也放行（扣次已成功），用缓存状态兜底
	m.mu.RLock()
	cached := m.cachedOverview
	m.mu.RUnlock()
	return &TrialConsumeResult{OK: true, Overview: cached}
}

// ReportError 上报错误日志
func (m *AuthManager) ReportError(errMsg string) {
	if m.identity != nil {
		m.client.FeedbackError(m.identity.NewSN, errMsg, "error")
	}
}

// OrderPackages 返回各档套餐（价格来自 overview；服务端未配价时标记为不可购买）
func (m *AuthManager) OrderPackages() []OrderPackage {
	m.mu.RLock()
	ov := m.cachedOverview
	m.mu.RUnlock()

	if ov == nil {
		return nil
	}

	parse := func(s string) float64 {
		v, _ := strconv.ParseFloat(strings.TrimSpace(s), 64)
		return v
	}
	mk := func(ptype, label, priceStr string) OrderPackage {
		y := parse(priceStr)
		return OrderPackage{
			PackageType: ptype,
			Label:       label,
			PriceYuan:   y,
			AmountCent:  int(math.Round(y * 100)),
			Purchasable: y > 0,
		}
	}

	return []OrderPackage{
		mk("monthly", "月度", ov.M122MonthPrice),
		mk("seasonal", "季度", ov.M122SeasonPrice),
		mk("yearly", "年度", ov.M122YearPrice),
		mk("permanent", "永久", ov.M122PermanentPrice),
	}
}

// CreateOrder 按套餐类型下单（金额由本地按 overview 价格换算成"分"传给服务端）
func (m *AuthManager) CreateOrder(packageType string) *OrderCreateResult {
	m.mu.RLock()
	ov := m.cachedOverview
	m.mu.RUnlock()

	if ov == nil || ov.NewSN == "" {
		return &OrderCreateResult{Success: false, Message: "授权信息未就绪，请稍后重试"}
	}

	var target *OrderPackage
	for _, p := range m.OrderPackages() {
		if p.PackageType == packageType {
			cp := p
			target = &cp
			break
		}
	}
	if target == nil || !target.Purchasable {
		return &OrderCreateResult{Success: false, Message: "该套餐暂不可购买"}
	}

	res, err := m.client.CreateOrder(ov.NewSN, target.AmountCent, packageType)
	if err != nil {
		return &OrderCreateResult{Success: false, Message: err.Error()}
	}
	if res == nil {
		return &OrderCreateResult{Success: false, Message: "下单失败，请稍后重试"}
	}
	return res
}

// QueryOrder 查询支付状态；支付成功后顺带刷新一次授权状态
func (m *AuthManager) QueryOrder(outTradeNo string) *OrderQueryResult {
	m.mu.RLock()
	ov := m.cachedOverview
	m.mu.RUnlock()

	if ov == nil || ov.NewSN == "" {
		return &OrderQueryResult{Success: false, TradeState: "NOTFOUND", TradeStateDesc: "授权信息未就绪"}
	}

	res, err := m.client.QueryOrder(outTradeNo, ov.NewSN)
	if err != nil {
		return &OrderQueryResult{Success: false, TradeState: "ERROR", TradeStateDesc: err.Error()}
	}

	if res != nil && res.TradeState == "SUCCESS" {
		// 支付成功 → 刷新授权状态，让界面立刻显示已开通
		_, _ = m.RefreshOverview()
	}
	return res
}

// CloseOrder 关闭待支付订单（用户取消支付时调用）。
// 失败不抛错——对调用方来说只是"尽力关单"，不影响用户继续操作。
func (m *AuthManager) CloseOrder(outTradeNo string) *OrderQueryResult {
	m.mu.RLock()
	ov := m.cachedOverview
	m.mu.RUnlock()

	if ov == nil || ov.NewSN == "" || outTradeNo == "" {
		return &OrderQueryResult{Success: false, TradeState: "NOTFOUND", TradeStateDesc: "参数不完整"}
	}

	res, err := m.client.CloseOrder(outTradeNo, ov.NewSN)
	if err != nil {
		return &OrderQueryResult{Success: false, TradeState: "ERROR", TradeStateDesc: err.Error()}
	}
	return res
}
