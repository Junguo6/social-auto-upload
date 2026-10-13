package storage

import (
	"fmt"
	"os"
	"path/filepath"
)

// ResolveDataDir 解析可写的持久化数据主目录：
// 1. 若当前运行目录具备写权限（便携绿色免安装版），优先存放在当前目录下，保证数据便携性
// 2. 若当前运行目录不可写（如受保护的 Program Files 或 macOS /Applications），自动存放在用户配置目录 (%APPDATA%\xiaoying_sau 或 ~/Library/Application Support/xiaoying_sau)
func ResolveDataDir(workDir string) string {
	if workDir != "" && isDirWritable(workDir) {
		return filepath.Join(workDir, "data")
	}
	if userConfig, err := os.UserConfigDir(); err == nil && userConfig != "" {
		appDir := filepath.Join(userConfig, "xiaoying_sau", "data")
		_ = os.MkdirAll(appDir, 0755)
		return appDir
	}
	return filepath.Join(workDir, "data")
}

// ResolveCookiesDir 解析可写的 Cookies 目录
func ResolveCookiesDir(workDir string) string {
	if workDir != "" && isDirWritable(workDir) {
		return filepath.Join(workDir, "cookies")
	}
	if userConfig, err := os.UserConfigDir(); err == nil && userConfig != "" {
		appDir := filepath.Join(userConfig, "xiaoying_sau", "cookies")
		_ = os.MkdirAll(appDir, 0755)
		return appDir
	}
	return filepath.Join(workDir, "cookies")
}

func isDirWritable(dir string) bool {
	_ = os.MkdirAll(dir, 0755)
	testFile := filepath.Join(dir, fmt.Sprintf(".sau_perm_test_%d", os.Getpid()))
	f, err := os.OpenFile(testFile, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0666)
	if err != nil {
		return false
	}
	_ = f.Close()
	_ = os.Remove(testFile)
	return true
}

// StorageManager 统一存储门面管理器，为 Wails 上层提供持久化和业务同步能力
type StorageManager struct {
	driver      Driver
	accountSync *AccountSyncService
}

// NewStorageManager 创建存储管理器（装配 FileDriver 和 AccountSyncService）
func NewStorageManager(workDir string) *StorageManager {
	dataDir := ResolveDataDir(workDir)
	cookiesDir := ResolveCookiesDir(workDir)

	driver, _ := NewFileDriver(dataDir)
	syncService := NewAccountSyncService(cookiesDir, driver)

	return &StorageManager{
		driver:      driver,
		accountSync: syncService,
	}
}

// Driver 获取底层驱动接口（便于扩展其他仓储）
func (sm *StorageManager) Driver() Driver {
	return sm.driver
}

// LoadData 读取指定业务 key 的持久化 JSON 字符串
func (sm *StorageManager) LoadData(key string) (string, error) {
	bytes, err := sm.driver.Read(key)
	if err != nil {
		return "", err
	}
	return string(bytes), nil
}

// SaveData 原子持久化指定业务 key 的 JSON 字符串
func (sm *StorageManager) SaveData(key string, payload string) error {
	return sm.driver.Write(key, []byte(payload))
}

// DeleteData 删除指定业务 key 的数据
func (sm *StorageManager) DeleteData(key string) error {
	return sm.driver.Delete(key)
}

// SyncAccountsWithCookies 扫描本地 cookies/*.json，与前端账号列表做双向对齐与反向发现
func (sm *StorageManager) SyncAccountsWithCookies(clientAccountsJSON string) (string, error) {
	return sm.accountSync.SyncAccounts(clientAccountsJSON)
}
