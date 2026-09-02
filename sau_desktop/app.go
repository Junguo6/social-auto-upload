package main

import (
	"context"
	"encoding/json"
	"fmt"
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
}

// GetAuthOverview 获取机器识别码与授权状态概览
func (a *App) GetAuthOverview() (*auth.AuthOverview, error) {
	if a.authMgr == nil {
		return nil, fmt.Errorf("鉴权服务未初始化")
	}
	return a.authMgr.RefreshOverview()
}

// ApplyActiveCode 提交激活码进行在线核销
func (a *App) ApplyActiveCode(code string) (*auth.AuthOverview, error) {
	if a.authMgr == nil {
		return nil, fmt.Errorf("鉴权服务未初始化")
	}
	return a.authMgr.ApplyActiveCode(code)
}

// GetDeviceID 获取设备机器识别码
func (a *App) GetDeviceID() string {
	if a.authMgr == nil {
		return ""
	}
	return a.authMgr.GetDeviceID()
}

// PublishMedia 单账号媒体发布接口
func (a *App) PublishMedia(param engine.PublishParam) (string, error) {
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
	if a.executor == nil {
		return false
	}
	return a.executor.StopActiveTask()
}

// StopSingleTask 手动中止单个特定账号的子任务 (不影响同一通道后续任务及其它通道)
func (a *App) StopSingleTask(platform, account string) bool {
	if a.executor == nil {
		return false
	}
	return a.executor.StopSingleTask(platform, account)
}

// StopTaskById 手动根据 TaskId 中止子任务 (不影响同一通道后续任务及其它通道)
func (a *App) StopTaskById(taskId string) bool {
	if a.executor == nil {
		return false
	}
	return a.executor.StopTaskById(taskId)
}

// GetAccountRiskStatus 查询账号实时风控与健康度状态
func (a *App) GetAccountRiskStatus(platform, account string) engine.RiskState {
	if a.executor == nil {
		return engine.RiskState{Platform: platform, Account: account}
	}
	return a.executor.GetAccountRiskStatus(platform, account)
}

// ResumeAccount 人工已核验处理，解除账号安全熔断状态
func (a *App) ResumeAccount(platform, account string) bool {
	if a.executor == nil {
		return false
	}
	return a.executor.ResumeAccount(platform, account)
}

// GetRiskOverview 获取系统中全部账号的风控概览列表
func (a *App) GetRiskOverview() []engine.RiskState {
	if a.executor == nil {
		return nil
	}
	return a.executor.GetRiskOverview()
}

// DetectBrowserStatus 获取当前浏览器环境诊断状态 (是否已就绪、内核类型与路径)
func (a *App) DetectBrowserStatus() engine.BrowserEnvironmentInfo {
	if a.executor == nil {
		return engine.BrowserEnvironmentInfo{IsReady: false, Summary: "底层自动化引擎未就绪"}
	}
	return a.executor.DetectBrowserStatus()
}

// CheckAccountStatus 校验账号 Cookie 状态
func (a *App) CheckAccountStatus(platform, account string) engine.AccountStatus {
	if a.executor == nil {
		return engine.AccountStatus{Platform: platform, Account: account, IsValid: false, Msg: "引擎初始化失败"}
	}
	isValid, msg := a.executor.CheckAccount(platform, account)
	return engine.AccountStatus{
		Platform: platform,
		Account:  account,
		IsValid:  isValid,
		Msg:      msg,
	}
}

// LoginAccount 拉起账号授权登录并返回账号信息
func (a *App) LoginAccount(platform, account string, headed bool) (engine.LoginResult, error) {
	if a.executor == nil {
		return engine.LoginResult{Success: false, Msg: "引擎未正常加载"}, fmt.Errorf("引擎未正常加载")
	}
	res, err := a.executor.LoginAccount(platform, account, headed, func(evt engine.EngineEvent) {
		if a.ctx != nil {
			runtime.EventsEmit(a.ctx, "sau-log", evt)
		}
	})
	if err != nil {
		return res, err
	}
	return res, nil
}

// LoginAccountWithScreencast 使用应用内实时 CDP 画布投屏拉起扫码登录 (无需外部独立弹窗)
func (a *App) LoginAccountWithScreencast(platform, account string) (engine.LoginResult, error) {
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

