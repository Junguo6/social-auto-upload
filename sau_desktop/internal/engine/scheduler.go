package engine

import (
	"bufio"
	"context"
	"fmt"
	"strings"
	"sync"
	"time"
)

// PublishScheduler 负责矩阵多账号高并发发布任务的编排、限流与执行监控
type PublishScheduler struct {
	runtime *RuntimeManager
	builder *TaskArgsBuilder
	tracker *ProcessTracker
}

func NewPublishScheduler(runtime *RuntimeManager, builder *TaskArgsBuilder, tracker *ProcessTracker) *PublishScheduler {
	return &PublishScheduler{
		runtime: runtime,
		builder: builder,
		tracker: tracker,
	}
}

// execSingleTask 抽取单个账号发布任务的核心执行逻辑
func (s *PublishScheduler) execSingleTask(ctx context.Context, task AccountPublishTask, laneTag string, onEvent func(EngineEvent)) AccountPublishResult {
	args := s.builder.BuildTaskArgs(task)
	cmd := s.runtime.BuildCommand(ctx, args...)

	taskKey := fmt.Sprintf("%s:%s", task.Platform, task.Account)
	s.tracker.RegisterTaskCmd(taskKey, cmd)
	if task.TaskId != "" {
		s.tracker.RegisterTaskCmd(task.TaskId, cmd)
	}
	defer func() {
		s.tracker.UnregisterTaskCmd(taskKey, cmd)
		if task.TaskId != "" {
			s.tracker.UnregisterTaskCmd(task.TaskId, cmd)
		}
	}()

	displayName := task.Nickname
	if displayName == "" {
		displayName = task.Account
	}
	tagPrefix := fmt.Sprintf("[%s:%s]", task.Platform, displayName)
	if laneTag != "" {
		tagPrefix = fmt.Sprintf("[%s][%s:%s]", laneTag, task.Platform, displayName)
	}

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return AccountPublishResult{
			TaskId:   task.TaskId,
			Platform: task.Platform,
			Account:  task.Account,
			Success:  false,
			ErrorMsg: fmt.Sprintf("创建输出管道失败: %v", err),
		}
	}
	cmd.Stderr = cmd.Stdout

	if err := cmd.Start(); err != nil {
		return AccountPublishResult{
			TaskId:   task.TaskId,
			Platform: task.Platform,
			Account:  task.Account,
			Success:  false,
			ErrorMsg: fmt.Sprintf("启动引擎失败: %v", err),
		}
	}

	onEvent(EngineEvent{
		Type:     "task_start",
		TaskId:   task.TaskId,
		Platform: task.Platform,
		Account:  task.Account,
		Message:  fmt.Sprintf("▶ %s 开始执行发布 (标题: %s)...", tagPrefix, task.Title),
	})

	scanner := bufio.NewScanner(stdout)
	for scanner.Scan() {
		line := scanner.Text()
		onEvent(EngineEvent{
			Type:     "log",
			TaskId:   task.TaskId,
			Platform: task.Platform,
			Account:  task.Account,
			Message:  fmt.Sprintf("%s %s", tagPrefix, line),
		})
	}

	waitErr := cmd.Wait()
	if waitErr != nil {
		errMsg := waitErr.Error()
		if strings.Contains(errMsg, "killed") {
			errMsg = "任务被手动中止"
		}
		onEvent(EngineEvent{
			Type:     "task_error",
			TaskId:   task.TaskId,
			Platform: task.Platform,
			Account:  task.Account,
			Message:  fmt.Sprintf("❌ %s 发布失败: %s", tagPrefix, errMsg),
		})
		return AccountPublishResult{
			TaskId:   task.TaskId,
			Platform: task.Platform,
			Account:  task.Account,
			Success:  false,
			ErrorMsg: errMsg,
		}
	}

	onEvent(EngineEvent{
		Type:     "task_success",
		TaskId:   task.TaskId,
		Platform: task.Platform,
		Account:  task.Account,
		Message:  fmt.Sprintf("✅ %s 发布成功！", tagPrefix),
	})
	return AccountPublishResult{
		TaskId:   task.TaskId,
		Platform: task.Platform,
		Account:  task.Account,
		Success:  true,
	}
}

