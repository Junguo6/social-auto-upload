package engine

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

// RiskCode 风险信号代码常量
const (
	RiskCodeNone            = ""
	RiskCodeCaptcha         = "captcha"          // 触发人机验证/滑块
	RiskCodeLoginExpired    = "login_expired"    // 登录过期/Cookie失效
	RiskCodeRateLimited     = "rate_limited"     // 平台频率限制/操作过于频繁
	RiskCodeContentRejected = "content_rejected" // 内容违规/审核拒绝
	RiskCodeDuplicate       = "duplicate"        // 24小时内同账号重复发布相同内容
	RiskCodeQuotaExceeded   = "quota_exceeded"   // 超过每日/小时发布配额
)

// RiskState 账号运行健康度与风险状态模型
type RiskState struct {
	Platform            string    `json:"platform"`
	Account             string    `json:"account"`
	LastStartedAt       time.Time `json:"lastStartedAt"`
	LastFinishedAt      time.Time `json:"lastFinishedAt"`
	HourlyCount         int       `json:"hourlyCount"`
	DailyCount          int       `json:"dailyCount"`
	LastCountReset      time.Time `json:"lastCountReset"`
	ConsecutiveFailures int       `json:"consecutiveFailures"`
	CooldownUntil       time.Time `json:"cooldownUntil"`
	LastRiskCode        string    `json:"lastRiskCode"`
	Paused              bool      `json:"paused"`
	PauseReason         string    `json:"pauseReason"`
}

// PreflightResult 发布前准入安全检查结果
type PreflightResult struct {
	Allowed     bool   `json:"allowed"`
	RiskCode    string `json:"riskCode,omitempty"`
	Reason      string `json:"reason,omitempty"`
	WaitSeconds int    `json:"waitSeconds,omitempty"`
}

// riskPersistData 磁盘持久化封装
type riskPersistData struct {
	States       map[string]*RiskState `json:"states"`
	Fingerprints map[string]int64      `json:"fingerprints"` // key: platform:account:fingerprint -> unix
}

// RiskController 全局风险控制与两级锁引擎 (系统级单例)
type RiskController struct {
	workDir             string
	persistPath         string
	states              map[string]*RiskState  // key: platform:account
	fingerprints        map[string]int64      // key: platform:account:fingerprint -> timestamp
	platformLocks       map[string]*sync.Mutex // 平台级全局互斥锁
	accountLocks        map[string]*sync.Mutex // 账号级全局互斥锁
	platMu              sync.Mutex
	accMu               sync.Mutex
	stateMu             sync.RWMutex
	maxDailyPerAccount  int
	maxHourlyPerAccount int
}

// NewRiskController 初始化全局风控引擎并从磁盘恢复状态
func NewRiskController(workDir string) *RiskController {
	dataDir := filepath.Join(workDir, "data")
	_ = os.MkdirAll(dataDir, 0755)
	persistPath := filepath.Join(dataDir, "risk_state.json")

	rc := &RiskController{
		workDir:             workDir,
		persistPath:         persistPath,
		states:              make(map[string]*RiskState),
		fingerprints:        make(map[string]int64),
		platformLocks:       make(map[string]*sync.Mutex),
		accountLocks:        make(map[string]*sync.Mutex),
		maxDailyPerAccount:  20, // 默认单账号单日最大 20 次安全上限
		maxHourlyPerAccount: 5,  // 默认单账号单小时最大 5 次安全上限
	}

	rc.loadFromDisk()
	return rc
}

// getAccountKey 生成账号全局唯一检索 Key
func (rc *RiskController) getAccountKey(platform, account string) string {
	return fmt.Sprintf("%s:%s", strings.TrimSpace(platform), strings.TrimSpace(account))
}

// GetOrCreateState 获取或创建账号风控状态对象
func (rc *RiskController) GetOrCreateState(platform, account string) *RiskState {
	key := rc.getAccountKey(platform, account)
	rc.stateMu.Lock()
	defer rc.stateMu.Unlock()

	st, ok := rc.states[key]
	if !ok {
		st = &RiskState{
			Platform:       platform,
			Account:        account,
			LastCountReset: time.Now(),
		}
		rc.states[key] = st
	}

	// 检查计数器每日/每小时重置
	now := time.Now()
	if now.Day() != st.LastCountReset.Day() || now.Month() != st.LastCountReset.Month() {
		st.DailyCount = 0
		st.HourlyCount = 0
		st.LastCountReset = now
	} else if now.Hour() != st.LastCountReset.Hour() {
		st.HourlyCount = 0
		st.LastCountReset = now
	}

	return st
}

// ComputeContentFingerprint 计算内容指纹 Hash (防同一账号重复搬运/误触限流)
func (rc *RiskController) ComputeContentFingerprint(task AccountPublishTask) string {
	raw := fmt.Sprintf("%s|%s|%s|%s|%s|%s",
		task.Platform,
		task.Account,
		filepath.Clean(task.FilePath),
		strings.TrimSpace(task.Title),
		strings.TrimSpace(task.Desc),
		strings.TrimSpace(task.Tags),
	)
	h := sha256.Sum256([]byte(raw))
	return hex.EncodeToString(h[:])
}

