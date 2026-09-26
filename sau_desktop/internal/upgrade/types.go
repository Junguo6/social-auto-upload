package upgrade

import "time"

// VersionInfo 服务端返回的最新版本信息
type VersionInfo struct {
	ID         string `json:"id,omitempty"`
	ToolID     string `json:"tool_id,omitempty"`
	Version    string `json:"version"`
	Desc       string `json:"desc"`
	Brief      string `json:"brief"`
	IsPopUp    bool   `json:"is_pop_up"`
	IsOfficial bool   `json:"is_official"`
	IsForced   bool   `json:"is_forced"`
	CreatedAt  string `json:"created_at"`
	UpdatedAt  string `json:"updated_at,omitempty"`
}

// CheckUpdateResult 客户端检测更新结果
type CheckUpdateResult struct {
	HasUpdate      bool         `json:"has_update"`
	CurrentVersion string       `json:"current_version"`
	LatestVersion  string       `json:"latest_version"`
	VersionInfo    *VersionInfo `json:"version_info"`
	Message        string       `json:"message"`
	CheckTime      time.Time    `json:"check_time"`
}

// DownloadProgress 下载进度信息
type DownloadProgress struct {
	Percentage   int     `json:"percentage"`
	Downloaded   int64   `json:"downloaded"`
	Total        int64   `json:"total"`
	DownloadedMB float64 `json:"downloaded_mb"`
	TotalMB      float64 `json:"total_mb"`
	Status       string  `json:"status"` // "idle", "downloading", "completed", "error"
	Message      string  `json:"message,omitempty"`
	Error        string  `json:"error,omitempty"`
}

// RawVersionResponse 服务端原始返回结构
type RawVersionResponse struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Result  *RawVersionItem `json:"result"`
}

// RawVersionItem 服务端原始版本字段（兼容字符串和整型数值）
type RawVersionItem struct {
	ID         interface{} `json:"id"`
	ToolID     interface{} `json:"tool_id"`
	Version    string      `json:"version"`
	Desc       string      `json:"desc"`
	Brief      string      `json:"brief"`
	IsPopUp    interface{} `json:"is_pop_up"`
	IsOfficial interface{} `json:"is_official"`
	IsForced   interface{} `json:"is_forced"`
	CreatedAt  string      `json:"created_at"`
	UpdatedAt  string      `json:"updated_at"`
}
