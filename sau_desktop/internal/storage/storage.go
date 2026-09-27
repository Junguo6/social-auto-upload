package storage

import (
	"path/filepath"
)

// StorageManager 统一存储门面管理器，为 Wails 上层提供持久化和业务同步能力
type StorageManager struct {
	driver      Driver
	accountSync *AccountSyncService
}

// NewStorageManager 创建存储管理器（装配 FileDriver 和 AccountSyncService）
func NewStorageManager(workDir string) *StorageManager {
	dataDir := filepath.Join(workDir, "data")
	cookiesDir := filepath.Join(workDir, "cookies")

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
