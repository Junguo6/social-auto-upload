//go:build windows

package upgrade

import (
	"bytes"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
	"time"
	"unsafe"

	"golang.org/x/sys/windows"
)

var (
	shell32        = windows.NewLazySystemDLL("shell32.dll")
	shellExecuteW  = shell32.NewProc("ShellExecuteW")
)

// ensureUptool 检查并在缺失时下载 Windows 升级辅助工具 uptool.exe
func ensureUptool(targetDir, host string) (string, error) {
	uptoolPath := filepath.Join(targetDir, "uptool.exe")
	if _, err := os.Stat(uptoolPath); err == nil {
		return uptoolPath, nil
	}

	url := fmt.Sprintf("%s/pkg/uptool.exe", stringsTrimRight(host, "/"))
	resp, err := http.Get(url)
	if err != nil {
		return "", fmt.Errorf("下载 uptool.exe 失败: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("下载 uptool.exe 失败 (HTTP %d)", resp.StatusCode)
	}

	out, err := os.OpenFile(uptoolPath, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0755)
	if err != nil {
		return "", fmt.Errorf("创建 uptool.exe 失败: %w", err)
	}
	defer out.Close()

	if _, err := io.Copy(out, resp.Body); err != nil {
		_ = os.Remove(uptoolPath)
		return "", fmt.Errorf("写入 uptool.exe 失败: %w", err)
	}

	return uptoolPath, nil
}

func stringsTrimRight(s, cutset string) string {
	for len(s) > 0 && len(cutset) > 0 && s[len(s)-1] == cutset[0] {
		s = s[:len(s)-1]
	}
	return s
}

func joinArgs(args []string) string {
	var buf bytes.Buffer
	for i, arg := range args {
		if bytes.Contains([]byte(arg), []byte(" ")) {
			buf.WriteString(`"`)
			buf.WriteString(arg)
			buf.WriteString(`"`)
		} else {
			buf.WriteString(arg)
		}
		if i < len(args)-1 {
			buf.WriteString(" ")
		}
	}
	return buf.String()
}

func callUpgradeToolWithAdmin(exePath string, args []string) error {
	absExePath, err := filepath.Abs(exePath)
	if err != nil {
		return fmt.Errorf("获取绝对路径失败: %w", err)
	}

	if _, err := os.Stat(absExePath); os.IsNotExist(err) {
		return fmt.Errorf("文件不存在: %s", absExePath)
	}

	verbPtr, _ := windows.UTF16PtrFromString("runas")
	exePathPtr, _ := windows.UTF16PtrFromString(absExePath)
	argLine := joinArgs(args)
	argLinePtr, _ := windows.UTF16PtrFromString(argLine)
	wd := filepath.Dir(absExePath)
	wdPtr, _ := windows.UTF16PtrFromString(wd)

	ret, _, _ := shellExecuteW.Call(
		0,
		uintptr(unsafe.Pointer(verbPtr)),
		uintptr(unsafe.Pointer(exePathPtr)),
		uintptr(unsafe.Pointer(argLinePtr)),
		uintptr(unsafe.Pointer(wdPtr)),
		uintptr(windows.SW_SHOW),
	)

	if ret <= 32 {
		return fmt.Errorf("启动提权升级工具失败 (ShellExecute 返回 %d)", ret)
	}

	return nil
}

// ExecuteInstall 执行 Windows 平台升级安装
func ExecuteInstall(zipPath, currentVersion, newSN, host string) error {
	execPath, err := os.Executable()
	if err != nil {
		return fmt.Errorf("获取当前可执行文件路径失败: %w", err)
	}

	destDir := filepath.Dir(execPath)
	execName := filepath.Base(execPath)

	uptoolPath, err := ensureUptool(destDir, host)
	if err == nil {
		feedbackAPI := fmt.Sprintf("%s/jym/feedback_err", stringsTrimRight(host, "/"))
		args := []string{
			destDir,
			execName,
			newSN,
			"--version", currentVersion,
			"--api-url", feedbackAPI,
			"--app", execName,
		}

		if err := callUpgradeToolWithAdmin(uptoolPath, args); err == nil {
			return nil
		}
	}

	// 回退机制: 尝试 powershell 脚本
	batPath := filepath.Join(destDir, "upgrade.bat")
	if _, statErr := os.Stat(batPath); statErr == nil {
		cmd := exec.Command("powershell", "-Command", fmt.Sprintf("Start-Process -WindowStyle Hidden '%s' -Verb RunAs", batPath))
		cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
		return cmd.Start()
	}

	// 最终回退: 解压覆盖 (可能因文件占用需要提示重启)
	return ExtractZip(zipPath, destDir)
}
