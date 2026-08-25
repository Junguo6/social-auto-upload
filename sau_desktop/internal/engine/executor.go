package engine

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"sync"
)

type Executor struct {
	engineBin    string
	workDir      string
	activeCancel context.CancelFunc
	activeCmds   map[*exec.Cmd]bool
	mu           sync.Mutex
}

func NewExecutor() (*Executor, error) {
	execPath, workDir, err := resolveEngineAndWorkDir()
	if err != nil {
		return nil, err
	}
	return &Executor{
		engineBin:  execPath,
		workDir:    workDir,
		activeCmds: make(map[*exec.Cmd]bool),
	}, nil
}

func resolveEngineAndWorkDir() (string, string, error) {
	dir, err := os.Getwd()
	if err != nil {
		return "", "", err
	}

	binName := "sau_engine"
	if runtime.GOOS == "windows" {
		binName = "sau_engine.exe"
	}

	possiblePaths := []string{
		filepath.Join(dir, "bin", "sau_engine", binName),
		filepath.Join(dir, "sau_desktop", "bin", "sau_engine", binName),
		filepath.Join(dir, "..", "dist", "sau_engine", binName),
		filepath.Join(dir, "dist", "sau_engine", binName),
		filepath.Join(dir, binName),
	}

	var foundBin string
	for _, p := range possiblePaths {
		absP, _ := filepath.Abs(p)
		if _, err := os.Stat(absP); err == nil {
			foundBin = absP
			break
		}
	}

	if foundBin == "" {
		return "", "", fmt.Errorf("sau_engine 可执行二进制文件未找到，查找路径包括: %v", possiblePaths)
	}

	workDir := dir
	candidates := []string{
		dir,
		filepath.Join(dir, ".."),
		filepath.Dir(filepath.Dir(foundBin)),
	}

	for _, c := range candidates {
		absC, _ := filepath.Abs(c)
		if _, err := os.Stat(filepath.Join(absC, "conf.py")); err == nil {
			workDir = absC
			break
		}
	}

	return foundBin, workDir, nil
}

func (e *Executor) resolveToAbsPath(rawPath string) string {
	if rawPath == "" {
		return ""
	}
	if filepath.IsAbs(rawPath) {
		return rawPath
	}
	target1 := filepath.Join(e.workDir, rawPath)
	if _, err := os.Stat(target1); err == nil {
		return target1
	}
	cwd, _ := os.Getwd()
	target2 := filepath.Join(cwd, rawPath)
	if _, err := os.Stat(target2); err == nil {
		return target2
	}
	return target1
}

func (e *Executor) buildCommand(ctx context.Context, args ...string) *exec.Cmd {
	var cmd *exec.Cmd
	if ctx != nil {
		cmd = exec.CommandContext(ctx, e.engineBin, args...)
	} else {
		cmd = exec.Command(e.engineBin, args...)
	}
	cmd.Dir = e.workDir

	envs := os.Environ()
	envs = append(envs,
		"PYTHONIOENCODING=utf-8",
		"PYTHONUTF8=1",
		"LANG=en_US.UTF-8",
		"LC_ALL=en_US.UTF-8",
	)
	cmd.Env = envs
	return cmd
}

