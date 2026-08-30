package auth

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"runtime"
	"strconv"
	"strings"
	"time"
)

const (
	ServerHost        = "https://xyrun.cn"
	ToolIdentifier    = "zidongfabu"
	MainModuleID      = 122
	MainFunctionID    = 81
	CurrentAppVersion = "1.2.0"
)

// Client 小映鉴权服务器 HTTP 客户端
type Client struct {
	httpClient *http.Client
}

func NewClient() *Client {
	return &Client{
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

// FetchOverview 请求 /jym/overview 接口，查询或注册设备并获取授权信息
func (c *Client) FetchOverview(identity *DeviceIdentity, activeCode string) (*AuthOverview, error) {
	apiURL := ServerHost + "/jym/overview"
	params := url.Values{}
	params.Add("system", runtime.GOOS)
	params.Add("new_sn", identity.NewSN)
	params.Add("sn", identity.NewSN)
	params.Add("tool_id", ToolIdentifier)
	params.Add("version", CurrentAppVersion)
	params.Add("agent_id", "0")
	params.Add("machine_id", identity.MachineID)
	if activeCode != "" {
		params.Add("code", activeCode)
	}

	req, err := http.NewRequest(http.MethodGet, apiURL+"?"+params.Encode(), nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("连接鉴权服务器失败: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("读取服务器响应失败: %w", err)
	}

	var sResp ServerResponse
	if err := json.Unmarshal(body, &sResp); err != nil {
		return nil, fmt.Errorf("解析服务器数据异常: %w", err)
	}

	if sResp.Code != 200 {
		errMsg := sResp.Message
		if errMsg == "" {
			errMsg = sResp.Msg
		}
		return nil, fmt.Errorf("服务器响应错误 (code %d): %s", sResp.Code, errMsg)
	}

	res := sResp.Result
	if res == nil {
		res = make(map[string]interface{})
	}

	overview := &AuthOverview{
		NewSN:         identity.NewSN,
		MachineID:     identity.MachineID,
		Version:       CurrentAppVersion,
		LastCheckTime: time.Now(),
	}

	if uid, ok := res["id"]; ok {
		overview.UserId = fmt.Sprintf("%v", uid)
	} else if uid, ok := res["user_id"]; ok {
		overview.UserId = fmt.Sprintf("%v", uid)
	}

	// 解析模块 122 授权状态
	if val, ok := res["m122_activated"]; ok {
		overview.M122Activated = toBool(val)
	}
	if val, ok := res["m100_activated"]; ok {
		overview.M100Activated = toBool(val)
	}

	if dl, ok := res["m122_deadline"]; ok {
		overview.Deadline = fmt.Sprintf("%v", dl)
	}
	if day, ok := res["m122_day"]; ok {
		overview.DaysRemaining = toInt(day)
	}

	// 综合判断是否激活且有效
	overview.IsActivated = overview.M100Activated || overview.M122Activated || overview.DaysRemaining > 0
	overview.IsExpired = overview.IsActivated && overview.DaysRemaining <= 0 && overview.Deadline != ""

	// 解析公告与帮助
	if notice, ok := res["announcement"]; ok && notice != nil {
		overview.Announcement = fmt.Sprintf("%v", notice)
	}
	if help, ok := res["need_help"]; ok && help != nil {
		overview.HelpUrl = fmt.Sprintf("%v", help)
	}

	return overview, nil
}

// ApplyActiveCode 请求 /jym/active 接口，提交激活码进行核销
func (c *Client) ApplyActiveCode(identity *DeviceIdentity, code, userId string) (*AuthOverview, error) {
	cleanCode := strings.TrimSpace(code)
	if cleanCode == "" {
		return nil, fmt.Errorf("激活码不能为空")
	}

	apiURL := ServerHost + "/jym/active"
	params := url.Values{}
	params.Add("code", cleanCode)
	params.Add("uid", userId)
	params.Add("version", CurrentAppVersion)
	params.Add("tool_id", ToolIdentifier)
	params.Add("sn", identity.NewSN)
	params.Add("new_sn", identity.NewSN)

	req, err := http.NewRequest(http.MethodGet, apiURL+"?"+params.Encode(), nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("连接激活服务器失败: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("读取响应失败: %w", err)
	}

	var rawRet map[string]interface{}
	if err := json.Unmarshal(body, &rawRet); err != nil {
		return nil, fmt.Errorf("解析服务器响应数据异常: %w", err)
	}

	// 核心业务校验：小映服务端业务失败时 result 恒为 null，错误信息在 message 字段
	if rawRet["result"] == nil {
		errMsg, _ := rawRet["message"].(string)
		if errMsg == "" {
			errMsg, _ = rawRet["msg"].(string)
		}
		if errMsg == "" {
			errMsg = "激活失败：激活码不存在、已过期或已被使用"
		}
		return nil, fmt.Errorf("%s", errMsg)
	}

	// 激活接口成功后，拉取一次最新的 Overview 刷新状态
	newOverview, err := c.FetchOverview(identity, cleanCode)
	if err != nil {
		return nil, err
	}

	if !newOverview.IsActivated {
		return nil, fmt.Errorf("激活码已核销，但未获取到自动发布授权，请联系管理员")
	}

	return newOverview, nil
}

// IncTrialTimes 请求 /jym/inc-trail-times 接口，扣减试用次数
func (c *Client) IncTrialTimes(userId string, functionId int) error {
	apiURL := ServerHost + "/jym/inc-trail-times"
	params := url.Values{}
	params.Add("id", userId)
	params.Add("function_id", strconv.Itoa(functionId))
	params.Add("version", CurrentAppVersion)

	req, err := http.NewRequest(http.MethodGet, apiURL+"?"+params.Encode(), nil)
	if err != nil {
		return err
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	return nil
}

// FeedbackError 上报错误日志到服务器
func (c *Client) FeedbackError(newSN, errMsg, level string) {
	apiURL := ServerHost + "/jym/feedback/error"
	form := url.Values{}
	form.Add("series_no", newSN)
	form.Add("error_msg", errMsg)
	form.Add("error_level", level)
	form.Add("version", CurrentAppVersion)

	go func() {
		_, _ = c.httpClient.PostForm(apiURL, form)
	}()
}

func toBool(v interface{}) bool {
	switch val := v.(type) {
	case bool:
		return val
	case float64:
		return val > 0
	case int:
		return val > 0
	case string:
		return val == "1" || strings.ToLower(val) == "true"
	}
	return false
}

func toInt(v interface{}) int {
	switch val := v.(type) {
	case int:
		return val
	case float64:
		return int(val)
	case string:
		i, _ := strconv.Atoi(val)
		return i
	}
	return 0
}
