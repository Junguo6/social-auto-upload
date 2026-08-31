package engine

import (
	"bufio"
	"context"
	"fmt"
	"strings"
	"sync"
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
		Message: fmt.Sprintf("🚀 启动矩阵并发差异化发布任务 (目标账号数: %d, 最大并发限制: %d)...", total, param.Concurrency),
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

			args := s.builder.BuildTaskArgs(task)
			cmd := s.runtime.BuildCommand(ctx, args...)

			s.tracker.RegisterCmd(cmd)
			defer s.tracker.UnregisterCmd(cmd)

			displayName := task.Nickname
			if displayName == "" {
				displayName = task.Account
			}
			tagPrefix := fmt.Sprintf("[%s:%s]", task.Platform, displayName)

			stdout, err := cmd.StdoutPipe()
			if err != nil {
				results[idx] = AccountPublishResult{
					Platform: task.Platform,
					Account:  task.Account,
					Success:  false,
					ErrorMsg: fmt.Sprintf("创建输出管道失败: %v", err),
				}
				return
			}
			cmd.Stderr = cmd.Stdout

			if err := cmd.Start(); err != nil {
				results[idx] = AccountPublishResult{
					Platform: task.Platform,
					Account:  task.Account,
					Success:  false,
					ErrorMsg: fmt.Sprintf("启动引擎失败: %v", err),
				}
				return
			}

			onEvent(EngineEvent{
				Type:     "log",
				Platform: task.Platform,
				Account:  task.Account,
				Message:  fmt.Sprintf("▶ %s 开始执行发布 (标题: %s)...", tagPrefix, task.Title),
			})

			scanner := bufio.NewScanner(stdout)
			for scanner.Scan() {
				line := scanner.Text()
				onEvent(EngineEvent{
					Type:     "log",
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
				results[idx] = AccountPublishResult{
					Platform: task.Platform,
					Account:  task.Account,
					Success:  false,
					ErrorMsg: errMsg,
				}
				onEvent(EngineEvent{
					Type:     "error",
					Platform: task.Platform,
					Account:  task.Account,
					Message:  fmt.Sprintf("❌ %s 发布失败: %s", tagPrefix, errMsg),
				})
			} else {
				results[idx] = AccountPublishResult{
					Platform: task.Platform,
					Account:  task.Account,
					Success:  true,
				}
				onEvent(EngineEvent{
					Type:     "success",
					Platform: task.Platform,
					Account:  task.Account,
					Message:  fmt.Sprintf("✅ %s 发布成功！", tagPrefix),
				})
			}
		}(i, t)
	}

	wg.Wait()

	onEvent(EngineEvent{
		Type:    "success",
		Message: "🎉 矩阵全景发布批次全部调度执行完毕！",
	})
	return results
}

// ExecBatchPublish 执行普通矩阵批量发布任务 (统一转为 MatrixPublishParam 调度)
func (s *PublishScheduler) ExecBatchPublish(param BatchPublishParam, onEvent func(evt EngineEvent)) []AccountPublishResult {
	if len(param.Targets) == 0 {
		return nil
	}

	// 转换为全景矩阵任务
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
