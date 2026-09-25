<template>
  <el-drawer
    :model-value="modelValue"
    :title="task ? `任务日志与详情 [${task.nickname || task.account}]` : '全局引擎实时标准输出日志'"
    size="600px"
    append-to-body
    class="task-log-drawer"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div class="log-drawer-body">
      <!-- 1. 任务核心概览卡片 (若选中了单任务) -->
      <div v-if="task" class="task-summary-card">
        <div class="summary-top-row">
          <div class="summary-left">
            <span class="plat-badge" :style="{ background: getPlatformStyle(task.platform).brandColor }">
              {{ getPlatformStyle(task.platform).name }}
            </span>
            <span class="acc-title">{{ task.nickname || task.account }}</span>
            <span class="order-badge">步骤 #{{ task.orderIndex }}</span>
          </div>

          <div class="summary-right">
            <span class="status-pill" :class="task.status">
              <el-icon v-if="task.status === 'running'" class="is-loading"><Loading /></el-icon>
              <el-icon v-else-if="task.status === 'success'"><Check /></el-icon>
              <el-icon v-else-if="task.status === 'failed'"><WarningFilled /></el-icon>
              <el-icon v-else-if="task.status === 'queued'"><Clock /></el-icon>
              <span>{{ getStatusText(task.status) }}</span>
            </span>
          </div>
        </div>

        <div class="summary-work-title">
          <span class="work-action-tag">{{ task.action === 'upload-video' ? '视频' : '图文' }}</span>
          <span class="work-title-text">{{ task.title }}</span>
        </div>

        <div class="summary-meta-grid">
          <div class="meta-item">
            <span class="meta-k">批次所属:</span>
            <span class="meta-v">{{ task.batchName }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-k">创建时间:</span>
            <span class="meta-v">{{ task.createdAt }}</span>
          </div>
          <div class="meta-item" v-if="task.scheduledAt">
            <span class="meta-k">计划执行:</span>
            <span class="meta-v highlight">{{ task.scheduledAt }}</span>
          </div>
          <div class="meta-item" v-if="task.delaySeconds">
            <span class="meta-k">步骤延时:</span>
            <span class="meta-v">{{ task.delaySeconds }} 秒</span>
          </div>
          <div class="meta-item" v-if="task.duration">
            <span class="meta-k">执行耗时:</span>
            <span class="meta-v">{{ task.duration }} 秒</span>
          </div>
        </div>

        <div v-if="task.errorMsg" class="summary-error-box">
          <el-icon><WarningFilled /></el-icon>
          <span>{{ task.errorMsg }}</span>
        </div>
      </div>

      <!-- 2. 下发参数快照折叠面板 -->
      <div v-if="task && task.params" class="params-snapshot-box">
        <div class="params-header" @click="showParams = !showParams">
          <div class="params-title">
            <el-icon><Setting /></el-icon>
            <span>下发 CLI 参数快照</span>
          </div>
          <el-icon class="toggle-arrow">{{ showParams ? '▼' : '▲' }}</el-icon>
        </div>
        <div v-show="showParams" class="params-content custom-scrollbar">
          <div class="param-row" v-if="task.params.filePath">
            <span class="param-k">视频文件:</span>
            <span class="param-v">{{ task.params.filePath }}</span>
          </div>
          <div class="param-row" v-if="task.params.thumbnail">
            <span class="param-k">封面路径:</span>
            <span class="param-v">{{ task.params.thumbnail }}</span>
          </div>
          <div class="param-row" v-if="task.params.tags">
            <span class="param-k">话题标签:</span>
            <span class="param-v">{{ task.params.tags }}</span>
          </div>
          <div class="param-row" v-if="task.params.tid">
            <span class="param-k">分区 TID:</span>
            <span class="param-v">{{ task.params.tid }}</span>
          </div>
          <div class="param-row" v-if="task.params.collection">
            <span class="param-k">合集/专栏:</span>
            <span class="param-v">{{ task.params.collection }}</span>
          </div>
        </div>
      </div>

      <!-- 2.5 视图模式切换: 实时画面 vs 终端日志 -->
      <div class="view-mode-tabs">
        <el-radio-group v-model="activeTab" size="small">
          <el-radio-button label="terminal" style="display:flex;">
            <el-icon><Monitor /></el-icon>
            <span style="margin-left: 5px;">终端标准输出日志</span>
          </el-radio-button>
          <el-radio-button label="live" style="display:flex;">
            <el-icon><VideoCamera /></el-icon>
            <span style="margin-left: 5px;">实时运行画面 (CDP)</span>
          </el-radio-button>
        </el-radio-group>

        <!-- 若选中了单任务，提供单任务专属与全局流切换 -->
        <div v-if="task && activeTab === 'terminal'" class="log-scope-switch">
          <el-radio-group v-model="logScope" size="small">
            <el-radio-button label="task">聚焦本任务 ({{ task.logs.length }})</el-radio-button>
            <el-radio-button label="all">全局日志流 ({{ taskStore.globalLiveLogs.length }})</el-radio-button>
          </el-radio-group>
        </div>
      </div>

      <!-- 3. 实时运行画面视窗 (CDP Canvas) -->
      <div v-show="activeTab === 'live'" class="live-canvas-wrapper">
        <LiveBrowserCanvas 
          :taskId="task?.id"
          :title="task ? `${task.platform} - ${task.nickname || task.account} 运行监视器` : '全局浏览器监视器'"
        />
      </div>

      <!-- 4. 实时终端控制台 -->
      <div 
        v-show="activeTab === 'terminal'" 
        class="terminal-container" 
        :class="['term-theme-' + activeTerminalTheme]"
      >
        <div class="terminal-header">
          <div class="header-left">
            <el-icon><Monitor /></el-icon>
            <span class="terminal-title">
              {{ task && logScope === 'task' ? `[${task.nickname || task.account}] 专属执行日志` : '全局实时控制台日志流' }}
            </span>
            <el-tag size="small" effect="dark" round class="log-count-tag">
              {{ filteredLogs.length }} 条
            </el-tag>
          </div>

          <div class="header-right">
            <el-input 
              v-model="logSearch"
              placeholder="搜索日志..." 
              size="small" 
              clearable 
              class="terminal-search-input"
            />
            <!-- 终端明暗风格快速切换 -->
            <el-tooltip :content="activeTerminalTheme === 'dark' ? '当前为极客暗色终端，点击切换为明亮风格' : '当前为明亮控制台，点击切换为极客暗色'" placement="top">
              <el-button size="small" link class="term-tool-btn" @click="toggleTerminalTheme">
                <span v-if="activeTerminalTheme === 'dark'">🌙 暗色</span>
                <span v-else>☀️ 亮色</span>
              </el-button>
            </el-tooltip>
            <el-button size="small" type="primary" link class="term-tool-btn" @click="copyAllLogs">
              <el-icon><CopyDocument /></el-icon> 复制
            </el-button>
            <el-button size="small" type="info" link class="term-tool-btn" @click="clearCurrentLogs">
              清屏
            </el-button>
          </div>
        </div>

        <div class="terminal-body custom-scrollbar" ref="terminalBodyRef">
          <div v-if="filteredLogs.length === 0" class="empty-logs">
            <el-icon><InfoFilled /></el-icon>
            <span v-if="logSearch">未搜索到包含「{{ logSearch }}」的日志行</span>
            <span v-else-if="task && logScope === 'task'">该任务暂无独立日志输出 (卡片可能正在排队等待或尚未启动)</span>
            <span v-else>暂无实时控制台日志输出</span>
            <el-button v-if="task && logScope === 'task' && !logSearch" size="small" type="primary" plain @click="logScope = 'all'">
              切换为全局日志流
            </el-button>
          </div>
          <div 
            v-for="(log, idx) in filteredLogs" 
            :key="idx" 
            class="log-line" 
            :class="[getLogTypeClass(log), { 'is-highlighted-task': isLineForCurrentTask(log.message) }]"
          >
            <span class="log-time">{{ log.time }}</span>
            <span class="log-msg">{{ log.message }}</span>
          </div>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { getPlatformConfig } from '../../config/platforms'
import { useTaskStore } from '../../stores/taskStore'
import { useThemeStore } from '../../stores/themeStore'
import type { PublishTask, TaskLogItem } from '../../types/task'
import LiveBrowserCanvas from './LiveBrowserCanvas.vue'

const props = withDefaults(defineProps<{
  modelValue: boolean
  task: PublishTask | null
  initialTab?: string
}>(), {
  initialTab: 'terminal'
})

defineEmits<{
  (e: 'update:modelValue', val: boolean): void
}>()

const taskStore = useTaskStore()
const themeStore = useThemeStore()
const activeTab = ref(props.initialTab || 'terminal')
const logScope = ref<'task' | 'all'>('task')
const logSearch = ref('')
const showParams = ref(false)
const terminalBodyRef = ref<HTMLElement | null>(null)

// 终端明暗主题模式：默认遵循用户偏好，默认为极客暗色终端保证最高对比度
const terminalThemeMode = ref<'auto' | 'dark' | 'light'>(
  (localStorage.getItem('sau_terminal_theme_mode') as 'auto' | 'dark' | 'light') || 'dark'
)

const activeTerminalTheme = computed<'dark' | 'light'>(() => {
  if (terminalThemeMode.value === 'auto') {
    return themeStore.isDark ? 'dark' : 'light'
  }
  return terminalThemeMode.value
})

const toggleTerminalTheme = () => {
  if (activeTerminalTheme.value === 'dark') {
    terminalThemeMode.value = 'light'
  } else {
    terminalThemeMode.value = 'dark'
  }
  localStorage.setItem('sau_terminal_theme_mode', terminalThemeMode.value)
}

// 智能判定日志行色彩类型 (即使底层缺失 type 或仅为标准输出，也能精准着色)
const getLogTypeClass = (log: TaskLogItem): string => {
  if (log.type && log.type !== 'log') return log.type
  const m = (log.message || '').toLowerCase()
  if (m.includes('error') || m.includes('failed') || m.includes('fail') || m.includes('失败') || m.includes('异常') || m.includes('traceback') || m.includes('拒绝')) {
    return 'error'
  }
  if (m.includes('success') || m.includes('成功') || m.includes('published') || m.includes('完成') || m.includes('已保存')) {
    return 'success'
  }
  if (m.includes('warn') || m.includes('warning') || m.includes('警告') || m.includes('跳过') || m.includes('排队')) {
    return 'warn'
  }
  if (m.includes('info') || m.includes('正在') || m.includes('开始') || m.includes('启动') || m.includes('准备')) {
    return 'info'
  }
  return 'log'
}

watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    activeTab.value = props.initialTab || 'terminal'
    logScope.value = props.task ? 'task' : 'all'
    logSearch.value = ''
    nextTick(() => {
      if (terminalBodyRef.value) {
        terminalBodyRef.value.scrollTop = terminalBodyRef.value.scrollHeight
      }
    })
  }
})

