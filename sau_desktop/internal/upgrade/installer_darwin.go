//go:build darwin

package upgrade

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// ExecuteInstall macOS 平台升级执行
func ExecuteInstall(zipPath, currentVersion, newSN, host string) error {
	execPath, err := os.Executable()
	if err != nil {
		return fmt.Errorf("获取当前可执行文件路径失败: %w", err)
	}

	destDir := filepath.Dir(execPath)
	appBundle := ""
	if strings.Contains(execPath, ".app/Contents/MacOS") {
		appBundle = strings.Split(execPath, ".app/Contents/MacOS")[0] + ".app"
		destDir = filepath.Dir(appBundle)
	}

	// 解压升级包
	if err := ExtractZip(zipPath, destDir); err != nil {
		return fmt.Errorf("解压升级包失败: %w", err)
	}

	// 重新拉起应用
	if appBundle != "" {
		_ = exec.Command("open", "-n", appBundle).Start()
	}

	return nil
}
