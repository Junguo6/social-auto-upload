package main

import (
	"context"
	"encoding/json"
	"fmt"
	godebug "runtime/debug"
	"sau_desktop/internal/auth"
	"sau_desktop/internal/engine"

	"github.com/wailsapp/wails/v2/pkg/runtime"
)

// App struct
type App struct {
	ctx      context.Context
	executor *engine.Executor
	authMgr  *auth.AuthManager
}

// PanicRecover 捕获 Wails 暴露方法内的 panic，避免整个应用崩溃。
// 对齐小映批量助手的做法：打印堆栈 + 参数，并上报服务端便于排查。
// 用法：在方法第一行 defer a.PanicRecover("方法名", map[string]interface{}{...})
func (a *App) PanicRecover(apiName string, params interface{}) {
	if r := recover(); r != nil {
		stackInfo := string(godebug.Stack())
		paramsJSON, _ := json.Marshal(params)
		errMsg := fmt.Sprintf("[%s] panic recovered: %v\nParams: %s\nStackTrace:\n%s",
			apiName, r, string(paramsJSON), stackInfo)
		fmt.Printf("❌ %s\n", errMsg)

		// 上报服务端（authMgr 可能未初始化，需判空）
		if a.authMgr != nil {
			a.authMgr.ReportError(errMsg)
		}
	}
}

// NewApp creates a new App application struct
func NewApp() *App {
	exec, err := engine.NewExecutor()
	if err != nil {
		fmt.Printf("警告: 引擎初始化异常: %v\n", err)
	}

	authManager, err := auth.NewManager()
	if err != nil {
		fmt.Printf("警告: 鉴权模块初始化异常: %v\n", err)
	}

	return &App{
		executor: exec,
		authMgr:  authManager,
	}
}

// startup is called when the app starts. The context is saved
// so we can call the runtime methods
func (a *App) startup(ctx context.Context) {
	a.ctx = ctx

	// 注册原生文件/文件夹拖拽回调（Wails v2.10+）：
	// 拖入窗口后拿到真实绝对路径，解析文件夹结构并通过事件推送给前端
	go runtime.OnFileDrop(ctx, func(x, y int, paths []string) {
		a.handleNativeFileDrop(paths)
	})
}

// GetAuthOverview 获取机器识别码与授权状态概览
func (a *App) GetAuthOverview() (*auth.AuthOverview, error) {
	defer a.PanicRecover("GetAuthOverview", nil)
	if a.authMgr == nil {
		return nil, fmt.Errorf("鉴权服务未初始化")
	}
	return a.authMgr.RefreshOverview()
}

// ApplyActiveCode 提交激活码进行在线核销
func (a *App) ApplyActiveCode(code string) (*auth.AuthOverview, error) {
	defer a.PanicRecover("ApplyActiveCode", map[string]interface{}{"code": code})
	if a.authMgr == nil {
		return nil, fmt.Errorf("鉴权服务未初始化")
	}
	return a.authMgr.ApplyActiveCode(code)
}

// GetDeviceID 获取设备机器识别码
func (a *App) GetDeviceID() string {
	defer a.PanicRecover("GetDeviceID", nil)
	if a.authMgr == nil {
		return ""
	}
	return a.authMgr.GetDeviceID()
}

// ConsumeTrial 消费一次试用配额（未授权用户执行发布前调用）
func (a *App) ConsumeTrial() *auth.TrialConsumeResult {
	defer a.PanicRecover("ConsumeTrial", nil)
	if a.authMgr == nil {
		return &auth.TrialConsumeResult{OK: false, Message: "鉴权服务未初始化"}
	}
	return a.authMgr.ConsumeTrial()
}

// GetOrderPackages 获取可购买的套餐列表（含价格）
func (a *App) GetOrderPackages() []auth.OrderPackage {
	defer a.PanicRecover("GetOrderPackages", nil)
	if a.authMgr == nil {
		return nil
	}
	return a.authMgr.OrderPackages()
}

// CreateOrder 创建开通订单，返回微信支付二维码链接
func (a *App) CreateOrder(packageType string) *auth.OrderCreateResult {
	defer a.PanicRecover("CreateOrder", map[string]interface{}{"packageType": packageType})
	if a.authMgr == nil {
		return &auth.OrderCreateResult{Success: false, Message: "鉴权服务未初始化"}
	}
	return a.authMgr.CreateOrder(packageType)
}

// QueryOrder 查询订单支付状态
func (a *App) QueryOrder(outTradeNo string) *auth.OrderQueryResult {
	defer a.PanicRecover("QueryOrder", map[string]interface{}{"outTradeNo": outTradeNo})
	if a.authMgr == nil {
		return &auth.OrderQueryResult{Success: false, TradeState: "NOTFOUND"}
	}
	return a.authMgr.QueryOrder(outTradeNo)
}

