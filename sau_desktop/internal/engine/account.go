package engine

import (
	"bufio"
	"encoding/json"
	"fmt"
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
						}
					}
				}
				onEvent(EngineEvent{
					Type:     "login_success",
					TaskId:   loginTaskId,
					Platform: platform,
					Account:  account,
					Message:  line,
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

	targetAcc := account
	if res.Account != "" && res.Account != "auto" {
		targetAcc = res.Account
	}

	// 辅助验证：若浏览器会话已明确报告登录成功，则信任该结果，check 仅作为锦上添花；
	// 若会话本身未能确认登录状态，才以 check 结果作为最终仲裁。
	if res.Success {
		// 浏览器会话已确认成功（检测到 "login flow completed"），信任该结果
		res.Msg = "登录成功且凭证已存盘"
		// 异步尝试 check，但不覆盖成功状态
		isValid, _ := am.CheckAccount(platform, targetAcc)
		if isValid {
			res.Msg = "登录成功且凭证有效"
		}
		// 即使 check 失败也不翻转 Success：凭证文件已存盘，后续上传时会再次验证
	} else {
		// 会话未能明确确认登录，以 check 命令结果作为最终判定
		isValid, checkMsg := am.CheckAccount(platform, targetAcc)
		if isValid {
			res.Success = true
			res.Msg = "登录成功且凭证有效"
		} else {
			res.Msg = fmt.Sprintf("凭证未就绪或未检测到有效登录 (%s)", checkMsg)
		}
	}

	if res.Nickname == "" || res.Nickname == "auto" {
		if res.Account != "" && res.Account != "auto" {
			res.Nickname = res.Account
		}
	}
	return res, nil
}
