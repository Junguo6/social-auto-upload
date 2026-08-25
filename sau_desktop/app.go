package main

import (
	"context"
	"fmt"
	"sau_desktop/internal/engine"

	"github.com/wailsapp/wails/v2/pkg/runtime"
)

// App struct
type App struct {
	ctx      context.Context
	executor *engine.Executor
}

// NewApp creates a new App application struct
func NewApp() *App {
	exec, err := engine.NewExecutor()
	if err != nil {
		fmt.Printf("警告: 引擎初始化异常: %v\n", err)
	}
	return &App{
		executor: exec,
	}
}

// startup is called when the app starts. The context is saved
// so we can call the runtime methods
func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
}

// PublishMedia 单账号媒体发布接口
func (a *App) PublishMedia(param engine.PublishParam) (string, error) {
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

// StopActivePublish 手动中止当前正在运行的发布任务 (包括所有批量 Goroutines)
func (a *App) StopActivePublish() bool {
	if a.executor == nil {
		return false
	}
	return a.executor.StopActiveTask()
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

// LoginAccount 拉起账号授权登录
func (a *App) LoginAccount(platform, account string, headed bool) (string, error) {
	if a.executor == nil {
		return "", fmt.Errorf("引擎未正常加载")
	}
	err := a.executor.LoginAccount(platform, account, headed, func(evt engine.EngineEvent) {
		if a.ctx != nil {
			runtime.EventsEmit(a.ctx, "sau-log", evt)
		}
	})
	if err != nil {
		return "", err
	}
	return "登录成功", nil
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
