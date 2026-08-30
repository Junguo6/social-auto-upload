package engine

import (
	"bufio"
	"context"
	"encoding/json"
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
	usePythonSrc bool
	pythonBin    string
	sauCliScript string
	activeCancel context.CancelFunc
	activeCmds   map[*exec.Cmd]bool
	mu           sync.Mutex
}

func NewExecutor() (*Executor, error) {
	execPath, workDir, pythonBin, sauCliScript, useSrc, err := resolveEngineAndWorkDir()
	if err != nil {
		return nil, err
	}
	return &Executor{
		engineBin:    execPath,
		workDir:      workDir,
		usePythonSrc: useSrc,
		pythonBin:    pythonBin,
		sauCliScript: sauCliScript,
		activeCmds:   make(map[*exec.Cmd]bool),
	}, nil
}

func resolveEngineAndWorkDir() (string, string, string, string, bool, error) {
	dir, err := os.Getwd()
	if err != nil {
		return "", "", "", "", false, err
	}

	// 1. 定位项目根目录 (包含 conf.py 或 sau_cli.py 的目录)
	workDir := dir
	candidates := []string{
		dir,
		filepath.Join(dir, ".."),
		filepath.Join(dir, "..", ".."),
	}

	for _, c := range candidates {
		absC, _ := filepath.Abs(c)
		if _, err := os.Stat(filepath.Join(absC, "conf.py")); err == nil {
			workDir = absC
			break
		} else if _, err := os.Stat(filepath.Join(absC, "sau_cli.py")); err == nil {
			workDir = absC
			break
		}
	}

	// 2. 优先探测 Python 源码调试环境 (.venv + sau_cli.py)
	pyName := filepath.Join("bin", "python")
	if runtime.GOOS == "windows" {
		pyName = filepath.Join("Scripts", "python.exe")
	}

	venvPyCandidates := []string{
		filepath.Join(workDir, ".venv", pyName),
		filepath.Join(dir, ".venv", pyName),
		filepath.Join(dir, "..", ".venv", pyName),
	}

	sauCliPath := filepath.Join(workDir, "sau_cli.py")
	if _, err := os.Stat(sauCliPath); err == nil {
		for _, vpy := range venvPyCandidates {
			absVpy, _ := filepath.Abs(vpy)
			if _, err := os.Stat(absVpy); err == nil {
				return "", workDir, absVpy, sauCliPath, true, nil
			}
		}
	}

	// 3. 生产/无源码环境下，回退查找打包好的 sau_engine 二进制
	binName := "sau_engine"
	if runtime.GOOS == "windows" {
		binName = "sau_engine.exe"
	}

	possiblePaths := []string{
		filepath.Join(workDir, "sau_desktop", "bin", "sau_engine", binName),
		filepath.Join(workDir, "dist", "sau_engine", binName),
		filepath.Join(dir, "bin", "sau_engine", binName),
		filepath.Join(dir, "sau_desktop", "bin", "sau_engine", binName),
		filepath.Join(dir, "..", "dist", "sau_engine", binName),
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
		return "", "", "", "", false, fmt.Errorf("sau_engine 可执行二进制或 Python 源码环境未找到，查找路径包括: %v", possiblePaths)
	}

	return foundBin, workDir, "", "", false, nil
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
	if e.usePythonSrc {
		fullArgs := append([]string{e.sauCliScript}, args...)
		if ctx != nil {
			cmd = exec.CommandContext(ctx, e.pythonBin, fullArgs...)
		} else {
			cmd = exec.Command(e.pythonBin, fullArgs...)
		}
	} else {
		if ctx != nil {
			cmd = exec.CommandContext(ctx, e.engineBin, args...)
		} else {
			cmd = exec.Command(e.engineBin, args...)
		}
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

			// 组装命令行参数 (严格匹配 sau_cli.py 各平台解析器的支持参数)
			args := []string{
				tgt.Platform, action,
				"--account", tgt.Account,
			}

			// 基础媒体与文本参数
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

			// 封面图支持: 绝大多数平台支持 --thumbnail
			if absThumbnail != "" {
				args = append(args, "--thumbnail", absThumbnail)
			}
			// 横竖版封面: 仅 douyin 与 tencent 支持
			if (tgt.Platform == "douyin" || tgt.Platform == "tencent") && action == "upload-video" {
				if absThumbLand != "" {
					args = append(args, "--thumbnail-landscape", absThumbLand)
				}
				if absThumbPort != "" {
					args = append(args, "--thumbnail-portrait", absThumbPort)
				}
			}

			// 定时发布: 仅 douyin, kuaishou, xiaohongshu, bilibili, tencent 支持
			if param.Schedule != "" {
				switch tgt.Platform {
				case "douyin", "kuaishou", "xiaohongshu", "bilibili", "tencent":
					args = append(args, "--schedule", param.Schedule)
				}
			}

			// 合规声明: 仅 douyin 支持
			if tgt.Platform == "douyin" && param.Declaration != "" && action == "upload-video" {
				args = append(args, "--declaration", param.Declaration)
			}

			// 专栏/合集: 仅 douyin, kuaishou, tencent, alipay, weibo, baijiahao 支持
			if param.Collection != "" && action == "upload-video" {
				switch tgt.Platform {
				case "douyin", "kuaishou", "tencent", "alipay", "weibo", "baijiahao":
					args = append(args, "--collection", param.Collection)
				}
			}

			// B站特定分区 (TID)
			if tgt.Platform == "bilibili" && param.Tid > 0 && action == "upload-video" {
				args = append(args, "--tid", strconv.Itoa(param.Tid))
			}

			// 微信视频号特定选项
			if tgt.Platform == "tencent" && action == "upload-video" {
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
			if tgt.Platform == "douyin" && action == "upload-video" {
				if param.ProductLink != "" {
					args = append(args, "--product-link", param.ProductLink)
				}
				if param.ProductTitle != "" {
					args = append(args, "--product-title", param.ProductTitle)
				}
			}

			// YouTube 特定可见性与播放列表
			if tgt.Platform == "youtube" && action == "upload-video" {
				if param.Visibility != "" {
					args = append(args, "--visibility", param.Visibility)
				}
				if param.Playlist != "" {
					args = append(args, "--playlist", param.Playlist)
				}
			}

			// 图文特有参数 (BGM, Note, Notef)
			if action == "upload-note" {
				if tgt.Platform == "douyin" && param.Bgm != "" {
					args = append(args, "--bgm", param.Bgm)
				}
				if param.Note != "" {
					args = append(args, "--note", param.Note)
				}
				if tgt.Platform == "douyin" && absNotef != "" {
					args = append(args, "--notef", absNotef)
				}
			}

			// 运行模式 (bilibili 命令行封装不接收 --headless/--headed 参数)
			if tgt.Platform != "bilibili" {
				if param.Headless {
					args = append(args, "--headless")
				} else {
					args = append(args, "--headed")
				}
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

// LoginAccount 拉起界面/终端登录并自动解析账号昵称与UID
func (e *Executor) LoginAccount(platform, account string, headed bool, onEvent func(evt EngineEvent)) (LoginResult, error) {
	if account == "" {
		account = "auto"
	}
	args := []string{platform, "login", "--account", account}
	if headed {
		args = append(args, "--headed")
	}

	res := LoginResult{
		Platform: platform,
		Account:  account,
		Nickname: account,
		Success:  false,
	}

	cmd := e.buildCommand(nil, args...)
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return res, err
	}
	cmd.Stderr = cmd.Stdout

	if err := cmd.Start(); err != nil {
		return res, err
	}

	onEvent(EngineEvent{Type: "log", Message: fmt.Sprintf("▶ 开始登录流程: sau %s", strings.Join(args, " "))})

	scanner := bufio.NewScanner(stdout)
	for scanner.Scan() {
		line := scanner.Text()
		onEvent(EngineEvent{Type: "log", Message: line})

		// 匹配结构化登录结果，如: Tencent/WeChat Channels login flow completed: {"nickname": "...", "finder_uid": "...", "account_name": "..."}
		if strings.Contains(line, "login flow completed") {
			res.Success = true
			if idx := strings.Index(line, "{"); idx != -1 {
				jsonStr := line[idx:]
				var meta map[string]interface{}
				if jsonErr := json.Unmarshal([]byte(jsonStr), &meta); jsonErr == nil {
					if nick, ok := meta["nickname"].(string); ok && nick != "" {
						res.Nickname = nick
					}
					if uid, ok := meta["finder_uid"].(string); ok && uid != "" {
						res.FinderUid = uid
					}
					if acc, ok := meta["account_name"].(string); ok && acc != "" {
						res.Account = acc
					}
				}
			}
		}
	}

	waitErr := cmd.Wait()
	if waitErr != nil {
		res.Success = false
		res.Msg = waitErr.Error()
		return res, waitErr
	}

	res.Success = true
	res.Msg = "登录成功"
	if res.Nickname == "" || res.Nickname == "auto" {
		if res.Account != "" && res.Account != "auto" {
			res.Nickname = res.Account
		}
	}
	return res, nil
}

