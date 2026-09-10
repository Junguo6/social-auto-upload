package engine

import "fmt"

// Executor 是自动化发布引擎的外观门面 (Facade)，向外部暴露极简统一的执行接口
type Executor struct {
	runtime   *RuntimeManager
	builder   *TaskArgsBuilder
	tracker   *ProcessTracker
	account   *AccountManager
	risk      *RiskController
	scheduler *PublishScheduler
}

// NewExecutor 初始化引擎门面与底层各领域组件
func NewExecutor() (*Executor, error) {
	rt, err := NewRuntimeManager()
	if err != nil {
		return nil, err
	}

	builder := NewTaskArgsBuilder(rt.WorkDir)
	tracker := NewProcessTracker()
	account := NewAccountManager(rt, tracker)
	risk := NewRiskController(rt.WorkDir)
	scheduler := NewPublishScheduler(rt, builder, tracker, risk)

	return &Executor{
		runtime:   rt,
		builder:   builder,
		tracker:   tracker,
		account:   account,
		risk:      risk,
		scheduler: scheduler,
	}, nil
}

// GetAccountRiskStatus 获取指定账号的风控与健康度状态
func (e *Executor) GetAccountRiskStatus(platform, account string) RiskState {
	return e.risk.GetAccountRiskStatus(platform, account)
}

// ResumeAccount 人工解除指定账号的熔断状态
func (e *Executor) ResumeAccount(platform, account string) bool {
	return e.risk.ResumeAccount(platform, account)
}

// GetRiskOverview 获取系统中全部账号的风控概览
func (e *Executor) GetRiskOverview() []RiskState {
	return e.risk.GetRiskOverview()
}

// StopActiveTask 手动中止当前正在运行的全部任务 (单发或批处理)
func (e *Executor) StopActiveTask() bool {
	return e.tracker.StopActiveTask()
}

// StopSingleTask 手动中止单个特定账号的子任务
func (e *Executor) StopSingleTask(platform, account string) bool {
	return e.tracker.StopSingleTask(platform, account)
}

// StopTaskById 手动根据 TaskId 中止子任务
func (e *Executor) StopTaskById(taskId string) bool {
	return e.tracker.StopTaskById(taskId)
}

// SendBrowserInput 向正在运行的任务浏览器反向发送鼠标拖拽或按键指令
func (e *Executor) SendBrowserInput(taskId string, data []byte) error {
	return e.tracker.SendInput(taskId, data)
}

// DetectBrowserStatus 检查当前环境是否具备可运行的浏览器内核
func (e *Executor) DetectBrowserStatus() BrowserEnvironmentInfo {
	return e.runtime.DetectBrowserStatus()
}

// CheckAccount 检查账号登录凭证有效性
func (e *Executor) CheckAccount(platform, account string) (bool, string) {
	return e.account.CheckAccount(platform, account)
}

// LoginAccount 拉起界面/终端登录并自动解析账号昵称与 UID
func (e *Executor) LoginAccount(platform, account string, headed bool, onEvent func(evt EngineEvent)) (LoginResult, error) {
	return e.account.LoginAccount(platform, account, headed, onEvent)
}

// LoginAccountWithAppWindow 拉起原生 Chrome App 沉浸式真机视窗 (4K 原生画质与 0 延迟)
func (e *Executor) LoginAccountWithAppWindow(platform, account string, onEvent func(evt EngineEvent)) (LoginResult, error) {
	return e.account.LoginAccountWithAppWindow(platform, account, onEvent)
}

// LoginAccountWithScreencast 拉起后台无头登录并实时抽取 CDP 画面帧流供应用内画布交互
func (e *Executor) LoginAccountWithScreencast(platform, account string, onEvent func(evt EngineEvent)) (LoginResult, error) {
	return e.account.LoginAccountWithScreencast(platform, account, onEvent)
}

// ExecMatrixPublish 执行全景矩阵差异化并发发布
func (e *Executor) ExecMatrixPublish(param MatrixPublishParam, onEvent func(EngineEvent)) []AccountPublishResult {
	return e.scheduler.ExecMatrixPublish(param, onEvent)
}

// ExecPipelinePublish 执行多协程泳道任务工作流发布
func (e *Executor) ExecPipelinePublish(param PipelinePublishParam, onEvent func(EngineEvent)) []AccountPublishResult {
	return e.scheduler.ExecPipelinePublish(param, onEvent)
}

// ExecBatchPublish 执行普通矩阵批量发布
func (e *Executor) ExecBatchPublish(param BatchPublishParam, onEvent func(evt EngineEvent)) []AccountPublishResult {
	return e.scheduler.ExecBatchPublish(param, onEvent)
}

// ExecPublish 执行单账号发布任务
func (e *Executor) ExecPublish(param PublishParam, onEvent func(evt EngineEvent)) error {
	results := e.ExecBatchPublish(BatchPublishParam{
		Targets:            []TargetAccount{{Platform: param.Platform, Account: param.Account}},
		Concurrency:        1,
		Action:             param.Action,
		FilePath:           param.FilePath,
		Images:             param.Images,
		Title:              param.Title,
		Desc:               param.Desc,
		Tags:               param.Tags,
		Thumbnail:          param.Thumbnail,
		ThumbnailLandscape: param.ThumbnailLandscape,
		ThumbnailPortrait:  param.ThumbnailPortrait,
		Tid:                param.Tid,
		ShortTitle:         param.ShortTitle,
		Category:           param.Category,
		Draft:              param.Draft,
		Schedule:           param.Schedule,
		Declaration:        param.Declaration,
		Collection:         param.Collection,
		ProductLink:        param.ProductLink,
		ProductTitle:       param.ProductTitle,
		Visibility:         param.Visibility,
		Playlist:           param.Playlist,
		Bgm:                param.Bgm,
		Note:               param.Note,
		Notef:              param.Notef,
		Headless:           param.Headless,
	}, onEvent)

	if len(results) > 0 && !results[0].Success {
		return fmt.Errorf("%s", results[0].ErrorMsg)
	}
	return nil
}