// PreflightCheck 任务准入严苛前置安全检查
func (rc *RiskController) PreflightCheck(task AccountPublishTask) PreflightResult {
	st := rc.GetOrCreateState(task.Platform, task.Account)

	rc.stateMu.RLock()
	defer rc.stateMu.RUnlock()

	// 1. 是否处于熔断暂停状态 (如触发滑块、Cookie 失效)
	if st.Paused {
		return PreflightResult{
			Allowed:  false,
			RiskCode: st.LastRiskCode,
			Reason:   fmt.Sprintf("账号已被安全熔断暂停: %s (请核验处理后在任务中心点击「恢复」)", st.PauseReason),
		}
	}

	// 2. 是否处于冷却倒计时中
	now := time.Now()
	if now.Before(st.CooldownUntil) {
		remaining := int(time.Until(st.CooldownUntil).Seconds())
		return PreflightResult{
			Allowed:     false,
			RiskCode:    RiskCodeRateLimited,
			Reason:      fmt.Sprintf("账号处于平台风控安全冷却保护中 (剩余 %d 秒)", remaining),
			WaitSeconds: remaining,
		}
	}

	// 3. 是否超出单日发布配额
	if rc.maxDailyPerAccount > 0 && st.DailyCount >= rc.maxDailyPerAccount {
		return PreflightResult{
			Allowed:  false,
			RiskCode: RiskCodeQuotaExceeded,
			Reason:   fmt.Sprintf("账号今日发布频次已达安全保护上限 (%d 次)，请明天再试", rc.maxDailyPerAccount),
		}
	}

	// 4. 24小时内内容指纹查重 (防止同一视频和文案手滑重复发往同一账号)
	fp := rc.ComputeContentFingerprint(task)
	fpKey := fmt.Sprintf("%s:%s", rc.getAccountKey(task.Platform, task.Account), fp)
	if lastTime, exists := rc.fingerprints[fpKey]; exists {
		if now.Unix()-lastTime < 24*3600 {
			hoursAgo := (now.Unix() - lastTime) / 3600
			return PreflightResult{
				Allowed:  false,
				RiskCode: RiskCodeDuplicate,
				Reason:   fmt.Sprintf("该账号在 %d 小时前已发布过完全相同的内容，已智能拦截防重以保护账号权重", hoursAgo),
			}
		}
	}

	return PreflightResult{Allowed: true}
}

// getPlatformMutex 获取指定平台的全局互斥锁
func (rc *RiskController) getPlatformMutex(platform string) *sync.Mutex {
	rc.platMu.Lock()
	defer rc.platMu.Unlock()

	lk, ok := rc.platformLocks[platform]
	if !ok {
		lk = &sync.Mutex{}
		rc.platformLocks[platform] = lk
	}
	return lk
}

// getAccountMutex 获取指定账号的全局互斥锁
func (rc *RiskController) getAccountMutex(platform, account string) *sync.Mutex {
	rc.accMu.Lock()
	defer rc.accMu.Unlock()

	key := rc.getAccountKey(platform, account)
	lk, ok := rc.accountLocks[key]
	if !ok {
		lk = &sync.Mutex{}
		rc.accountLocks[key] = lk
	}
	return lk
}

// AcquireDualLocks 获取两级全局排他锁：账号锁 + 平台锁
// 遵循严格的加锁顺序：先锁定账号，再锁定平台，确保同平台串行且同账号绝不并发
func (rc *RiskController) AcquireDualLocks(ctx context.Context, platform, account string) (func(), error) {
	accLock := rc.getAccountMutex(platform, account)
	platLock := rc.getPlatformMutex(platform)

	// 1. 加账号锁 (防同账号多任务同时跑)
	accLock.Lock()

	// 2. 加平台锁 (防同平台多账号在不同泳道同时调浏览器)
	platLock.Lock()

	unlock := func() {
		platLock.Unlock()
		accLock.Unlock()
	}

	if ctx.Err() != nil {
		unlock()
		return nil, ctx.Err()
	}

	return unlock, nil
}

// OnTaskStart 记录任务启动时刻
func (rc *RiskController) OnTaskStart(task AccountPublishTask) {
	st := rc.GetOrCreateState(task.Platform, task.Account)
	rc.stateMu.Lock()
	st.LastStartedAt = time.Now()
	rc.stateMu.Unlock()
	rc.saveToDisk()
}

// OnTaskSuccess 记录任务执行成功并更新健康指标
func (rc *RiskController) OnTaskSuccess(task AccountPublishTask) {
	st := rc.GetOrCreateState(task.Platform, task.Account)
	now := time.Now()

	rc.stateMu.Lock()
	st.LastFinishedAt = now
	st.ConsecutiveFailures = 0
	st.LastRiskCode = RiskCodeNone
	st.HourlyCount++
	st.DailyCount++

	// 记录内容指纹
	fp := rc.ComputeContentFingerprint(task)
	fpKey := fmt.Sprintf("%s:%s", rc.getAccountKey(task.Platform, task.Account), fp)
	rc.fingerprints[fpKey] = now.Unix()
	rc.stateMu.Unlock()

	rc.saveToDisk()
}