// ExecMatrixPublish 执行全景矩阵差异化发布任务 (Goroutine 信号量池并发调度)
func (s *PublishScheduler) ExecMatrixPublish(param MatrixPublishParam, onEvent func(EngineEvent)) []AccountPublishResult {
	if param.Concurrency <= 0 {
		param.Concurrency = 3
	}

	ctx, cancel := context.WithCancel(context.Background())
	s.tracker.SetCancelFunc(cancel)
	defer s.tracker.ClearCancelFunc()

	total := len(param.Tasks)
	results := make([]AccountPublishResult, total)
	if total == 0 {
		return results
	}

	onEvent(EngineEvent{
		Type:    "info",
		Message: fmt.Sprintf("启动矩阵并发差异化发布任务 (目标账号数: %d, 最大并发限制: %d)...", total, param.Concurrency),
	})

	sem := make(chan struct{}, param.Concurrency)
	var wg sync.WaitGroup

	for i, t := range param.Tasks {
		wg.Add(1)
		go func(idx int, task AccountPublishTask) {
			defer wg.Done()

			select {
			case sem <- struct{}{}:
				defer func() { <-sem }()
			case <-ctx.Done():
				results[idx] = AccountPublishResult{
					Platform: task.Platform,
					Account:  task.Account,
					Success:  false,
					ErrorMsg: "任务已取消",
				}
				return
			}

			results[idx] = s.execSingleTask(ctx, task, "", onEvent)
		}(i, t)
	}

	wg.Wait()

	onEvent(EngineEvent{
		Type:    "success",
		Message: "矩阵全景发布批次全部调度执行完毕！",
	})
	return results
}

// waitWithCountdown 在两个任务节点之间执行带有实时日志倒计时的防风控等待
func waitWithCountdown(ctx context.Context, seconds int, reason string, laneTag string, onEvent func(EngineEvent), taskId, plat, acc string) bool {
	if seconds <= 0 {
		return true
	}

	onEvent(EngineEvent{
		Type:     "log",
		TaskId:   taskId,
		Platform: plat,
		Account:  acc,
		Message:  fmt.Sprintf("⏳ 通道 [%s] %s: 正在执行防风控安全延时 (%d 秒后启动下一操作)...", laneTag, reason, seconds),
	})

	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()

	remaining := seconds
	for remaining > 0 {
		select {
		case <-ticker.C:
			remaining--
			// 在起始、每隔 5 秒或最后 3 秒时向前端推送倒计时心跳日志
			if remaining > 0 && (remaining <= 3 || remaining%5 == 0) {
				onEvent(EngineEvent{
					Type:     "log",
					TaskId:   taskId,
					Platform: plat,
					Account:  acc,
					Message:  fmt.Sprintf("⏳ 通道 [%s] 防风控延时倒计时: 剩余 %d 秒...", laneTag, remaining),
				})
			}
		case <-ctx.Done():
			return false
		}
	}
	return true
}

