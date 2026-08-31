<template>
  <div class="task-center-workspace">
    <!-- 1. 顶部数据卡片概览与快捷操作栏 -->
    <div class="task-stats-bar glass-card">
      <div class="stats-group">
        <div class="stat-card" :class="{ active: currentTab === 'all' }" @click="currentTab = 'all'">
          <div class="stat-num">{{ taskStore.tasks.length }}</div>
          <div class="stat-label">全部任务</div>
        </div>
        <div class="stat-card running-card" :class="{ active: currentTab === 'running' }" @click="currentTab = 'running'">
          <div class="stat-num">{{ taskStore.runningTasksCount }}</div>
          <div class="stat-label">执行中</div>
        </div>
        <div class="stat-card queued-card" :class="{ active: currentTab === 'queued' }" @click="currentTab = 'queued'">
          <div class="stat-num">{{ taskStore.queuedTasksCount }}</div>
          <div class="stat-label">等待排队</div>
        </div>
        <div class="stat-card success-card" :class="{ active: currentTab === 'success' }" @click="currentTab = 'success'">
          <div class="stat-num">{{ taskStore.successTasksCount }}</div>
          <div class="stat-label">已成功</div>
        </div>
        <div class="stat-card failed-card" :class="{ active: currentTab === 'failed' }" @click="currentTab = 'failed'">
          <div class="stat-num">{{ taskStore.failedTasksCount }}</div>
          <div class="stat-label">失败/异常</div>
        </div>
      </div>

      <div class="stats-actions">
        <el-button 
          v-if="taskStore.runningTasksCount > 0" 
          type="danger" 
          size="small" 
          plain 
          @click="taskStore.cancelActiveTask()"
        >
          <el-icon><CircleClose /></el-icon> 停止当前任务
        </el-button>
        <el-button size="small" plain @click="taskStore.clearFinishedTasks">
          <el-icon><Delete /></el-icon> 清理已完成
        </el-button>
        <el-button size="small" type="info" link @click="taskStore.clearAllTasks">
          清空全部记录
        </el-button>
      </div>
    </div>

    <!-- 2. 主体筛选与任务列表 -->
    <div class="task-content-layout">
      <!-- 左侧 / 上侧：任务列表 -->
      <div class="task-list-panel glass-card">
        <!-- 搜索与筛选工具栏 -->
        <div class="panel-toolbar">
          <div class="filter-left">
            <el-radio-group v-model="currentTab" size="small">
              <el-radio-button value="all">全部 ({{ taskStore.tasks.length }})</el-radio-button>
              <el-radio-button value="running">执行中 ({{ taskStore.runningTasksCount }})</el-radio-button>
              <el-radio-button value="queued">排队中 ({{ taskStore.queuedTasksCount }})</el-radio-button>
              <el-radio-button value="success">已成功 ({{ taskStore.successTasksCount }})</el-radio-button>
              <el-radio-button value="failed">失败/中止 ({{ taskStore.failedTasksCount }})</el-radio-button>
            </el-radio-group>
          </div>

          <div class="filter-right">
            <el-input 
              v-model="searchKeyword" 
              placeholder="搜索任务标题、平台或账号..." 
              prefix-icon="Search"
              size="small"
              clearable
              style="width: 220px"
            />
          </div>
        </div>

        <!-- 任务卡片列表 -->
        <div class="tasks-scroll-container custom-scrollbar">
          <div 
            v-for="task in filteredTasks" 
            :key="task.id"
            class="task-item-card"
            :class="[task.status, { selected: activeInspectTask?.id === task.id }]"
            @click="activeInspectTask = task"
          >
            <div class="item-header">
              <div class="item-header-left">
                <span class="platform-badge" :style="{ background: getPlatformStyle(task.platform).brandColor }">
                  {{ getPlatformStyle(task.platform).name }}
                </span>
                <span class="account-name" :title="task.nickname || task.account">
                  {{ task.nickname || task.account }}
                </span>
                <span class="priority-tag" :class="task.priority" v-if="task.priority !== 'normal'">
                  {{ task.priority === 'high' ? '高优先级' : '低优先级' }}
                </span>
              </div>

              <div class="item-header-right">
                <span class="status-indicator-tag" :class="task.status">
                  <el-icon v-if="task.status === 'running'" class="is-loading"><Loading /></el-icon>
                  <el-icon v-else-if="task.status === 'success'"><Check /></el-icon>
                  <el-icon v-else-if="task.status === 'failed'"><WarningFilled /></el-icon>
                  <el-icon v-else-if="task.status === 'queued'"><Clock /></el-icon>
                  <el-icon v-else><Remove /></el-icon>
                  <span>{{ getStatusText(task.status) }}</span>
                </span>
              </div>
            </div>

            <!-- 任务核心内容与作品标题 -->
            <div class="item-body">
              <div class="task-title-row">
                <span class="action-tag">{{ task.action === 'upload-video' ? '视频' : '图文' }}</span>
                <span class="task-title" :title="task.title">{{ task.title }}</span>
              </div>
              <div v-if="task.errorMsg" class="task-error-text">
                <el-icon><WarningFilled /></el-icon> {{ task.errorMsg }}
              </div>
            </div>

            <!-- 底部元信息与操作按钮 -->
            <div class="item-footer">
              <div class="footer-meta">
                <span class="meta-time">创建: {{ task.createdAt }}</span>
                <span v-if="task.duration" class="meta-duration">耗时: {{ task.duration }}s</span>
                <span class="meta-logs-count" v-if="task.logs.length > 0">
                  {{ task.logs.length }} 条执行日志
                </span>
              </div>

              <div class="footer-actions" @click.stop>
                <el-button 
                  v-if="task.status === 'failed' || task.status === 'cancelled'" 
                  size="small" 
                  type="primary" 
                  link 
                  @click="taskStore.retryTask(task.id)"
                >
                  <el-icon><RefreshRight /></el-icon> 重试
                </el-button>

                <el-button 
                  v-if="task.status === 'running' || task.status === 'queued'" 
                  size="small" 
                  type="danger" 
                  link 
                  @click="taskStore.cancelActiveTask(task.id)"
                >
                  <el-icon><CircleClose /></el-icon> 取消
                </el-button>

                <el-dropdown trigger="click" @command="(cmd: string) => handlePriorityCommand(task.id, cmd)">
                  <el-button size="small" type="info" link>
                    <el-icon><MoreFilled /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="high">设为高优先级</el-dropdown-item>
                      <el-dropdown-item command="normal">设为普通优先级</el-dropdown-item>
                      <el-dropdown-item command="low">设为低优先级</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </div>

          <div v-if="filteredTasks.length === 0" class="empty-task-placeholder">
            <el-icon class="empty-icon"><Document /></el-icon>
            <div class="empty-text">当前筛选条件下暂无任务</div>
            <div class="empty-sub">前往发布中心创建发布内容，系统将自动加入执行队列</div>
          </div>
        </div>
      </div>

      <!-- 右侧：实时日志与选中任务详情 -->
      <div class="task-detail-panel glass-card">
        <div class="detail-header">
          <div class="detail-title">
            <el-icon><Monitor /></el-icon>
            <span>{{ activeInspectTask ? `任务执行详情 [${activeInspectTask.nickname || activeInspectTask.account}]` : '引擎实时标准输出日志' }}</span>
          </div>
          <div class="detail-header-actions">
            <el-button v-if="activeInspectTask" size="small" link type="primary" @click="activeInspectTask = null">
              查看全局日志流
            </el-button>
            <el-button size="small" link type="info" @click="clearLogs">
              清屏
            </el-button>
          </div>
        </div>

        <!-- 终端日志流展示 -->
        <div class="terminal-body custom-scrollbar" ref="terminalRef">
          <div v-if="displayedLogs.length === 0" class="empty-terminal">
            <span>暂无运行日志输出</span>
          </div>
          <div v-for="(log, idx) in displayedLogs" :key="idx" class="log-line" :class="log.type">
            <span class="log-time">{{ log.time }}</span>
            <span class="log-msg">{{ log.message }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getPlatformConfig } from '../config/platforms'