watch(() => props.task, (newTask) => {
  logScope.value = newTask ? 'task' : 'all'
})

const getPlatformStyle = (platformId: string) => {
  return getPlatformConfig(platformId)
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'running': return '正在执行'
    case 'queued': return '排队等待'
    case 'success': return '发布成功'
    case 'failed': return '发布失败'
    case 'cancelled': return '已取消'
    default: return '未知'
  }
}

const currentLogs = computed<TaskLogItem[]>(() => {
  if (props.task && logScope.value === 'task') {
    return props.task.logs
  }
  return taskStore.globalLiveLogs
})

const filteredLogs = computed<TaskLogItem[]>(() => {
  const list = currentLogs.value
  if (!logSearch.value.trim()) return list
  const q = logSearch.value.trim().toLowerCase()
  return list.filter(l => l.message.toLowerCase().includes(q))
})

const isLineForCurrentTask = (msg: string): boolean => {
  if (!props.task || logScope.value === 'task') return false
  const p = props.task.platform.toLowerCase()
  const a = props.task.account.toLowerCase()
  const n = (props.task.nickname || '').toLowerCase()
  const m = msg.toLowerCase()
  return m.includes(p) && (m.includes(a) || (!!n && m.includes(n)))
}

const clearCurrentLogs = () => {
  if (props.task && logScope.value === 'task') {
    props.task.logs = []
  } else {
    taskStore.globalLiveLogs = []
  }
}

