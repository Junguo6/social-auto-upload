package engine

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// AccountManager 负责账号凭证有效性检查与扫码登录
type AccountManager struct {
	runtime *RuntimeManager
	tracker *ProcessTracker
}

func NewAccountManager(runtime *RuntimeManager, tracker *ProcessTracker) *AccountManager {
	return &AccountManager{runtime: runtime, tracker: tracker}
}

// CheckAccount 检查账号登录凭证有效性 (杜绝假阳性)
func (am *AccountManager) CheckAccount(platform, account string) (bool, string) {
	if account == "" || account == "auto" {
		return false, "无效账号标识"
	}
	cmd := am.runtime.BuildCommand(nil, platform, "check", "--account", account)
	output, err := cmd.CombinedOutput()
	outStr := strings.TrimSpace(string(output))

	if err != nil || strings.Contains(outStr, "invalid") {
		return false, "凭证已失效"
	}

	lines := strings.Split(outStr, "\n")
	for _, l := range lines {
		if strings.TrimSpace(l) == "valid" {
			return true, "凭证有效"
		}
	}
	return false, outStr
}

// DeleteAccountCredential 安全彻底删除本地磁盘上的指定平台账号凭证及关联缓存文件 (防幽灵文件残留)
func (am *AccountManager) DeleteAccountCredential(platform, account string) error {
	if platform == "" || account == "" || account == "auto" {
		return nil
	}

	// 候选 cookies 存储目录链
	candidateDirs := []string{
		filepath.Join(am.runtime.WorkDir, "cookies"),
		filepath.Join(filepath.Dir(am.runtime.EngineBin), "cookies"),
		filepath.Join(am.runtime.WorkDir, "bin", "sau_engine", "_internal", "cookies"),
	}

	targetJsonName := fmt.Sprintf("%s_%s.json", platform, account)
	filePrefix := fmt.Sprintf("%s_%s", platform, account)

	for _, dir := range candidateDirs {
		if _, err := os.Stat(dir); os.IsNotExist(err) {
			continue
		}

		// 1. 删除具体的凭证 JSON 文件，并同步清理该平台的 auto.json 临时残留文件
		jsonPath := filepath.Join(dir, targetJsonName)
		_ = os.Remove(jsonPath)
		autoPath := filepath.Join(dir, fmt.Sprintf("%s_auto.json", platform))
		_ = os.Remove(autoPath)

		// 2. 清理关联的登录二维码或验证码图片
		entries, err := os.ReadDir(dir)
		if err == nil {
			for _, entry := range entries {
				if !entry.IsDir() && strings.HasPrefix(entry.Name(), filePrefix) {
					_ = os.Remove(filepath.Join(dir, entry.Name()))
				}
			}
		}
	}

	return nil
}

// GetAccountSavedMeta 从磁盘凭证文件快速读取已缓存的头像 URL、真实昵称与 UID
func (am *AccountManager) GetAccountSavedMeta(platform, account string) (avatar string, nickname string, finderUid string) {
	if platform == "" || account == "" || account == "auto" {
		return "", "", ""
	}
	candidateDirs := []string{
		filepath.Join(am.runtime.WorkDir, "cookies"),
		filepath.Join(filepath.Dir(am.runtime.EngineBin), "cookies"),
		filepath.Join(am.runtime.WorkDir, "bin", "sau_engine", "_internal", "cookies"),
	}
	targetJsonName := fmt.Sprintf("%s_%s.json", platform, account)
	for _, dir := range candidateDirs {
		jsonPath := filepath.Join(dir, targetJsonName)
		data, err := os.ReadFile(jsonPath)
		if err != nil {
			continue
		}
		var state map[string]interface{}
		if err := json.Unmarshal(data, &state); err == nil {
			if meta, ok := state["__account_meta__"].(map[string]interface{}); ok {
				if av, ok := meta["avatar"].(string); ok {
					avatar = av
				}
				if nick, ok := meta["nickname"].(string); ok {
					nickname = nick
				}
				if uid, ok := meta["finder_uid"].(string); ok {
					finderUid = uid
				}
				if avatar != "" || nickname != "" {
					return
				}
			}
		}
	}
	return
}

// GetAccountSavedAvatar 从磁盘凭证文件快速读取已缓存的头像 URL
func (am *AccountManager) GetAccountSavedAvatar(platform, account string) string {
	avatar, _, _ := am.GetAccountSavedMeta(platform, account)
	return avatar
}

// LoginAccount 拉起界面/终端登录并自动解析账号昵称与 UID
func (am *AccountManager) LoginAccount(platform, account string, headed bool, onEvent func(evt EngineEvent)) (LoginResult, error) {
	return am.loginInternal(platform, account, headed, false, onEvent)
}

// LoginAccountWithAppWindow 在原生系统拉起独立的纯净 Chrome App 沉浸式视窗 (4K 原生画质与 0 延迟，剥离地址栏)
func (am *AccountManager) LoginAccountWithAppWindow(platform, account string, onEvent func(evt EngineEvent)) (LoginResult, error) {
	return am.loginInternal(platform, account, true, false, onEvent)
}

// LoginAccountWithScreencast 在后台以无头模式拉起登录，并通过 CDP 实时抽取画面流供前端画布呈现与反向交互
func (am *AccountManager) LoginAccountWithScreencast(platform, account string, onEvent func(evt EngineEvent)) (LoginResult, error) {
	return am.loginInternal(platform, account, false, true, onEvent)
}

