//go:build !windows

package engine

import "os/exec"

func setupSysProcAttr(cmd *exec.Cmd) {}
