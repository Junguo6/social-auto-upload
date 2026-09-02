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
          <el-radio-button label="live">
            <el-icon><VideoCamera /></el-icon>
            <span>📺 实时运行画面 (CDP)</span>
          </el-radio-button>
          <el-radio-button label="terminal">
            <el-icon><Monitor /></el-icon>
            <span>📄 终端标准输出日志</span>
          </el-radio-button>
        </el-radio-group>
      </div>

      <!-- 3. 实时运行画面视窗 (CDP Canvas) -->
      <div v-show="activeTab === 'live'" class="live-canvas-wrapper">
        <LiveBrowserCanvas 
          :taskId="task?.id"
          :title="task ? `${task.platform} - ${task.nickname || task.account} 运行监视器` : '全局浏览器监视器'"
        />
      </div>

      <!-- 4. 实时终端控制台 -->
      <div v-show="activeTab === 'terminal'" class="terminal-container">
        <div class="terminal-header">
          <div class="header-left">
            <el-icon><Monitor /></el-icon>
            <span>{{ task ? '当前任务执行日志流' : '全局引擎实时标准输出流' }}</span>
            <el-tag size="small" effect="dark" round class="log-count-tag">
              {{ currentLogs.length }} 条
            </el-tag>
          </div>

          <div class="header-right">
            <el-button size="small" type="primary" link @click="copyAllLogs">
              <el-icon><CopyDocument /></el-icon> 复制日志
            </el-button>
            <el-button size="small" type="info" link @click="clearCurrentLogs">
              清屏
            </el-button>
          </div>
        </div>

        <div class="terminal-body custom-scrollbar" ref="terminalBodyRef">
          <div v-if="currentLogs.length === 0" class="empty-logs">
            <el-icon><InfoFilled /></el-icon>
            <span>暂无日志输出</span>
          </div>
          <div v-for="(log, idx) in currentLogs" :key="idx" class="log-line" :class="log.type">
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
import type { PublishTask, TaskLogItem } from '../../types/task'
import LiveBrowserCanvas from './LiveBrowserCanvas.vue'

const props = defineProps<{
  modelValue: boolean
  task: PublishTask | null
}>()

defineEmits<{
  (e: 'update:modelValue', val: boolean): void
}>()

const taskStore = useTaskStore()
const activeTab = ref('live')
const showParams = ref(false)
const terminalBodyRef = ref<HTMLElement | null>(null)

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
  if (props.task) {
    return props.task.logs.length > 0 ? props.task.logs : taskStore.globalLiveLogs
  }
  return taskStore.globalLiveLogs
})

const clearCurrentLogs = () => {
  if (props.task) {
    props.task.logs = []
  } else {
    taskStore.globalLiveLogs = []
  }
}

const copyAllLogs = () => {
  const text = currentLogs.value.map(l => `[${l.time}] ${l.message}`).join('\n')
  navigator.clipboard.writeText(text)
  ElMessage.success('已复制日志到剪贴板')
}

// 日志自动滚动到底部
watch(() => currentLogs.value.length, () => {
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

.terminal-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-radius: 10px;
  border: 1px solid var(--border-subtle);
  background: #090d16;
  overflow: hidden;
}

.terminal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 12px;
  color: #94a3b8;
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

.terminal-body {
  flex: 1;
  padding: 12px 14px;
  overflow-y: auto;
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 11px;
  line-height: 1.55;
}

.empty-logs {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: #475569;
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

.view-mode-tabs {
  margin: 10px 0 6px 0;
  display: flex;
  justify-content: center;
}

.live-canvas-wrapper {
  height: 380px;
  width: 100%;
  margin-bottom: 12px;
}

.log-line.error .log-msg { color: #f87171; }
.log-line.success .log-msg { color: #34d399; }
.log-line.log .log-msg { color: #cbd5e1; }
.log-line.warn .log-msg { color: #fbbf24; }
</style>