func (am *AccountManager) loginInternal(platform, account string, headed bool, screencast bool, onEvent func(evt EngineEvent)) (LoginResult, error) {
	if account == "" {
		account = "auto"
	}
	loginTaskId := fmt.Sprintf("login_%s_%s", platform, account)
	args := []string{platform, "login", "--account", account}
	if headed {
		args = append(args, "--headed", "--app-mode", "--task-id", loginTaskId)
	} else {
		args = append(args, "--headless")
	}
	if screencast {
		args = append(args, "--screencast", "--task-id", loginTaskId)
	}

	res := LoginResult{
		Platform: platform,
		Account:  account,
		Nickname: account,
		Success:  false,
	}

	cmd := am.runtime.BuildCommand(nil, args...)
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return res, err
	}
	cmd.Stderr = cmd.Stdout

	stdin, err := cmd.StdinPipe()
	if err == nil && am.tracker != nil {
		am.tracker.RegisterTaskStdin(loginTaskId, stdin)
		am.tracker.RegisterTaskStdin(fmt.Sprintf("%s:%s", platform, account), stdin)
	}
	defer func() {
		if am.tracker != nil {
			am.tracker.UnregisterTaskStdin(loginTaskId)
			am.tracker.UnregisterTaskStdin(fmt.Sprintf("%s:%s", platform, account))
		}
	}()

	if err := cmd.Start(); err != nil {
		return res, err
	}

	if am.tracker != nil {
		am.tracker.RegisterTaskCmd(loginTaskId, cmd)
		am.tracker.RegisterTaskCmd(fmt.Sprintf("%s:%s", platform, account), cmd)
	}
	defer func() {
		if am.tracker != nil {
			am.tracker.UnregisterTaskCmd(loginTaskId, cmd)
			am.tracker.UnregisterTaskCmd(fmt.Sprintf("%s:%s", platform, account), cmd)
			am.tracker.UnregisterTaskStdin(loginTaskId)
			am.tracker.UnregisterTaskStdin(fmt.Sprintf("%s:%s", platform, account))
		}
	}()

	onEvent(EngineEvent{
		Type:    "log",
		TaskId:  loginTaskId,
		Message: fmt.Sprintf("▶ 开始登录流程 (内嵌实时投屏: %v): sau %s", screencast, strings.Join(args, " ")),
	})

	var lastErrLine string
	reader := bufio.NewReaderSize(stdout, 1024*1024)
	for {
		lineBytes, err := reader.ReadBytes('\n')
		if len(lineBytes) > 0 {
			line := strings.TrimRight(string(lineBytes), "\r\n")
			lowerLine := strings.ToLower(line)
			if strings.Contains(lowerLine, "error") || strings.Contains(line, "traceback") || strings.Contains(line, "exception") || strings.Contains(lowerLine, "failed") {
				// 避免被 PyInstaller 的通用致命错误行覆盖掉真正的 Python Traceback 根因
				if !strings.HasPrefix(line, "[PYI-") || lastErrLine == "" {
					lastErrLine = line
				}
			}

			// 捕获并分发 CDP 实时投屏帧，不污染普通日志抽屉
			if strings.HasPrefix(line, "[CDP_FRAME] ") {
				framePayload := strings.TrimPrefix(line, "[CDP_FRAME] ")
				onEvent(EngineEvent{
					Type:     "screencast_frame",
					TaskId:   loginTaskId,
					Platform: platform,
					Account:  account,
					Message:  framePayload,
				})
				if err != nil {
					break
				}
				continue
			}

			onEvent(EngineEvent{
				Type:     "log",
				TaskId:   loginTaskId,
				Platform: platform,
				Account:  account,
				Message:  line,
			})

			// 匹配结构化登录元数据
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
						} else if res.Account == "auto" && res.FinderUid != "" {
							res.Account = res.FinderUid
						}
						if av, ok := meta["avatar"].(string); ok && av != "" {
							res.Avatar = av
						}
					}
				}
				onEvent(EngineEvent{
					Type:      "login_success",
					TaskId:    loginTaskId,
					Platform:  platform,
					Account:   res.Account,
					Nickname:  res.Nickname,
					FinderUid: res.FinderUid,
					Avatar:    res.Avatar,
					Message:   line,
				})
			}
		}

		if err != nil {
			break
		}
	}

	waitErr := cmd.Wait()
	if waitErr != nil && !res.Success {
		res.Success = false
		if lastErrLine != "" {
			res.Msg = fmt.Sprintf("拉起浏览器异常: %s", lastErrLine)
		} else {
			res.Msg = fmt.Sprintf("浏览器进程异常退出: %v", waitErr)
		}
		return res, fmt.Errorf("%s", res.Msg)
	}

	// 毫秒级极速仲裁（杜绝关闭视窗后的二次全量阻塞 check 与假阳性）
	if res.Success {
		// 浏览器会长连接已明确完成登录并抽取了 UID/昵称与 storage_state
		res.Msg = "登录成功且凭证已存盘"
	} else {
		// 会话中未检测到登录授权即被关闭
		res.Success = false
		if account == "auto" {
			res.Msg = "未完成扫码登录，会话已结束"
		} else {
			res.Msg = "会话已结束，凭证未更新"
		}
	}

	if res.Nickname == "" || res.Nickname == "auto" {
		if res.Account != "" && res.Account != "auto" {
			res.Nickname = res.Account
		}
	}
	return res, nil
}