import { useTaskStore } from '../stores/taskStore'
import type { PublishTask, TaskPriority, TaskStatus } from '../types/task'

const taskStore = useTaskStore()

const currentTab = ref<string>('all')
const searchKeyword = ref('')
const activeInspectTask = ref<PublishTask | null>(null)
const terminalRef = ref<HTMLElement | null>(null)

const getPlatformStyle = (platformId: string) => {
  return getPlatformConfig(platformId)
}

const getStatusText = (status: TaskStatus) => {
  switch (status) {
    case 'running': return '执行中'
    case 'queued': return '排队中'
    case 'success': return '发布成功'
    case 'failed': return '发布失败'
    case 'cancelled': return '已取消'
    default: return '未知'
  }
}

const filteredTasks = computed(() => {
  return taskStore.tasks.filter(t => {
    if (currentTab.value !== 'all' && t.status !== currentTab.value) {
      return false
    }
    if (searchKeyword.value) {
      const kw = searchKeyword.value.toLowerCase()
      const matchTitle = t.title.toLowerCase().includes(kw)
      const matchPlat = t.platform.toLowerCase().includes(kw)
      const matchAcc = t.account.toLowerCase().includes(kw)
      const matchNick = t.nickname ? t.nickname.toLowerCase().includes(kw) : false
      return matchTitle || matchPlat || matchAcc || matchNick
    }
    return true
  })
})

const displayedLogs = computed(() => {
  if (activeInspectTask.value) {
    return activeInspectTask.value.logs.length > 0 
      ? activeInspectTask.value.logs 
      : taskStore.globalLiveLogs
  }
  return taskStore.globalLiveLogs
})

