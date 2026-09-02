package engine

import (
	"context"
	"fmt"
	"io"
	"os/exec"
	"sync"
)

// ProcessTracker 管理运行中的子进程、并发 Context 与 Stdin 双向输入管道
type ProcessTracker struct {
	ActiveCancel context.CancelFunc
	ActiveCmds   map[*exec.Cmd]bool
	TaskCmds     map[string]*exec.Cmd       // key: platform:account 或 taskId
	TaskStdin    map[string]io.WriteCloser  // key: platform:account 或 taskId
	Mu           sync.Mutex
}

func NewProcessTracker() *ProcessTracker {
	return &ProcessTracker{
		ActiveCmds: make(map[*exec.Cmd]bool),
		TaskCmds:   make(map[string]*exec.Cmd),
		TaskStdin:  make(map[string]io.WriteCloser),
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

// RegisterTaskCmd 登记按账号颗粒度的子进程
func (pt *ProcessTracker) RegisterTaskCmd(taskKey string, cmd *exec.Cmd) {
	pt.Mu.Lock()
	defer pt.Mu.Unlock()
	pt.ActiveCmds[cmd] = true
	pt.TaskCmds[taskKey] = cmd
}

// UnregisterTaskCmd 注销按账号颗粒度的子进程
func (pt *ProcessTracker) UnregisterTaskCmd(taskKey string, cmd *exec.Cmd) {
	pt.Mu.Lock()
	defer pt.Mu.Unlock()
	delete(pt.ActiveCmds, cmd)
	delete(pt.TaskCmds, taskKey)
}

// StopSingleTask 手动中止单个特定账号的子任务 (仅杀死该进程，不影响通道后续任务及其他通道)
func (pt *ProcessTracker) StopSingleTask(platform, account string) bool {
	pt.Mu.Lock()
	defer pt.Mu.Unlock()
	taskKey := platform + ":" + account
	if cmd, ok := pt.TaskCmds[taskKey]; ok && cmd != nil && cmd.Process != nil {
		_ = cmd.Process.Kill()
		delete(pt.TaskCmds, taskKey)
		delete(pt.ActiveCmds, cmd)
		return true
	}
	return false
}

// StopTaskById 手动根据 TaskId 唯一标识精准杀死进程
func (pt *ProcessTracker) StopTaskById(taskId string) bool {
	pt.Mu.Lock()
	defer pt.Mu.Unlock()
	if cmd, ok := pt.TaskCmds[taskId]; ok && cmd != nil && cmd.Process != nil {
		_ = cmd.Process.Kill()
		delete(pt.TaskCmds, taskId)
		delete(pt.ActiveCmds, cmd)
		return true
	}
	return false
}

// StopActiveTask 手动中止当前全部正在运行的任务 (全局中止)
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

// RegisterTaskStdin 注册指定任务的 stdin 写入管道
func (pt *ProcessTracker) RegisterTaskStdin(key string, stdin io.WriteCloser) {
	pt.Mu.Lock()
	defer pt.Mu.Unlock()
	pt.TaskStdin[key] = stdin
}

// UnregisterTaskStdin 注销指定任务的 stdin 写入管道
func (pt *ProcessTracker) UnregisterTaskStdin(key string) {
	pt.Mu.Lock()
	defer pt.Mu.Unlock()
	if w, ok := pt.TaskStdin[key]; ok && w != nil {
		_ = w.Close()
	}
	delete(pt.TaskStdin, key)
}

// SendInput 向指定任务的子进程 stdin 写入反向交互 JSON 指令 (如鼠标点击、滑块拖动、按键)
func (pt *ProcessTracker) SendInput(targetId string, data []byte) error {
	pt.Mu.Lock()
	defer pt.Mu.Unlock()

	w, ok := pt.TaskStdin[targetId]
	if !ok || w == nil {
		return fmt.Errorf("stdin pipe not found for target: %s", targetId)
	}

	payload := append(data, '\n')
	_, err := w.Write(payload)
	return err
}