// CloseOrder 关闭待支付订单（用户取消支付时调用）
func (a *App) CloseOrder(outTradeNo string) *auth.OrderQueryResult {
	defer a.PanicRecover("CloseOrder", map[string]interface{}{"outTradeNo": outTradeNo})
	if a.authMgr == nil {
		return &auth.OrderQueryResult{Success: false, TradeState: "NOTFOUND"}
	}
	return a.authMgr.CloseOrder(outTradeNo)
}

// PublishMedia 单账号媒体发布接口
func (a *App) PublishMedia(param engine.PublishParam) (string, error) {
	defer a.PanicRecover("PublishMedia", map[string]interface{}{"param": param})
	if a.authMgr != nil {
		if err := a.authMgr.RequirePublishAuth(); err != nil {
			return "", err
		}
	}
	if a.executor == nil {
		return "", fmt.Errorf("引擎未正常加载")
	}

	err := a.executor.ExecPublish(param, func(evt engine.EngineEvent) {
		if a.ctx != nil {
			runtime.EventsEmit(a.ctx, "sau-log", evt)
		}
	})

	if err != nil {
		return "", err
	}
	return "发布成功", nil
}

// BatchPublishMedia 矩阵多账号高并发批量发布接口 (Go Goroutines 并发池调度)
func (a *App) BatchPublishMedia(param engine.BatchPublishParam) ([]engine.AccountPublishResult, error) {
	defer a.PanicRecover("BatchPublishMedia", map[string]interface{}{"param": param})
	if a.authMgr != nil {
		if err := a.authMgr.RequirePublishAuth(); err != nil {
			return nil, err
		}
	}

	if a.executor == nil {
		return nil, fmt.Errorf("引擎未正常加载")
	}

	results := a.executor.ExecBatchPublish(param, func(evt engine.EngineEvent) {
		if a.ctx != nil {
			runtime.EventsEmit(a.ctx, "sau-log", evt)
		}
	})

	return results, nil
}

// MatrixPublishMedia 全景矩阵差异化发布接口 (支持各平台/各账号独立定制参数与 Goroutines 并发调度)
func (a *App) MatrixPublishMedia(param engine.MatrixPublishParam) ([]engine.AccountPublishResult, error) {
	defer a.PanicRecover("MatrixPublishMedia", map[string]interface{}{"param": param})
	if a.authMgr != nil {
		if err := a.authMgr.RequirePublishAuth(); err != nil {
			return nil, err
		}
	}

	if a.executor == nil {
		return nil, fmt.Errorf("引擎未正常加载")
	}

	results := a.executor.ExecMatrixPublish(param, func(evt engine.EngineEvent) {
		if a.ctx != nil {
			if evt.Type == "screencast_frame" {
				runtime.EventsEmit(a.ctx, "sau-screencast", evt)
			} else {
				runtime.EventsEmit(a.ctx, "sau-log", evt)
			}
		}
	})

	return results, nil
}

// PipelinePublishMedia 多协程泳道任务工作流发布接口 (各线程通道并行，通道内卡片串行调度)
func (a *App) PipelinePublishMedia(param engine.PipelinePublishParam) ([]engine.AccountPublishResult, error) {
	defer a.PanicRecover("PipelinePublishMedia", map[string]interface{}{"param": param})
	if a.authMgr != nil {
		if err := a.authMgr.RequirePublishAuth(); err != nil {
			return nil, err
		}
	}

	if a.executor == nil {
		return nil, fmt.Errorf("引擎未正常加载")
	}

	results := a.executor.ExecPipelinePublish(param, func(evt engine.EngineEvent) {
		if a.ctx != nil {
			if evt.Type == "screencast_frame" {
				runtime.EventsEmit(a.ctx, "sau-screencast", evt)
			} else {
				runtime.EventsEmit(a.ctx, "sau-log", evt)
			}
		}
	})

	return results, nil
}

// StopActivePublish 手动中止当前正在运行的发布任务 (包括所有批量 Goroutines)
func (a *App) StopActivePublish() bool {
	defer a.PanicRecover("StopActivePublish", nil)
	if a.executor == nil {
		return false
	}
	return a.executor.StopActiveTask()
}

// StopSingleTask 手动中止单个特定账号的子任务 (不影响同一通道后续任务及其它通道)
func (a *App) StopSingleTask(platform, account string) bool {
	defer a.PanicRecover("StopSingleTask", map[string]interface{}{"platform": platform, "account": account})
	if a.executor == nil {
		return false
	}
	return a.executor.StopSingleTask(platform, account)
}