const handlePriorityCommand = (taskId: string, priority: string) => {
  taskStore.changePriority(taskId, priority as TaskPriority)
  ElMessage.success(`已更新任务优先级为 ${priority}`)
}

const clearLogs = () => {
  if (activeInspectTask.value) {
    activeInspectTask.value.logs = []
  } else {
    taskStore.globalLiveLogs = []
  }
}

// 自动滚动日志终端
watch(() => displayedLogs.value.length, () => {
  nextTick(() => {
    if (terminalRef.value) {
      terminalRef.value.scrollTop = terminalRef.value.scrollHeight
    }
  })
})
</script>

<style scoped>
.task-center-workspace {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 84px);
  gap: 12px;
  overflow: hidden;
  box-sizing: border-box;
}

.task-stats-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 18px;
  border-radius: 10px;
  flex-shrink: 0;
  border: 1px solid var(--border-subtle);
  background: var(--bg-card);
}

.stats-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 6px 14px;
  border-radius: 8px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: all 0.15s ease;
  min-width: 68px;
}

.stat-card:hover {
  border-color: var(--border-highlight);
}

.stat-card.active {
  background: rgba(99, 102, 241, 0.15);
  border-color: var(--primary-light);
}

.stat-num {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
  line-height: 1.2;
}

.stat-label {
  font-size: 10px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.running-card.active .stat-num { color: #3b82f6; }
.queued-card.active .stat-num { color: #eab308; }
.success-card.active .stat-num { color: #10b981; }
.failed-card.active .stat-num { color: #ef4444; }

.stats-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-content-layout {
  display: grid;
  grid-template-columns: minmax(460px, 1.2fr) minmax(420px, 1fr);
  gap: 12px;
  flex: 1;
  min-height: 0;
}

.task-list-panel {
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-card);
  overflow: hidden;
  min-width: 0;
}

.panel-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-subtle);
  background: rgba(0, 0, 0, 0.05);
  flex-shrink: 0;
}

.tasks-scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-item-card {
  padding: 10px 14px;
  border-radius: 8px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.task-item-card:hover {
  border-color: var(--border-highlight);
  background: rgba(255, 255, 255, 0.03);
}

.task-item-card.selected {
  border-color: var(--primary-light);
  background: rgba(99, 102, 241, 0.08);
}

.task-item-card.running {
  border-left: 3px solid #3b82f6;
}

.task-item-card.success {
  border-left: 3px solid #10b981;
}

.task-item-card.failed {
  border-left: 3px solid #ef4444;
}

.item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.item-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.platform-badge {
  font-size: 10px;
  font-weight: 600;
  color: #fff;
  padding: 1px 6px;
  border-radius: 3px;
}

.account-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
}

.priority-tag {
  font-size: 9px;
  padding: 1px 4px;
  border-radius: 2px;
}

.priority-tag.high {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.priority-tag.low {
  background: rgba(148, 163, 184, 0.15);
  color: #94a3b8;
}

.status-indicator-tag {
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-indicator-tag.running { color: #3b82f6; }
.status-indicator-tag.success { color: #10b981; }
.status-indicator-tag.failed { color: #ef4444; }
.status-indicator-tag.queued { color: #eab308; }
.status-indicator-tag.cancelled { color: #94a3b8; }

.task-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.action-tag {
  font-size: 9px;
  color: #818cf8;
  background: rgba(99, 102, 241, 0.12);
  padding: 1px 4px;
  border-radius: 2px;
}

.task-title {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-error-text {
  font-size: 11px;
  color: #ef4444;
  display: flex;
  align-items: center;
  gap: 4px;
}

.item-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 10px;
  color: var(--text-muted);
  border-top: 1px solid rgba(255, 255, 255, 0.04);
  padding-top: 5px;
}

.footer-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.footer-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.empty-task-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 36px;
  margin-bottom: 8px;
  opacity: 0.4;
}

.empty-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.empty-sub {
  font-size: 11px;
  margin-top: 4px;
}

.task-detail-panel {
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-card);
  overflow: hidden;
  min-width: 0;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-subtle);
  background: rgba(0, 0, 0, 0.05);
}

.detail-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 6px;
}

.detail-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.terminal-body {
  flex: 1;
  padding: 10px 14px;
  overflow-y: auto;
  background: #090d16;
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 11px;
  line-height: 1.5;
}

.empty-terminal {
  color: #475569;
  text-align: center;
  padding-top: 60px;
}

.log-line {
  margin-bottom: 2px;
  word-break: break-all;
}

.log-time {
  color: #64748b;
  margin-right: 8px;
}

.log-line.error .log-msg { color: #f87171; }
.log-line.success .log-msg { color: #34d399; }
.log-line.log .log-msg { color: #cbd5e1; }
.log-line.warn .log-msg { color: #fbbf24; }
</style>
