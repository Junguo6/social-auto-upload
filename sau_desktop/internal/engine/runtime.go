package engine

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
)

// RuntimeManager 管理 Python 虚拟环境、CLI 脚本与二进制引擎定位
type RuntimeManager struct {
	EngineBin    string
	WorkDir      string
	UsePythonSrc bool
	PythonBin    string
	SauCliScript string
}

// NewRuntimeManager 初始化并自动探测运行环境
func NewRuntimeManager() (*RuntimeManager, error) {
	execPath, workDir, pythonBin, sauCliScript, useSrc, err := resolveEngineAndWorkDir()
	if err != nil {
		return nil, err
	}
	return &RuntimeManager{
		EngineBin:    execPath,
		WorkDir:      workDir,
		UsePythonSrc: useSrc,
		PythonBin:    pythonBin,
		SauCliScript: sauCliScript,
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
	cmd.Env = envs
	return cmd
}