// StopTaskById 手动根据 TaskId 中止子任务 (不影响同一通道后续任务及其它通道)
func (a *App) StopTaskById(taskId string) bool {
	defer a.PanicRecover("StopTaskById", map[string]interface{}{"taskId": taskId})
	if a.executor == nil {
		return false
	}
	return a.executor.StopTaskById(taskId)
}

// GetAccountRiskStatus 查询账号实时风控与健康度状态
func (a *App) GetAccountRiskStatus(platform, account string) engine.RiskState {
	defer a.PanicRecover("GetAccountRiskStatus", map[string]interface{}{"platform": platform, "account": account})
	if a.executor == nil {
		return engine.RiskState{Platform: platform, Account: account}
	}
	return a.executor.GetAccountRiskStatus(platform, account)
}

// ResumeAccount 人工已核验处理，解除账号安全熔断状态
func (a *App) ResumeAccount(platform, account string) bool {
	defer a.PanicRecover("ResumeAccount", map[string]interface{}{"platform": platform, "account": account})
	if a.executor == nil {
		return false
	}
	return a.executor.ResumeAccount(platform, account)
}

// GetRiskOverview 获取系统中全部账号的风控概览列表
func (a *App) GetRiskOverview() []engine.RiskState {
	defer a.PanicRecover("GetRiskOverview", nil)
	if a.executor == nil {
		return nil
	}
	return a.executor.GetRiskOverview()
}

// DetectBrowserStatus 获取当前浏览器环境诊断状态 (是否已就绪、内核类型与路径)
func (a *App) DetectBrowserStatus() engine.BrowserEnvironmentInfo {
	defer a.PanicRecover("DetectBrowserStatus", nil)
	if a.executor == nil {
		return engine.BrowserEnvironmentInfo{IsReady: false, Summary: "底层自动化引擎未就绪"}
	}
	return a.executor.DetectBrowserStatus()
}

// CheckAccountStatus 校验账号 Cookie 状态
func (a *App) CheckAccountStatus(platform, account string) engine.AccountStatus {
	defer a.PanicRecover("CheckAccountStatus", map[string]interface{}{"platform": platform, "account": account})
	if a.executor == nil {
		return engine.AccountStatus{Platform: platform, Account: account, IsValid: false, Msg: "引擎初始化失败"}
	}
	isValid, msg := a.executor.CheckAccount(platform, account)
	avatar, nickname, finderUid := a.executor.GetAccountSavedMeta(platform, account)
	return engine.AccountStatus{
		Platform:  platform,
		Account:   account,
		IsValid:   isValid,
		Msg:       msg,
		Avatar:    avatar,
		Nickname:  nickname,
		FinderUid: finderUid,
	}
}

// DeleteAccountCredential 彻底删除本地磁盘上的指定账号凭证文件
func (a *App) DeleteAccountCredential(platform, account string) error {
	defer a.PanicRecover("DeleteAccountCredential", map[string]interface{}{"platform": platform, "account": account})
	if a.executor == nil {
		return fmt.Errorf("引擎未正常加载")
	}
	return a.executor.DeleteAccountCredential(platform, account)
}

// LoginAccount 拉起账号授权登录并返回账号信息
func (a *App) LoginAccount(platform, account string, headed bool) (engine.LoginResult, error) {
	defer a.PanicRecover("LoginAccount", map[string]interface{}{"platform": platform, "account": account, "headed": headed})
	if a.executor == nil {
		return engine.LoginResult{Success: false, Msg: "引擎未正常加载"}, fmt.Errorf("引擎未正常加载")
	}
	res, err := a.executor.LoginAccount(platform, account, headed, func(evt engine.EngineEvent) {
		if a.ctx != nil {
			if evt.Type == "login_success" {
				runtime.EventsEmit(a.ctx, "sau-login-success", evt)
			} else {
				runtime.EventsEmit(a.ctx, "sau-log", evt)
			}
		}
	})
	if err != nil {
		return res, err
	}
	return res, nil
}

// LoginAccountWithAppWindow 拉起独立的 Chrome App 沉浸式真机视窗 (4K 原生画质与 0 延迟，剥离地址栏)
func (a *App) LoginAccountWithAppWindow(platform, account string) (engine.LoginResult, error) {
	defer a.PanicRecover("LoginAccountWithAppWindow", map[string]interface{}{"platform": platform, "account": account})
	if a.executor == nil {
		return engine.LoginResult{Success: false, Msg: "引擎未正常加载"}, fmt.Errorf("引擎未正常加载")
	}
	res, err := a.executor.LoginAccountWithAppWindow(platform, account, func(evt engine.EngineEvent) {
		if a.ctx != nil {
			if evt.Type == "login_success" {
				runtime.EventsEmit(a.ctx, "sau-login-success", evt)
			} else {
				runtime.EventsEmit(a.ctx, "sau-log", evt)
			}
		}
	})
	if err != nil {
		return res, err
	}
	return res, nil
}

