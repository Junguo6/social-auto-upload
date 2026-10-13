//go:build windows

package upgrade

import (
	"archive/zip"
	"bytes"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
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
		clean := arg
		if bytes.Contains([]byte(clean), []byte(" ")) {
			// Windows 命令行边界防护: 若路径以 \ 结尾，加引号后 \" 会被系统识别为转义引号导致参数解析错乱
			if strings.HasSuffix(clean, "\\") && !strings.HasSuffix(clean, "\\\\") {
				clean = clean + "\\"
			}
			buf.WriteString(`"`)
			buf.WriteString(clean)
			buf.WriteString(`"`)
		} else {
			buf.WriteString(clean)
		}
		if i < len(args)-1 {
			buf.WriteString(" ")
		}
	}
	return buf.String()
}

// isDirWritable 检测目标目录是否对当前进程具备写入权限
func isDirWritable(dir string) bool {
	testFile := filepath.Join(dir, fmt.Sprintf(".sau_perm_test_%d", os.Getpid()))
	f, err := os.OpenFile(testFile, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0666)
	if err != nil {
		return false
	}
	_ = f.Close()
	_ = os.Remove(testFile)
	return true
}

func callUpgradeTool(exePath string, args []string, forceAdmin bool) error {
	absExePath, err := filepath.Abs(exePath)
	if err != nil {
		return fmt.Errorf("获取绝对路径失败: %w", err)
	}

	if _, err := os.Stat(absExePath); os.IsNotExist(err) {
		return fmt.Errorf("文件不存在: %s", absExePath)
	}

	verb := "open"
	if forceAdmin {
		verb = "runas"
	}

	verbPtr, _ := windows.UTF16PtrFromString(verb)
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
		uintptr(windows.SW_SHOWNORMAL),
	)

	// 若普通权限启动受阻且未强制提权，尝试 runas 提权启动
	if ret <= 32 && !forceAdmin {
		return callUpgradeTool(exePath, args, true)
	}

	if ret <= 32 {
		return fmt.Errorf("启动升级工具失败 (ShellExecute %s 返回 %d)", verb, ret)
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

	// 清理之前遗留的历史临时更名文件
	_ = os.Remove(filepath.Join(destDir, "updater.exe.old"))
	_ = os.Remove(filepath.Join(destDir, "updater.exe.new"))

	// 1. 优先调用自研专属升级工具 updater.exe
	localUpdater := filepath.Join(destDir, "updater.exe")
	if _, statErr := os.Stat(localUpdater); os.IsNotExist(statErr) {
		// 若安装目录不可写 (如 Program Files)，优先释放到临时目录执行
		tempDir := filepath.Join(os.TempDir(), "sau_upgrade_tool")
		_ = os.MkdirAll(tempDir, 0755)
		if extErr := extractSingleFileFromZip(zipPath, "updater.exe", tempDir); extErr == nil {
			localUpdater = filepath.Join(tempDir, "updater.exe")
		} else {
			_ = extractSingleFileFromZip(zipPath, "updater.exe", destDir)
		}
	}

	if _, statErr := os.Stat(localUpdater); statErr == nil {
		args := []string{
			"--target-dir", destDir,
			"--exec-name", execName,
			"--zip-file", zipPath,
			"--pid", fmt.Sprintf("%d", os.Getpid()),
			"--auto-restart=true",
		}

		// 智能判断提权需求：如果目录可写（如绿色版），无需弹出 UAC 提权窗口，亦可保留 Windows 原生拖拽能力
		needAdmin := !isDirWritable(destDir)
		if err := callUpgradeTool(localUpdater, args, needAdmin); err == nil {
			return nil
		}
	}

	// 2. 次选兼容小映升级工具 uptool.exe
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

		if err := callUpgradeTool(uptoolPath, args, true); err == nil {
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

// extractSingleFileFromZip 从 zip 压缩包中提取指定文件到目标目录
func extractSingleFileFromZip(zipPath, targetFileName, destDir string) error {
	r, err := zip.OpenReader(zipPath)
	if err != nil {
		return err
	}
	defer r.Close()

	for _, f := range r.File {
		if filepath.Base(f.Name) == targetFileName && !f.FileInfo().IsDir() {
			rc, err := f.Open()
			if err != nil {
				return err
			}
			defer rc.Close()

			targetPath := filepath.Join(destDir, targetFileName)
			out, err := os.OpenFile(targetPath, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, f.Mode())
			if err != nil {
				return err
			}
			defer out.Close()

			_, err = io.Copy(out, rc)
			return err
		}
	}
	return fmt.Errorf("升级包中未找到 %s", targetFileName)
}
