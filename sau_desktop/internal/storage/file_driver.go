package storage

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sync"
)

var keySanitizer = regexp.MustCompile(`[^a-zA-Z0-9_\-]`)

// FileDriver 基于本地磁盘文件的持久化驱动实现
type FileDriver struct {
	baseDir string
	mu      sync.RWMutex
}

// NewFileDriver 创建文件存储驱动实例
func NewFileDriver(baseDir string) (*FileDriver, error) {
	if err := os.MkdirAll(baseDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create base storage directory: %w", err)
	}
	return &FileDriver{
		baseDir: baseDir,
	}, nil
}

// sanitizeKey 规范化键名，防止路径穿越攻击（例如 ../../etc/passwd）
func sanitizeKey(key string) string {
	return keySanitizer.ReplaceAllString(key, "_")
}

func (f *FileDriver) resolvePath(key string) (string, error) {
	cleanKey := sanitizeKey(key)
	if cleanKey == "" {
		return "", fmt.Errorf("invalid storage key: %s", key)
	}
	return filepath.Join(f.baseDir, cleanKey+".json"), nil
}

// Read 从磁盘读取指定键的内容
func (f *FileDriver) Read(key string) ([]byte, error) {
	f.mu.RLock()
	defer f.mu.RUnlock()

	targetPath, err := f.resolvePath(key)
	if err != nil {
		return nil, err
	}

	if _, err := os.Stat(targetPath); os.IsNotExist(err) {
		return []byte{}, nil
	}

	return os.ReadFile(targetPath)
}

// Write 将数据原子写入磁盘文件（临时文件 + os.Rename）
func (f *FileDriver) Write(key string, data []byte) error {
	f.mu.Lock()
	defer f.mu.Unlock()

	targetPath, err := f.resolvePath(key)
	if err != nil {
		return err
	}

	tmpPath := targetPath + ".tmp"
	if err := os.WriteFile(tmpPath, data, 0644); err != nil {
		return fmt.Errorf("failed to write tmp file: %w", err)
	}

	if err := os.Rename(tmpPath, targetPath); err != nil {
		_ = os.Remove(tmpPath)
		return fmt.Errorf("failed to commit storage file: %w", err)
	}

	return nil
}

// Delete 删除指定键的文件
func (f *FileDriver) Delete(key string) error {
	f.mu.Lock()
	defer f.mu.Unlock()

	targetPath, err := f.resolvePath(key)
	if err != nil {
		return err
	}

	if err := os.Remove(targetPath); err != nil && !os.IsNotExist(err) {
		return err
	}
	return nil
}

// Exists 检查文件是否存在
func (f *FileDriver) Exists(key string) bool {
	f.mu.RLock()
	defer f.mu.RUnlock()

	targetPath, err := f.resolvePath(key)
	if err != nil {
		return false
	}

	_, err = os.Stat(targetPath)
	return err == nil
}