// ExecPipelinePublish 执行多协程泳道任务工作流 (每个 Lane 启动一个独立 Goroutine 并发运行，通道内串行流水线执行)
func (s *PublishScheduler) ExecPipelinePublish(param PipelinePublishParam, onEvent func(EngineEvent)) []AccountPublishResult {
	if len(param.Lanes) == 0 {
		return nil
	}

	ctx, cancel := context.WithCancel(context.Background())
	s.tracker.SetCancelFunc(cancel)
	defer s.tracker.ClearCancelFunc()

	var allResults []AccountPublishResult
	var mu sync.Mutex
	var wg sync.WaitGroup

	// 平台级防风控互斥锁池 (保障不同平台完全并发，同平台任务跨泳道亦安全串行)
	platformLocks := make(map[string]*sync.Mutex)
	var locksMu sync.Mutex
	getPlatLock := func(plat string) *sync.Mutex {
		locksMu.Lock()
		defer locksMu.Unlock()
		if lk, ok := platformLocks[plat]; ok {
			return lk
		}
		lk := &sync.Mutex{}
		platformLocks[plat] = lk
		return lk
	}

	onEvent(EngineEvent{
		Type:    "info",
		Message: fmt.Sprintf("启动多线程任务工作流调度 (总线程泳道数: %d, 已启用平台级防风控安全锁)...", len(param.Lanes)),
	})

	for laneIdx, lane := range param.Lanes {
		if len(lane.Tasks) == 0 {
			continue
		}
		wg.Add(1)
		go func(lIdx int, l PipelineTaskLane) {
			defer wg.Done()

			laneTag := l.LaneName
			if laneTag == "" {
				laneTag = fmt.Sprintf("线程通道-%d", lIdx+1)
			}

			onEvent(EngineEvent{
				Type:    "info",
				Message: fmt.Sprintf("线程通道 [%s] 启动执行 (包含 %d 个任务节点)...", laneTag, len(l.Tasks)),
			})

			for taskIdx, task := range l.Tasks {
				// 检查全局工作流是否被用户彻底中止
				if ctx.Err() != nil {
					mu.Lock()
					allResults = append(allResults, AccountPublishResult{
						TaskId:   task.TaskId,
						Platform: task.Platform,
						Account:  task.Account,
						Success:  false,
						ErrorMsg: "工作流已中止",
					})
					mu.Unlock()
					return
				}

				// 1. 如果该任务配置了前置防风控延时 (例如继承自上一轮已完成任务的时间间隔)，先执行前置安全倒计时
				if task.InitialDelaySeconds > 0 {
					if !waitWithCountdown(ctx, task.InitialDelaySeconds, "前置防风控保护", laneTag, onEvent, task.TaskId, task.Platform, task.Account) {
						return
					}
				}

				// 2. 平台级防风控锁保护 (避免同平台多账号在不同泳道同时发起调用)
				platLock := getPlatLock(task.Platform)
				platLock.Lock()
				res := s.execSingleTask(ctx, task, laneTag, onEvent)
				platLock.Unlock()

				mu.Lock()
				allResults = append(allResults, res)
				mu.Unlock()

				// 如果全局工作流已被中止，立即退出通道
				if ctx.Err() != nil {
					return
				}

				// 3. 如果不是通道内的最后一个任务，进行后置防风控延时等待
				if taskIdx < len(l.Tasks)-1 {
					delayTime := task.DelaySeconds
					if delayTime <= 0 {
						delayTime = l.DelayBetweenTasks
					}
					if delayTime <= 0 {
						delayTime = 15 // 兜底默认 15 秒
					}
					if !res.Success {
						delayTime = 2 // 异常或中止时仅做 2 秒缓冲即可继续下一个
					}
					if !waitWithCountdown(ctx, delayTime, "任务完成", laneTag, onEvent, task.TaskId, task.Platform, task.Account) {
						return
					}
				}
			}

			onEvent(EngineEvent{
				Type:    "success",
				Message: fmt.Sprintf("通道 [%s] 全部任务执行完成！", laneTag),
			})
		}(laneIdx, lane)
	}

	wg.Wait()

	onEvent(EngineEvent{
		Type:    "success",
		Message: "全部多线程工作流泳道调度执行完毕！",
	})
	return allResults
}

// ExecBatchPublish 执行普通矩阵批量发布任务 (统一转为 MatrixPublishParam 调度)
func (s *PublishScheduler) ExecBatchPublish(param BatchPublishParam, onEvent func(evt EngineEvent)) []AccountPublishResult {
	if len(param.Targets) == 0 {
		return nil
	}

	var tasks []AccountPublishTask
	for _, tgt := range param.Targets {
		tasks = append(tasks, AccountPublishTask{
			Platform:           tgt.Platform,
			Account:            tgt.Account,
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
		})
	}

	return s.ExecMatrixPublish(MatrixPublishParam{
		Concurrency: param.Concurrency,
		Tasks:       tasks,
	}, onEvent)
}
