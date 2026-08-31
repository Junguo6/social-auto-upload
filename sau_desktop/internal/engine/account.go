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
}

func NewAccountManager(runtime *RuntimeManager) *AccountManager {
	return &AccountManager{runtime: runtime}
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

	cmd := am.runtime.BuildCommand(nil, args...)
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
