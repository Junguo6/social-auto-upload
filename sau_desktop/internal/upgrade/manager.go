package upgrade

import (
	"context"
	"fmt"
	"sync"
)

// UpgradeManager 升级管理器
type UpgradeManager struct {
	client         *Client
	downloader     *Downloader
	host           string
	currentVersion string
	getDeviceSN    func() string

	mu             sync.RWMutex
	lastCheck      *CheckUpdateResult
	isDownloading  bool
	cancelDownload context.CancelFunc
	downloadedZip  string
	latestProgress DownloadProgress
}

// NewManager 创建升级管理器实例
func NewManager(currentVersion string, getDeviceSN func() string, host ...string) *UpgradeManager {
	h := ServerHost
	if len(host) > 0 && host[0] != "" {
		h = host[0]
	}
	return &UpgradeManager{
		client:         NewClient(h),
		downloader:     NewDownloader(h),
		host:           h,
		currentVersion: currentVersion,
		getDeviceSN:    getDeviceSN,
	}
}

// CheckUpdate 检查更新
func (m *UpgradeManager) CheckUpdate() (*CheckUpdateResult, error) {
	res, err := m.client.CheckUpdate(m.currentVersion)
	if err == nil && res != nil {
		m.mu.Lock()
		m.lastCheck = res
		m.mu.Unlock()
	}
	return res, err
}

// GetLastCheck 获取最近一次检查结果
func (m *UpgradeManager) GetLastCheck() *CheckUpdateResult {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.lastCheck
}

// GetDownloadProgress 获取当前下载进度
func (m *UpgradeManager) GetDownloadProgress() DownloadProgress {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.latestProgress
}

// StartDownload 开始后台下载升级包
func (m *UpgradeManager) StartDownload(
	ctx context.Context,
	emitProgress func(progress DownloadProgress),
) (*DownloadProgress, error) {
	m.mu.Lock()
	if m.isDownloading {
		m.mu.Unlock()
		return &m.latestProgress, fmt.Errorf("正在下载升级包中，请勿重复发起")
	}

	targetVer := ""
	if m.lastCheck != nil && m.lastCheck.VersionInfo != nil {
		targetVer = m.lastCheck.VersionInfo.Version
	}
	if targetVer == "" {
		m.mu.Unlock()
		return nil, fmt.Errorf("未获取到待升级版本信息，请先检查更新")
	}

	downloadCtx, cancel := context.WithCancel(ctx)
	m.cancelDownload = cancel
	m.isDownloading = true
	m.downloadedZip = ""
	m.latestProgress = DownloadProgress{
		Percentage: 0,
		Status:     "downloading",
		Message:    "准备开始下载升级包...",
	}
	m.mu.Unlock()

	// 异步执行下载任务
	go func() {
		defer func() {
			m.mu.Lock()
			m.isDownloading = false
			m.mu.Unlock()
		}()

		zipPath, err := m.downloader.DownloadPackage(
			downloadCtx,
			targetVer,
			"",
			func(p DownloadProgress) {
				m.mu.Lock()
				m.latestProgress = p
				m.mu.Unlock()
				if emitProgress != nil {
					emitProgress(p)
				}
			},
		)

		if err != nil {
			errProg := DownloadProgress{
				Percentage: 0,
				Status:     "error",
				Error:      err.Error(),
				Message:    fmt.Sprintf("下载失败: %v", err),
			}
			m.mu.Lock()
			m.latestProgress = errProg
			m.mu.Unlock()
			if emitProgress != nil {
				emitProgress(errProg)
			}
			return
		}

		m.mu.Lock()
		m.downloadedZip = zipPath
		m.mu.Unlock()
	}()

	return &m.latestProgress, nil
}

// CancelDownload 取消当前正在进行的下载
func (m *UpgradeManager) CancelDownload() {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.cancelDownload != nil {
		m.cancelDownload()
		m.cancelDownload = nil
	}
	m.isDownloading = false
	m.latestProgress = DownloadProgress{
		Percentage: 0,
		Status:     "idle",
		Message:    "下载已取消",
	}
}

// ApplyUpdate 执行更新安装
func (m *UpgradeManager) ApplyUpdate() error {
	m.mu.RLock()
	zipPath := m.downloadedZip
	m.mu.RUnlock()

	if zipPath == "" {
		return fmt.Errorf("尚未完成升级包下载，无法执行安装")
	}

	sn := ""
	if m.getDeviceSN != nil {
		sn = m.getDeviceSN()
	}

	return ExecuteInstall(zipPath, m.currentVersion, sn, m.host)
}

// IsForcedBlock 检查当前版本是否被强制升级且不可使用
func (m *UpgradeManager) IsForcedBlock() bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	if m.lastCheck != nil && m.lastCheck.HasUpdate && m.lastCheck.VersionInfo != nil {
		return m.lastCheck.VersionInfo.IsForced
	}
	return false
}
