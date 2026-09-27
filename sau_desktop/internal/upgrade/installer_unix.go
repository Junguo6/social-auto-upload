//go:build !windows && !darwin

package upgrade

import (
	"fmt"
	"os"
	"path/filepath"
)

// ExecuteInstall 通用 Unix 平台升级执行
func ExecuteInstall(zipPath, currentVersion, newSN, host string) error {
	execPath, err := os.Executable()
	if err != nil {
		return fmt.Errorf("获取当前可执行文件路径失败: %w", err)
	}

	destDir := filepath.Dir(execPath)
	if err := ExtractZip(zipPath, destDir); err != nil {
		return fmt.Errorf("解压升级包失败: %w", err)
	}

	return nil
}
