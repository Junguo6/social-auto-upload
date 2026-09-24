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
	// TrialFunctionID 试用扣次用的 function id
	// 注意：服务端按 function 表查 module（jym_function.id=81 → module_id=122），
	// 传模块号 122 会返回「功能不存在」
	TrialFunctionID   = 81
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

	// 服务端只返回 m122_deadline（Ymd），不返回 m122_day，剩余天数需自行计算
	if dl, ok := res["m122_deadline"]; ok {
		overview.Deadline = fmt.Sprintf("%v", dl)
		if t, err := time.ParseInLocation("20060102", overview.Deadline, time.Local); err == nil {
			overview.DaysRemaining = int(time.Until(t).Hours() / 24)
			if overview.DaysRemaining < 0 {
				overview.DaysRemaining = 0
			}
		}
	}

	// 剩余试用次数（服务端返回 m122_trial_times；未返回时保持 0）
	if tt, ok := res["m122_trial_times"]; ok && tt != nil {
		switch v := tt.(type) {
		case float64:
			overview.M122TrialTimes = int(v)
		case string:
			if n, err := strconv.Atoi(v); err == nil {
				overview.M122TrialTimes = n
			}
		}
	}

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
// 注意：必须带 tool_id —— 服务端默认值是 "xiaoying"，不传会把本工具的试用扣次记到小映批量助手头上，
// 或者因按 xiaoying 查不到用户而静默失败（表现为试用次数永不递减 = 无限试用）。
func (c *Client) IncTrialTimes(userId string, functionId int) error {
	apiURL := ServerHost + "/jym/inc-trail-times"
	params := url.Values{}
	params.Add("id", userId)
	params.Add("function_id", strconv.Itoa(functionId))
	params.Add("version", CurrentAppVersion)
	params.Add("tool_id", ToolIdentifier)

	req, err := http.NewRequest(http.MethodGet, apiURL+"?"+params.Encode(), nil)
	if err != nil {
		return err
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("读取试用扣次响应失败: %w", err)
	}

	var sResp ServerResponse
	if err := json.Unmarshal(body, &sResp); err != nil {
		return fmt.Errorf("解析试用扣次响应异常: %w", err)
	}

	if sResp.Code != 200 {
		errMsg := sResp.Message
		if errMsg == "" {
			errMsg = sResp.Msg
		}
		return fmt.Errorf("%s", errMsg)
	}

	return nil
}

// CreateOrder 创建开通订单（微信 Native 支付），返回 code_url 供前端生成二维码。
// 金额由服务端按 module_id + package_type 校验，客户端传值必须与配置一致，否则返回「金额不匹配」。
func (c *Client) CreateOrder(newSn string, amountCent int, packageType string) (*OrderCreateResult, error) {
	apiURL := ServerHost + "/jym/create_order"
	form := url.Values{}
	form.Add("new_sn", newSn)
	form.Add("amount", strconv.Itoa(amountCent))
	form.Add("package_type", packageType)
	form.Add("module_id", strconv.Itoa(MainModuleID))
	form.Add("function_id", strconv.Itoa(MainFunctionID))
	form.Add("version", CurrentAppVersion)
	form.Add("tool_id", ToolIdentifier)
	form.Add("agent_id", "0")

	req, err := http.NewRequest(http.MethodPost, apiURL, strings.NewReader(form.Encode()))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("下单请求失败: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("读取下单响应失败: %w", err)
	}

	var result OrderCreateResult
	c.decodeOrderResult(body, &result)
	if !result.Success {
		if result.Message == "" {
			result.Message = "下单失败，请稍后重试"
		}
	}
	return &result, nil
}

// QueryOrder 查询订单支付状态（前端下单后轮询用）
func (c *Client) QueryOrder(outTradeNo, newSn string) (*OrderQueryResult, error) {
	apiURL := ServerHost + "/jym/query_order"
	params := url.Values{}
	params.Add("out_trade_no", outTradeNo)
	params.Add("new_sn", newSn)
	params.Add("tool_id", ToolIdentifier)

	req, err := http.NewRequest(http.MethodGet, apiURL+"?"+params.Encode(), nil)
	if err != nil {
		return nil, err
	}
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("查询订单失败: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("读取订单响应失败: %w", err)
	}

	var result OrderQueryResult
	c.decodeOrderResult(body, &result)
	return &result, nil
}

// decodeOrderResult 解析订单类接口响应。
// 服务端有两种返回形态：① 直接是业务对象 ② 包在 {code, message, result} 里 —— 都兼容。
func (c *Client) decodeOrderResult(body []byte, out interface{}) {
	if err := json.Unmarshal(body, out); err != nil {
		return
	}
	// 判断是否已经是业务对象：成功字段已解析出来就不用再解包
	probe := map[string]interface{}{}
	if json.Unmarshal(body, &probe) == nil {
		if _, ok := probe["out_trade_no"]; ok {
			return
		}
		if _, ok := probe["trade_state"]; ok {
			return
		}
	}
	var sResp ServerResponse
	if err := json.Unmarshal(body, &sResp); err == nil && sResp.Result != nil {
		if b, err := json.Marshal(sResp.Result); err == nil {
			_ = json.Unmarshal(b, &out)
		}
	}
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