const copyAllLogs = () => {
  const text = filteredLogs.value.map(l => `[${l.time}] ${l.message}`).join('\n')
  navigator.clipboard.writeText(text)
  ElMessage.success('已复制日志到剪贴板')
}

// 日志自动滚动到底部
watch(() => filteredLogs.value.length, () => {
  nextTick(() => {
    if (terminalBodyRef.value) {
      terminalBodyRef.value.scrollTop = terminalBodyRef.value.scrollHeight
    }
  })
})
</script>

<style scoped>
.log-drawer-body {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 14px;
}

.task-summary-card {
  padding: 14px 16px;
  border-radius: 10px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex-shrink: 0;
}

.summary-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.summary-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.plat-badge {
  font-size: 10px;
  font-weight: 600;
  color: #fff;
  padding: 2px 6px;
  border-radius: 4px;
}

.acc-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

.order-badge {
  font-size: 10px;
  color: #818cf8;
  background: rgba(99, 102, 241, 0.12);
  padding: 1px 6px;
  border-radius: 4px;
}

.status-pill {
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-pill.running { color: #3b82f6; }
.status-pill.success { color: #10b981; }
.status-pill.failed { color: #ef4444; }
.status-pill.queued { color: #eab308; }
.status-pill.cancelled { color: #94a3b8; }

.summary-work-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.work-action-tag {
  font-size: 10px;
  color: #c084fc;
  background: rgba(168, 85, 247, 0.12);
  padding: 1px 5px;
  border-radius: 3px;
}

.work-title-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.summary-meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  font-size: 11px;
  color: var(--text-secondary);
}

.meta-k {
  color: var(--text-muted);
  margin-right: 4px;
}

.meta-v.highlight {
  color: #818cf8;
  font-weight: 600;
}

.summary-error-box {
  padding: 8px 12px;
  border-radius: 6px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.25);
  color: #f87171;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.params-snapshot-box {
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.05);
  overflow: hidden;
  flex-shrink: 0;
}

.params-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.02);
}

.params-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.toggle-arrow {
  font-size: 10px;
  color: var(--text-muted);
}

.params-content {
  padding: 10px 14px;
  max-height: 120px;
  overflow-y: auto;
  font-size: 11px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-top: 1px solid var(--border-subtle);
}

.param-row {
  display: flex;
  gap: 8px;
}

.param-k {
  color: var(--text-muted);
  width: 70px;
  flex-shrink: 0;
}

.param-v {
  color: var(--text-main);
  word-break: break-all;
}

/* 4. 实时终端控制台 (色彩独立隔离沙箱，根除亮色模式下文字变黑) */
.terminal-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-radius: 10px;
  overflow: hidden;
  transition: all 0.25s ease;
}

