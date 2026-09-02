package engine

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
)

// RuntimeManager 管理 Python 虚拟环境、CLI 脚本、二进制引擎定位与内置浏览器内核
type RuntimeManager struct {
	EngineBin       string
	WorkDir         string
	UsePythonSrc    bool
	PythonBin       string
	SauCliScript    string
	BrowsersDir     string // 探测到的内置或缓存 ms-playwright 浏览器路径
	LocalChromePath string // 探测到的系统原生 Google Chrome / Edge 路径
}

// NewRuntimeManager 初始化并自动探测运行环境与内置浏览器
func NewRuntimeManager() (*RuntimeManager, error) {
	execPath, workDir, pythonBin, sauCliScript, useSrc, err := resolveEngineAndWorkDir()
	if err != nil {
		return nil, err
	}

	execDir := filepath.Dir(execPath)
	if execDir == "" || execDir == "." {
		cwd, _ := os.Getwd()
		execDir = cwd
	}

	browsersDir := resolveBrowsersDir(workDir, execDir)
	localChrome := resolveSystemChrome()

	return &RuntimeManager{
		EngineBin:       execPath,
		WorkDir:         workDir,
		UsePythonSrc:    useSrc,
		PythonBin:       pythonBin,
		SauCliScript:    sauCliScript,
		BrowsersDir:     browsersDir,
		LocalChromePath: localChrome,
	}, nil
}

func resolveEngineAndWorkDir() (string, string, string, string, bool, error) {
	dir, err := os.Getwd()
	if err != nil {
		return "", "", "", "", false, err
	}

	// 1. 定位项目根目录 (包含 conf.py 或 sau_cli.py 的目录)
	workDir := dir
	candidates := []string{
		dir,
		filepath.Join(dir, ".."),
		filepath.Join(dir, "..", ".."),
	}

	for _, c := range candidates {
		absC, _ := filepath.Abs(c)
		if _, err := os.Stat(filepath.Join(absC, "conf.py")); err == nil {
			workDir = absC
			break
		} else if _, err := os.Stat(filepath.Join(absC, "sau_cli.py")); err == nil {
			workDir = absC
			break
		}
	}

	// 2. 优先探测 Python 源码调试环境 (.venv + sau_cli.py)
	pyName := filepath.Join("bin", "python")
	if runtime.GOOS == "windows" {
		pyName = filepath.Join("Scripts", "python.exe")
	}

	venvPyCandidates := []string{
		filepath.Join(workDir, ".venv", pyName),
		filepath.Join(dir, ".venv", pyName),
		filepath.Join(dir, "..", ".venv", pyName),
	}

	sauCliPath := filepath.Join(workDir, "sau_cli.py")
	if _, err := os.Stat(sauCliPath); err == nil {
		for _, vpy := range venvPyCandidates {
			absVpy, _ := filepath.Abs(vpy)
			if _, err := os.Stat(absVpy); err == nil {
				return "", workDir, absVpy, sauCliPath, true, nil
			}
		}
	}

	// 3. 生产/无源码环境下，回退查找打包好的 sau_engine 二进制
	binName := "sau_engine"
	if runtime.GOOS == "windows" {
		binName = "sau_engine.exe"
	}

	possiblePaths := []string{
		filepath.Join(workDir, "sau_desktop", "bin", "sau_engine", binName),
		filepath.Join(workDir, "dist", "sau_engine", binName),
		filepath.Join(dir, "bin", "sau_engine", binName),
		filepath.Join(dir, "sau_desktop", "bin", "sau_engine", binName),
		filepath.Join(dir, "..", "dist", "sau_engine", binName),
		filepath.Join(dir, binName),
	}

	var foundBin string
	for _, p := range possiblePaths {
		absP, _ := filepath.Abs(p)
		if _, err := os.Stat(absP); err == nil {
			foundBin = absP
			break
		}
	}

	if foundBin == "" {
		return "", "", "", "", false, fmt.Errorf("sau_engine 可执行二进制或 Python 源码环境未找到，查找路径包括: %v", possiblePaths)
	}

	return foundBin, workDir, "", "", false, nil
}

// ResolveToAbsPath 将相对路径安全转换为绝对路径
func ResolveToAbsPath(workDir, rawPath string) string {
	if rawPath == "" {
		return ""
	}
	if filepath.IsAbs(rawPath) {
		return rawPath
	}
	target1 := filepath.Join(workDir, rawPath)
	if _, err := os.Stat(target1); err == nil {
		return target1
	}
	cwd, _ := os.Getwd()
	target2 := filepath.Join(cwd, rawPath)
	if _, err := os.Stat(target2); err == nil {
		return target2
	}
	return target1
}