// LoginAccountWithScreencast 使用应用内实时 CDP 画布投屏拉起扫码登录 (无需外部独立弹窗)
func (a *App) LoginAccountWithScreencast(platform, account string) (engine.LoginResult, error) {
	defer a.PanicRecover("LoginAccountWithScreencast", map[string]interface{}{"platform": platform, "account": account})
	if a.executor == nil {
		return engine.LoginResult{Success: false, Msg: "引擎未正常加载"}, fmt.Errorf("引擎未正常加载")
	}
	res, err := a.executor.LoginAccountWithScreencast(platform, account, func(evt engine.EngineEvent) {
		if a.ctx != nil {
			if evt.Type == "screencast_frame" {
				runtime.EventsEmit(a.ctx, "sau-screencast", evt)
			} else if evt.Type == "login_success" {
				runtime.EventsEmit(a.ctx, "sau-login-success", evt)
			} else {
				runtime.EventsEmit(a.ctx, "sau-log", evt)
			}
		}
	})
	if err != nil {
		return res, err
	}
	return res, nil
}

// SendBrowserInput 向正在运行的任务浏览器反向发送鼠标拖拽或键盘交互指令
func (a *App) SendBrowserInput(taskId string, action string, inputType string, x, y int, button string, deltaX, deltaY int, key, text string) error {
	defer a.PanicRecover("SendBrowserInput", map[string]interface{}{"taskId": taskId, "action": action})
	if a.executor == nil {
		return fmt.Errorf("引擎未正常加载")
	}
	cmdMap := map[string]interface{}{
		"action": action,
	}
	if action == "mouse" {
		cmdMap["type"] = inputType
		cmdMap["x"] = x
		cmdMap["y"] = y
		cmdMap["button"] = button
		if inputType == "mouseWheel" {
			cmdMap["deltaX"] = deltaX
			cmdMap["deltaY"] = deltaY
		}
	} else if action == "key" {
		cmdMap["type"] = inputType
		cmdMap["key"] = key
		cmdMap["text"] = text
	}
	data, _ := json.Marshal(cmdMap)
	return a.executor.SendBrowserInput(taskId, data)
}

// SelectLocalFile 打开本地原生文件选择对话框
func (a *App) SelectLocalFile(title string, filterPatterns []string) (string, error) {
	defer a.PanicRecover("SelectLocalFile", map[string]interface{}{"title": title})
	filters := []runtime.FileFilter{}
	if len(filterPatterns) > 0 {
		filters = append(filters, runtime.FileFilter{
			DisplayName: "媒体文件",
			Pattern:     filterPatterns[0],
		})
	}
	filePath, err := runtime.OpenFileDialog(a.ctx, runtime.OpenDialogOptions{
		Title:   title,
		Filters: filters,
	})
	if err != nil {
		return "", err
	}
	return filePath, nil
}

// SelectLocalFiles 打开本地原生文件多选对话框 (支持按住 Ctrl/Cmd 批量多选视频或素材)
func (a *App) SelectLocalFiles(title string, filterPatterns []string) ([]string, error) {
	defer a.PanicRecover("SelectLocalFiles", map[string]interface{}{"title": title})
	filters := []runtime.FileFilter{}
	if len(filterPatterns) > 0 {
		filters = append(filters, runtime.FileFilter{
			DisplayName: "媒体文件",
			Pattern:     filterPatterns[0],
		})
	}
	filePaths, err := runtime.OpenMultipleFilesDialog(a.ctx, runtime.OpenDialogOptions{
		Title:   title,
		Filters: filters,
	})
	if err != nil {
		return nil, err
	}
	return filePaths, nil
}

// SelectLocalFolder 打开原生文件夹选择对话框，调用 ScanFolderStructure 进行结构扫描，
// 返回完整的扫描结果（含 valid/message/warnings），前端可据此判断是否合规。
func (a *App) SelectLocalFolder(title string) (*FolderScanResult, error) {
	defer a.PanicRecover("SelectLocalFolder", map[string]interface{}{"title": title})
	folderPath, err := runtime.OpenDirectoryDialog(a.ctx, runtime.OpenDialogOptions{
		Title: title,
	})
	if err != nil {
		return nil, err
	}
	if folderPath == "" {
		return &FolderScanResult{Root: "", Valid: true, Message: "未选择文件夹", Items: []ScannedMediaItem{}}, nil
	}

	res, scanErr := ScanFolderStructure(folderPath)
	if scanErr != nil {
		return nil, scanErr
	}
	return res, nil
}