/* 🌙 暗黑极客终端：深邃夜幕黑底 + 高对比银白高亮字 */
.terminal-container.term-theme-dark {
  --term-bg: #090e18;
  --term-header-bg: #0e1524;
  --term-border: #1e293b;
  --term-title: #f1f5f9;
  --term-text-default: #f1f5f9;
  --term-time: #94a3b8;
  --term-empty: #64748b;
  --term-color-log: #f1f5f9;
  --term-color-info: #38bdf8;
  --term-color-success: #34d399;
  --term-color-warn: #fbbf24;
  --term-color-error: #f87171;
  --term-bg-error: rgba(239, 68, 68, 0.12);
  --term-bg-success: rgba(52, 211, 153, 0.08);
  --term-bg-warn: rgba(251, 191, 36, 0.08);
  --term-highlight-task: rgba(99, 102, 241, 0.20);
  --term-highlight-border: #818cf8;
  --term-input-bg: #141d2e;
  --term-input-text: #f8fafc;
  --term-input-border: #334155;
  --term-scrollbar-thumb: rgba(148, 163, 184, 0.25);
  background: var(--term-bg) !important;
  border: 1px solid var(--term-border);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
}

/* ☀️ 明亮纸质控制台：米灰浅白底 + 深色高对比清晰字 */
.terminal-container.term-theme-light {
  --term-bg: #f8fafc;
  --term-header-bg: #f1f5f9;
  --term-border: #e2e8f0;
  --term-title: #0f172a;
  --term-text-default: #1e293b;
  --term-time: #64748b;
  --term-empty: #94a3b8;
  --term-color-log: #0f172a;
  --term-color-info: #0284c7;
  --term-color-success: #059669;
  --term-color-warn: #d97706;
  --term-color-error: #dc2626;
  --term-bg-error: rgba(239, 68, 68, 0.09);
  --term-bg-success: rgba(16, 185, 129, 0.09);
  --term-bg-warn: rgba(245, 158, 11, 0.09);
  --term-highlight-task: rgba(99, 102, 241, 0.10);
  --term-highlight-border: #6366f1;
  --term-input-bg: #ffffff;
  --term-input-text: #0f172a;
  --term-input-border: #cbd5e1;
  --term-scrollbar-thumb: rgba(148, 163, 184, 0.4);
  background: var(--term-bg) !important;
  border: 1px solid var(--term-border);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.terminal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: var(--term-header-bg);
  border-bottom: 1px solid var(--term-border);
  font-size: 12px;
  color: var(--term-title);
  flex-shrink: 0;
}