// BuildCommand 构造跨平台命令执行实例与 UTF-8 环境变量
func (r *RuntimeManager) BuildCommand(ctx context.Context, args ...string) *exec.Cmd {
	var cmd *exec.Cmd
	if r.UsePythonSrc {
		fullArgs := append([]string{r.SauCliScript}, args...)
		if ctx != nil {
			cmd = exec.CommandContext(ctx, r.PythonBin, fullArgs...)
		} else {
			cmd = exec.Command(r.PythonBin, fullArgs...)
		}
	} else {
		if ctx != nil {
			cmd = exec.CommandContext(ctx, r.EngineBin, args...)
		} else {
			cmd = exec.Command(r.EngineBin, args...)
		}
	}
	cmd.Dir = r.WorkDir

	envs := os.Environ()
	envs = append(envs,
		"PYTHONIOENCODING=utf-8",
		"PYTHONUTF8=1",
		"LANG=en_US.UTF-8",
		"LC_ALL=en_US.UTF-8",
	)

	// 注入内置浏览器内核环境变量，确保脱离终端亦可开箱即用
	if r.BrowsersDir != "" {
		envs = append(envs, fmt.Sprintf("PLAYWRIGHT_BROWSERS_PATH=%s", r.BrowsersDir))
	}
	if r.LocalChromePath != "" {
		envs = append(envs, fmt.Sprintf("LOCAL_CHROME_PATH=%s", r.LocalChromePath))
	}

	cmd.Env = envs
	return cmd
}

// BrowserEnvironmentInfo 浏览器环境诊断信息结构体
type BrowserEnvironmentInfo struct {
	IsReady     bool   `json:"isReady"`
	BrowserType string `json:"browserType"` // bundled_chromium, system_chrome, none
	Path        string `json:"path"`
	Summary     string `json:"summary"`
}

// DetectBrowserStatus 诊断当前环境是否已具备自动化浏览器内核
func (r *RuntimeManager) DetectBrowserStatus() BrowserEnvironmentInfo {
	if r.BrowsersDir != "" {
		return BrowserEnvironmentInfo{
			IsReady:     true,
			BrowserType: "bundled_chromium",
			Path:        r.BrowsersDir,
			Summary:     fmt.Sprintf("已就绪 (内置/缓存 Chromium: %s)", filepath.Base(r.BrowsersDir)),
		}
	}
	if r.LocalChromePath != "" {
		return BrowserEnvironmentInfo{
			IsReady:     true,
			BrowserType: "system_chrome",
			Path:        r.LocalChromePath,
			Summary:     fmt.Sprintf("已就绪 (复用系统原生浏览器: %s)", filepath.Base(r.LocalChromePath)),
		}
	}
	return BrowserEnvironmentInfo{
		IsReady:     false,
		BrowserType: "none",
		Path:        "",
		Summary:     "未检测到浏览器内核或系统 Chrome，请在设置中一键下载或安装 Google Chrome",
	}
}

// resolveBrowsersDir 智能探测内置或系统的 ms-playwright 浏览器目录
func resolveBrowsersDir(workDir, execDir string) string {
	candidates := []string{
		// 1. 本地工作区/程序同级目录 (开箱即用绿色内置)
		filepath.Join(workDir, "ms-playwright"),
		filepath.Join(workDir, "bin", "ms-playwright"),
		filepath.Join(workDir, "sau_desktop", "bin", "ms-playwright"),
		filepath.Join(execDir, "ms-playwright"),
		filepath.Join(execDir, "..", "Resources", "ms-playwright"), // macOS .app
		filepath.Join(execDir, "..", "ms-playwright"),
	}

	// 2. 操作系统全局缓存目录 (Playwright 标准位置)
	homeDir, _ := os.UserHomeDir()
	if runtime.GOOS == "windows" {
		localApp := os.Getenv("LOCALAPPDATA")
		if localApp != "" {
			candidates = append(candidates, filepath.Join(localApp, "ms-playwright"))
		}
	} else if runtime.GOOS == "darwin" && homeDir != "" {
		candidates = append(candidates, filepath.Join(homeDir, "Library", "Caches", "ms-playwright"))
	} else if homeDir != "" {
		candidates = append(candidates, filepath.Join(homeDir, ".cache", "ms-playwright"))
	}

	for _, cand := range candidates {
		if cand == "" {
			continue
		}
		if fi, err := os.Stat(cand); err == nil && fi.IsDir() {
			// 检查是否含有 chromium-* 子目录
			entries, _ := os.ReadDir(cand)
			for _, e := range entries {
				if e.IsDir() && strings.HasPrefix(e.Name(), "chromium-") {
					absPath, _ := filepath.Abs(cand)
					return absPath
				}
			}
		}
	}
	return ""
}

// resolveSystemChrome 探测系统原生安装的 Google Chrome 或 Microsoft Edge
func resolveSystemChrome() string {
	var candidates []string
	if runtime.GOOS == "darwin" {
		candidates = []string{
			"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
			"/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
		}
	} else if runtime.GOOS == "windows" {
		candidates = []string{
			`C:\Program Files\Google\Chrome\Application\chrome.exe`,
			`C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`,
			filepath.Join(os.Getenv("LOCALAPPDATA"), `Google\Chrome\Application\chrome.exe`),
			`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`,
			`C:\Program Files\Microsoft\Edge\Application\msedge.exe`,
		}
	} else {
		candidates = []string{
			"/usr/bin/google-chrome",
			"/usr/bin/chromium-browser",
			"/usr/bin/chromium",
		}
	}

	for _, p := range candidates {
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}
	return ""
}