// OnTaskError 智能分类风险信号并触发熔断降级
func (rc *RiskController) OnTaskError(task AccountPublishTask, errMsg string, logLines []string) (string, bool) {
	st := rc.GetOrCreateState(task.Platform, task.Account)
	now := time.Now()

	allText := errMsg + " " + strings.Join(logLines, " ")
	lowerText := strings.ToLower(allText)

	riskCode := RiskCodeNone
	paused := false
	pauseReason := ""

	// 智能识别平台返回的典型风控特征码
	if strings.Contains(allText, "验证码") || strings.Contains(allText, "人机验证") ||
		strings.Contains(allText, "滑块") || strings.Contains(allText, "安全验证") ||
		strings.Contains(lowerText, "captcha") || strings.Contains(lowerText, "verify") {
		riskCode = RiskCodeCaptcha
		paused = true
		pauseReason = "触发平台人机/滑块验证"
	} else if strings.Contains(allText, "登录已过期") || strings.Contains(allText, "登录失效") ||
		strings.Contains(allText, "Cookie已失效") || strings.Contains(allText, "请重新登录") ||
		strings.Contains(lowerText, "token expired") || strings.Contains(lowerText, "session expired") {
		riskCode = RiskCodeLoginExpired
		paused = true
		pauseReason = "登录凭证已失效，需重新扫码登录"
	} else if strings.Contains(allText, "过于频繁") || strings.Contains(allText, "频率过高") ||
		strings.Contains(allText, "访问受限") || strings.Contains(lowerText, "rate limit") ||
		strings.Contains(lowerText, "too many requests") {
		riskCode = RiskCodeRateLimited
		st.CooldownUntil = now.Add(30 * time.Minute) // 频率限制默认安全冷却 30 分钟
	} else if strings.Contains(allText, "违规") || strings.Contains(allText, "审核不通过") ||
		strings.Contains(allText, "封禁") || strings.Contains(lowerText, "rejected") {
		riskCode = RiskCodeContentRejected
		paused = true
		pauseReason = "内容触发平台违规审核拦截"
	}

	rc.stateMu.Lock()
	st.LastFinishedAt = now
	st.LastRiskCode = riskCode
	st.ConsecutiveFailures++

	if paused {
		st.Paused = true
		st.PauseReason = pauseReason
	} else if st.ConsecutiveFailures >= 3 && !st.Paused {
		// 连续失败 3 次，进入 10 分钟短时避震冷却
		st.CooldownUntil = now.Add(10 * time.Minute)
		st.LastRiskCode = RiskCodeRateLimited
	}
	rc.stateMu.Unlock()

	rc.saveToDisk()
	return riskCode, paused
}

// ResumeAccount 人工恢复解除熔断状态
func (rc *RiskController) ResumeAccount(platform, account string) bool {
	st := rc.GetOrCreateState(platform, account)
	rc.stateMu.Lock()
	st.Paused = false
	st.PauseReason = ""
	st.ConsecutiveFailures = 0
	st.CooldownUntil = time.Time{}
	st.LastRiskCode = RiskCodeNone
	rc.stateMu.Unlock()

	rc.saveToDisk()
	return true
}

// GetAccountRiskStatus 查询单个账号的实时风控健康度
func (rc *RiskController) GetAccountRiskStatus(platform, account string) RiskState {
	st := rc.GetOrCreateState(platform, account)
	rc.stateMu.RLock()
	defer rc.stateMu.RUnlock()
	return *st
}

// GetRiskOverview 获取系统中全部账号的风控全景概览
func (rc *RiskController) GetRiskOverview() []RiskState {
	rc.stateMu.RLock()
	defer rc.stateMu.RUnlock()

	var list []RiskState
	for _, st := range rc.states {
		list = append(list, *st)
	}
	return list
}

// loadFromDisk 从本地磁盘读取风控持久化状态
func (rc *RiskController) loadFromDisk() {
	if _, err := os.Stat(rc.persistPath); os.IsNotExist(err) {
		return
	}

	data, err := os.ReadFile(rc.persistPath)
	if err != nil {
		return
	}

	var pData riskPersistData
	if err := json.Unmarshal(data, &pData); err != nil {
		return
	}

	rc.stateMu.Lock()
	defer rc.stateMu.Unlock()

	if pData.States != nil {
		rc.states = pData.States
	}
	if pData.Fingerprints != nil {
		rc.fingerprints = pData.Fingerprints
	}
}

// saveToDisk 异步安全落盘风控持久化数据
func (rc *RiskController) saveToDisk() {
	rc.stateMu.RLock()
	pData := riskPersistData{
		States:       rc.states,
		Fingerprints: rc.fingerprints,
	}
	data, err := json.MarshalIndent(pData, "", "  ")
	rc.stateMu.RUnlock()

	if err != nil {
		return
	}

	_ = os.WriteFile(rc.persistPath, data, 0644)
}
