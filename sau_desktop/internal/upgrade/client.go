package upgrade

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"
)

const (
	ServerHost   = "https://xyrun.cn"
	ToolIDInt    = 4 // 分发助手数字 ID
	ToolIDString = "4"
)

// Client 版本检查与升级包下载 HTTP 客户端
type Client struct {
	httpClient *http.Client
	host       string
}

// NewClient 创建升级客户端
func NewClient(host ...string) *Client {
	h := ServerHost
	if len(host) > 0 && strings.TrimSpace(host[0]) != "" {
		h = strings.TrimRight(host[0], "/")
	}
	return &Client{
		httpClient: &http.Client{
			Timeout: 15 * time.Second,
		},
		host: h,
	}
}

// parseBoolField 将服务端可能返回的 int / string / bool 兼容转换为 bool
func parseBoolField(val interface{}) bool {
	if val == nil {
		return false
	}
	switch v := val.(type) {
	case bool:
		return v
	case float64:
		return int(v) == 1
	case int:
		return v == 1
	case string:
		v = strings.TrimSpace(v)
		if v == "1" || strings.EqualFold(v, "true") {
			return true
		}
		if n, err := strconv.Atoi(v); err == nil {
			return n == 1
		}
	}
	return false
}

// toStringField 将服务端字段转为 string
func toStringField(val interface{}) string {
	if val == nil {
		return ""
	}
	switch v := val.(type) {
	case string:
		return v
	case float64:
		return strconv.Itoa(int(v))
	case int:
		return strconv.Itoa(v)
	default:
		return fmt.Sprintf("%v", v)
	}
}

// CheckUpdate 请求服务端检测最新版本并比对
func (c *Client) CheckUpdate(currentVersion string) (*CheckUpdateResult, error) {
	apiURL := c.host + "/jym/version"
	params := url.Values{}
	params.Set("tool_id", ToolIDString)

	reqURL := apiURL + "?" + params.Encode()
	req, err := http.NewRequest(http.MethodGet, reqURL, nil)
	if err != nil {
		return &CheckUpdateResult{
			HasUpdate:      false,
			CurrentVersion: currentVersion,
			Message:        fmt.Sprintf("创建请求失败: %v", err),
			CheckTime:      time.Now(),
		}, err
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return &CheckUpdateResult{
			HasUpdate:      false,
			CurrentVersion: currentVersion,
			Message:        fmt.Sprintf("网络请求失败: %v", err),
			CheckTime:      time.Now(),
		}, nil // 不阻塞正常流程
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return &CheckUpdateResult{
			HasUpdate:      false,
			CurrentVersion: currentVersion,
			Message:        fmt.Sprintf("版本服务响应异常 (HTTP %d)", resp.StatusCode),
			CheckTime:      time.Now(),
		}, nil
	}

	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return &CheckUpdateResult{
			HasUpdate:      false,
			CurrentVersion: currentVersion,
			Message:        fmt.Sprintf("读取响应失败: %v", err),
			CheckTime:      time.Now(),
		}, nil
	}

	var raw RawVersionResponse
	if err := json.Unmarshal(bodyBytes, &raw); err != nil {
		return &CheckUpdateResult{
			HasUpdate:      false,
			CurrentVersion: currentVersion,
			Message:        fmt.Sprintf("解析版本数据失败: %v", err),
			CheckTime:      time.Now(),
		}, nil
	}

	// 尚未配置版本记录或服务端返回 null
	if raw.Result == nil || strings.TrimSpace(raw.Result.Version) == "" {
		return &CheckUpdateResult{
			HasUpdate:      false,
			CurrentVersion: currentVersion,
			LatestVersion:  currentVersion,
			Message:        "当前已是最新版本",
			CheckTime:      time.Now(),
		}, nil
	}

	item := raw.Result
	vInfo := &VersionInfo{
		ID:         toStringField(item.ID),
		ToolID:     toStringField(item.ToolID),
		Version:    CleanVersion(item.Version),
		Desc:       item.Desc,
		Brief:      item.Brief,
		MD5:        toStringField(item.MD5),
		IsPopUp:    parseBoolField(item.IsPopUp),
		IsOfficial: parseBoolField(item.IsOfficial),
		IsForced:   parseBoolField(item.IsForced),
		CreatedAt:  item.CreatedAt,
		UpdatedAt:  item.UpdatedAt,
	}

	// 仅正式版允许推送升级
	if !vInfo.IsOfficial {
		return &CheckUpdateResult{
			HasUpdate:      false,
			CurrentVersion: currentVersion,
			LatestVersion:  vInfo.Version,
			VersionInfo:    vInfo,
			Message:        "最新版本为非正式版，暂不提示升级",
			CheckTime:      time.Now(),
		}, nil
	}

	// 严格版本比对
	hasUpdate := CompareVersion(vInfo.Version, currentVersion) > 0

	msg := "当前已是最新版本"
	if hasUpdate {
		msg = fmt.Sprintf("发现新版本 v%s", vInfo.Version)
	}

	return &CheckUpdateResult{
		HasUpdate:      hasUpdate,
		CurrentVersion: currentVersion,
		LatestVersion:  vInfo.Version,
		VersionInfo:    vInfo,
		Message:        msg,
		CheckTime:      time.Now(),
	}, nil
}