// StopActiveTask 手动中止当前正在运行的全部任务 (单发或批处理)
func (e *Executor) StopActiveTask() bool {
	e.mu.Lock()
	defer e.mu.Unlock()
	if e.activeCancel != nil {
		e.activeCancel()
		e.activeCancel = nil
		return true
	}
	return false
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

// ExecBatchPublish 基于 Go Goroutine 并发池的矩阵批量发布调度器 (完整支持 CLI 规范全量参数)
func (e *Executor) ExecBatchPublish(param BatchPublishParam, onEvent func(evt EngineEvent)) []AccountPublishResult {
	if len(param.Targets) == 0 {
		return nil
	}

	concurrency := param.Concurrency
	if concurrency <= 0 {
		concurrency = 3
	}
	if concurrency > 10 {
		concurrency = 10
	}

	ctx, cancel := context.WithCancel(context.Background())
	e.mu.Lock()
	e.activeCancel = cancel
	e.mu.Unlock()

	defer func() {
		e.mu.Lock()
		e.activeCancel = nil
		e.mu.Unlock()
	}()

	action := param.Action
	if action == "" {
		action = "upload-video"
	}

	// 提前转换媒体与封面绝对路径
	absFilePath := e.resolveToAbsPath(param.FilePath)
	var absImages []string
	for _, img := range param.Images {
		absImages = append(absImages, e.resolveToAbsPath(img))
	}
	absThumbnail := e.resolveToAbsPath(param.Thumbnail)
	absThumbLand := e.resolveToAbsPath(param.ThumbnailLandscape)
	absThumbPort := e.resolveToAbsPath(param.ThumbnailPortrait)
	absNotef := e.resolveToAbsPath(param.Notef)

	total := len(param.Targets)
	onEvent(EngineEvent{
		Type:    "log",
		Message: fmt.Sprintf("🚀 启动矩阵并发发布任务 (目标账号数: %d, 最大并发限制: %d)...", total, concurrency),
	})

	results := make([]AccountPublishResult, total)
	var wg sync.WaitGroup
	sem := make(chan struct{}, concurrency)

	for i, target := range param.Targets {
		wg.Add(1)
		go func(idx int, tgt TargetAccount) {
			defer wg.Done()

			select {
			case sem <- struct{}{}:
				defer func() { <-sem }()
			case <-ctx.Done():
				results[idx] = AccountPublishResult{
					Platform: tgt.Platform,
					Account:  tgt.Account,
					Success:  false,
					ErrorMsg: "任务已取消",
				}
				return
			}

			// 组装完整的命令行参数 (严格遵循 docs/api_specification.md)
			args := []string{
				tgt.Platform, action,
				"--account", tgt.Account,
			}

			if absFilePath != "" && action == "upload-video" {
				args = append(args, "--file", absFilePath)
			}
			if len(absImages) > 0 && action == "upload-note" {
				args = append(args, "--images")
				args = append(args, absImages...)
			}
			if param.Title != "" {
				args = append(args, "--title", param.Title)
			}
			if param.Desc != "" {
				args = append(args, "--desc", param.Desc)
			}
			if param.Tags != "" {
				args = append(args, "--tags", param.Tags)
			}

			// 封面图
			if absThumbnail != "" {
				args = append(args, "--thumbnail", absThumbnail)
			}
			if absThumbLand != "" {
				args = append(args, "--thumbnail-landscape", absThumbLand)
			}
			if absThumbPort != "" {
				args = append(args, "--thumbnail-portrait", absThumbPort)
			}

			// B站特定分区
			if tgt.Platform == "bilibili" && param.Tid > 0 {
				args = append(args, "--tid", strconv.Itoa(param.Tid))
			}

			// 视频号特定选项
			if tgt.Platform == "tencent" {
				if param.ShortTitle != "" {
					args = append(args, "--short-title", param.ShortTitle)
				}
				if param.Category != "" {
					args = append(args, "--category", param.Category)
				}
				if param.Draft {
					args = append(args, "--draft")
				}
			}

			// 抖音特定小黄车带货
			if tgt.Platform == "douyin" {
				if param.ProductLink != "" {
					args = append(args, "--product-link", param.ProductLink)
				}
				if param.ProductTitle != "" {
					args = append(args, "--product-title", param.ProductTitle)
				}
			}

			// 合集专栏
			if param.Collection != "" {
				args = append(args, "--collection", param.Collection)
			}

			// YouTube/B站 可见性与播放列表
			if param.Visibility != "" {
				args = append(args, "--visibility", param.Visibility)
			}
			if param.Playlist != "" {
				args = append(args, "--playlist", param.Playlist)
			}

			// 图文配乐与长正文
			if action == "upload-note" {
				if param.Bgm != "" {
					args = append(args, "--bgm", param.Bgm)
				}
				if param.Note != "" {
					args = append(args, "--note", param.Note)
				}
				if absNotef != "" {
					args = append(args, "--notef", absNotef)
				}
			}

			// 定时与声明
			if param.Schedule != "" {
				args = append(args, "--schedule", param.Schedule)
			}
			if param.Declaration != "" {
				args = append(args, "--declaration", param.Declaration)
			}

			if param.Headless {
				args = append(args, "--headless")
			} else {
				args = append(args, "--headed")
			}

			cmd := e.buildCommand(ctx, args...)

			e.mu.Lock()
			e.activeCmds[cmd] = true
			e.mu.Unlock()

			defer func() {
				e.mu.Lock()
				delete(e.activeCmds, cmd)
				e.mu.Unlock()
			}()

			stdout, err := cmd.StdoutPipe()
			if err != nil {
				results[idx] = AccountPublishResult{
					Platform: tgt.Platform,
					Account:  tgt.Account,
					Success:  false,
					ErrorMsg: fmt.Sprintf("创建输出管道失败: %v", err),
				}
				return
			}
			cmd.Stderr = cmd.Stdout

			if err := cmd.Start(); err != nil {
				results[idx] = AccountPublishResult{
					Platform: tgt.Platform,
					Account:  tgt.Account,
					Success:  false,
					ErrorMsg: fmt.Sprintf("启动引擎失败: %v", err),
				}
				return
			}

			tagPrefix := fmt.Sprintf("[%s:%s]", tgt.Platform, tgt.Account)
			onEvent(EngineEvent{
				Type:     "log",
				Platform: tgt.Platform,
				Account:  tgt.Account,
				Message:  fmt.Sprintf("▶ %s 开始执行发布...", tagPrefix),
			})

			scanner := bufio.NewScanner(stdout)
			for scanner.Scan() {
				line := scanner.Text()
				onEvent(EngineEvent{
					Type:     "log",
					Platform: tgt.Platform,
					Account:  tgt.Account,
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
					Platform: tgt.Platform,
					Account:  tgt.Account,
					Success:  false,
					ErrorMsg: errMsg,
				}
				onEvent(EngineEvent{
					Type:     "error",
					Platform: tgt.Platform,
					Account:  tgt.Account,
					Message:  fmt.Sprintf("❌ %s 发布失败: %s", tagPrefix, errMsg),
				})
			} else {
				results[idx] = AccountPublishResult{
					Platform: tgt.Platform,
					Account:  tgt.Account,
					Success:  true,
				}
				onEvent(EngineEvent{
					Type:     "success",
					Platform: tgt.Platform,
					Account:  tgt.Account,
					Message:  fmt.Sprintf("✅ %s 发布成功！", tagPrefix),
				})
			}
		}(i, target)
	}

	wg.Wait()

	onEvent(EngineEvent{
		Type:    "success",
		Message: "🎉 矩阵批量发布批次全部调度执行完毕！",
	})
	return results
}

// CheckAccount 检查账号登录凭证有效性
func (e *Executor) CheckAccount(platform, account string) (bool, string) {
	cmd := e.buildCommand(nil, platform, "check", "--account", account)
	output, err := cmd.CombinedOutput()
	outStr := strings.TrimSpace(string(output))

	if err == nil && strings.Contains(outStr, "valid") {
		return true, "凭证有效"
	}
	return false, outStr
}

// LoginAccount 拉起界面/终端登录
func (e *Executor) LoginAccount(platform, account string, headed bool, onEvent func(evt EngineEvent)) error {
	args := []string{platform, "login", "--account", account}
	if headed {
		args = append(args, "--headed")
	}

	cmd := e.buildCommand(nil, args...)
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return err
	}
	cmd.Stderr = cmd.Stdout

	if err := cmd.Start(); err != nil {
		return err
	}

	onEvent(EngineEvent{Type: "log", Message: fmt.Sprintf("▶ 开始登录流程: sau %s", strings.Join(args, " "))})

	scanner := bufio.NewScanner(stdout)
	for scanner.Scan() {
		line := scanner.Text()
		onEvent(EngineEvent{Type: "log", Message: line})
	}

	return cmd.Wait()
}
