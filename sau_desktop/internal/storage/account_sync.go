package storage

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// AccountRecord 账号元数据模型（严格对齐前端 AccountItem）
type AccountRecord struct {
	Platform  string   `json:"platform"`
	Account   string   `json:"account"`
	Nickname  string   `json:"nickname,omitempty"`
	FinderUid string   `json:"finderUid,omitempty"`
	Avatar    string   `json:"avatar,omitempty"`
	Groups    []string `json:"groups,omitempty"`
	IsValid   bool     `json:"isValid,omitempty"`
	Checked   bool     `json:"checked,omitempty"`
	Msg       string   `json:"msg,omitempty"`
	CheckedAt int64    `json:"checkedAt,omitempty"`
}

// AccountSyncService 负责物理凭证目录 (cookies/*.json) 与系统账号数据的双向同步与反向发现
type AccountSyncService struct {
	cookiesDir string
	driver     Driver
}

// NewAccountSyncService 创建账号同步服务
func NewAccountSyncService(cookiesDir string, driver Driver) *AccountSyncService {
	_ = os.MkdirAll(cookiesDir, 0755)
	return &AccountSyncService{
		cookiesDir: cookiesDir,
		driver:     driver,
	}
}

// SyncAccounts 反向扫描 cookies 目录，与前端传入的数据合并并物理落盘
func (s *AccountSyncService) SyncAccounts(clientAccountsJSON string) (string, error) {
	var accounts []AccountRecord
	if strings.TrimSpace(clientAccountsJSON) != "" {
		_ = json.Unmarshal([]byte(clientAccountsJSON), &accounts)
	}

	// 建立 (platform + ":" + account) 唯一键索引
	accountMap := make(map[string]AccountRecord)
	for _, acc := range accounts {
		key := fmt.Sprintf("%s:%s", acc.Platform, acc.Account)
		accountMap[key] = acc
	}

	files, err := os.ReadDir(s.cookiesDir)
	if err != nil {
		return clientAccountsJSON, fmt.Errorf("failed to read cookies dir: %w", err)
	}

	hasChanges := false
	for _, entry := range files {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".json") {
			continue
		}

		baseName := strings.TrimSuffix(entry.Name(), ".json")
		parts := strings.SplitN(baseName, "_", 2)
		if len(parts) < 2 {
			continue
		}

		platform := parts[0]
		account := parts[1]
		key := fmt.Sprintf("%s:%s", platform, account)

		cookiePath := filepath.Join(s.cookiesDir, entry.Name())
		nickname, uid, avatar := parseCookieMetadata(cookiePath)

		existing, exists := accountMap[key]
		if !exists {
			newAcc := AccountRecord{
				Platform:  platform,
				Account:   account,
				Nickname:  nickname,
				FinderUid: uid,
				Avatar:    avatar,
				IsValid:   true,
				Checked:   true,
				Msg:       "从本地凭据文件反向恢复",
				CheckedAt: time.Now().UnixMilli(),
			}
			accountMap[key] = newAcc
			accounts = append(accounts, newAcc)
			hasChanges = true
		} else {
			updated := false
			if existing.Nickname == "" && nickname != "" {
				existing.Nickname = nickname
				updated = true
			}
			if existing.FinderUid == "" && uid != "" {
				existing.FinderUid = uid
				updated = true
			}
			if existing.Avatar == "" && avatar != "" {
				existing.Avatar = avatar
				updated = true
			}
			if updated {
				accountMap[key] = existing
				for i, item := range accounts {
					if item.Platform == existing.Platform && item.Account == existing.Account {
						accounts[i] = existing
						break
					}
				}
				hasChanges = true
			}
		}
	}

	resultBytes, err := json.Marshal(accounts)
	if err != nil {
		return clientAccountsJSON, err
	}

	// 若检测到变化或物理 data/accounts.json 尚未存在，立即持久化
	if hasChanges || !s.driver.Exists("accounts") {
		_ = s.driver.Write("accounts", resultBytes)
	}

	return string(resultBytes), nil
}

// parseCookieMetadata 解析 cookie 文件中包含的元数据（__account_meta__ 或 profile 扩展字段）
func parseCookieMetadata(filePath string) (nickname, uid, avatar string) {
	bytes, err := os.ReadFile(filePath)
	if err != nil {
		return
	}

	var root interface{}
	if err := json.Unmarshal(bytes, &root); err != nil {
		return
	}

	extractFromMap := func(m map[string]interface{}) {
		if meta, ok := m["__account_meta__"].(map[string]interface{}); ok {
			if n, ok := meta["nickname"].(string); ok && n != "" {
				nickname = n
			}
			if u, ok := meta["finderUid"].(string); ok && u != "" {
				uid = u
			}
			if a, ok := meta["avatar"].(string); ok && a != "" {
				avatar = a
			}
		}
		if nickname == "" {
			if n, ok := m["nickname"].(string); ok && n != "" {
				nickname = n
			} else if n, ok := m["name"].(string); ok && n != "" {
				nickname = n
			}
		}
		if uid == "" {
			if u, ok := m["finderUid"].(string); ok && u != "" {
				uid = u
			} else if u, ok := m["uid"].(string); ok && u != "" {
				uid = u
			}
		}
		if avatar == "" {
			if a, ok := m["avatar"].(string); ok && a != "" {
				avatar = a
			}
		}
	}

	switch v := root.(type) {
	case map[string]interface{}:
		extractFromMap(v)
	case []interface{}:
		for _, item := range v {
			if m, ok := item.(map[string]interface{}); ok {
				if name, ok := m["name"].(string); ok && name == "__account_meta__" {
					if val, ok := m["value"].(string); ok {
						var meta map[string]interface{}
						if err := json.Unmarshal([]byte(val), &meta); err == nil {
							extractFromMap(map[string]interface{}{"__account_meta__": meta})
						}
					}
				}
			}
		}
	}

	return
}
