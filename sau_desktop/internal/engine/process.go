package engine

import (
	"context"
	"os/exec"
	"sync"
)

// ProcessTracker 管理运行中的子进程与并发 Context
type ProcessTracker struct {
	ActiveCancel context.CancelFunc
	ActiveCmds   map[*exec.Cmd]bool
	Mu           sync.Mutex
}

func NewProcessTracker() *ProcessTracker {
	return &ProcessTracker{
		ActiveCmds: make(map[*exec.Cmd]bool),
	}
}

// SetCancelFunc 设置当前批处理的取消函数
func (pt *ProcessTracker) SetCancelFunc(cancel context.CancelFunc) {
	pt.Mu.Lock()
	defer pt.Mu.Unlock()
	pt.ActiveCancel = cancel
}

// ClearCancelFunc 清除取消函数
func (pt *ProcessTracker) ClearCancelFunc() {
	pt.Mu.Lock()
	defer pt.Mu.Unlock()
	pt.ActiveCancel = nil
}

// RegisterCmd 登记正在运行的子进程
func (pt *ProcessTracker) RegisterCmd(cmd *exec.Cmd) {
	pt.Mu.Lock()
	defer pt.Mu.Unlock()
	pt.ActiveCmds[cmd] = true
}

// UnregisterCmd 注销已结束的子进程
func (pt *ProcessTracker) UnregisterCmd(cmd *exec.Cmd) {
	pt.Mu.Lock()
	defer pt.Mu.Unlock()
	delete(pt.ActiveCmds, cmd)
}

// StopActiveTask 手动中止当前全部正在运行的任务
func (pt *ProcessTracker) StopActiveTask() bool {
	pt.Mu.Lock()
	defer pt.Mu.Unlock()
	if pt.ActiveCancel != nil {
		pt.ActiveCancel()
		pt.ActiveCancel = nil
		return true
	}
	return false
}