.terminal-title {
  font-weight: 600;
  color: var(--term-title) !important;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.log-count-tag {
  background: rgba(99, 102, 241, 0.15) !important;
  color: #818cf8 !important;
  border: 1px solid rgba(99, 102, 241, 0.3) !important;
  height: 20px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.terminal-search-input {
  width: 130px;
  margin-right: 2px;
}

/* 覆盖搜索输入框，完美融入终端 */
.term-theme-dark .terminal-search-input :deep(.el-input__wrapper) {
  background-color: var(--term-input-bg) !important;
  box-shadow: 0 0 0 1px var(--term-input-border) inset !important;
}
.term-theme-dark .terminal-search-input :deep(.el-input__inner) {
  color: var(--term-input-text) !important;
}
.term-theme-dark .terminal-search-input :deep(.el-input__inner::placeholder) {
  color: var(--term-empty) !important;
}

.term-tool-btn {
  font-size: 11px !important;
  padding: 2px 6px !important;
}

.terminal-body {
  flex: 1;
  padding: 12px 14px;
  overflow-y: auto;
  font-family: 'JetBrains Mono', Consolas, 'SF Mono', monospace;
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--term-text-default) !important;
}

.terminal-body::-webkit-scrollbar-thumb {
  background: var(--term-scrollbar-thumb);
}

.empty-logs {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: var(--term-empty);
  padding-top: 60px;
}

.log-line {
  margin-bottom: 3px;
  word-break: break-all;
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--term-text-default) !important;
  transition: background-color 0.15s ease;
}

.log-line:hover {
  background: rgba(255, 255, 255, 0.04);
}
.term-theme-light .log-line:hover {
  background: rgba(0, 0, 0, 0.03);
}

.log-time {
  color: var(--term-time) !important;
  margin-right: 8px;
  font-weight: 500;
  user-select: none;
  font-variant-numeric: tabular-nums;
}

.log-msg {
  color: var(--term-text-default) !important;
}

/* 日志分类色彩高对比度渲染 */
.log-line.log .log-msg {
  color: var(--term-color-log) !important;
}
.log-line.info .log-msg {
  color: var(--term-color-info) !important;
}
.log-line.warn {
  background: var(--term-bg-warn);
}
.log-line.warn .log-msg {
  color: var(--term-color-warn) !important;
  font-weight: 600;
}
.log-line.success {
  background: var(--term-bg-success);
}
.log-line.success .log-msg {
  color: var(--term-color-success) !important;
  font-weight: 600;
}
.log-line.error {
  background: var(--term-bg-error);
}
.log-line.error .log-msg {
  color: var(--term-color-error) !important;
  font-weight: 600;
}

.log-line.is-highlighted-task {
  background: var(--term-highlight-task) !important;
  border-left: 3px solid var(--term-highlight-border) !important;
  padding-left: 8px;
}

.view-mode-tabs {
  margin: 6px 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.log-scope-switch {
  display: flex;
  align-items: center;
}

.live-canvas-wrapper {
  height: 380px;
  width: 100%;
  margin-bottom: 12px;
}
</style>
