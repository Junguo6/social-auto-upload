<template>
  <el-drawer
    :model-value="modelValue"
    title="矩阵并发发布调度监视器"
    size="560px"
    :close-on-click-modal="false"
    append-to-body
    class="exec-monitor-drawer"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div class="exec-drawer-content">
      <!-- 账号进度卡片群 -->
      <div class="exec-account-cards custom-scrollbar">
        <div 
          v-for="task in preparedTasks" 
          :key="`${task.platform}:${task.account}`"
          class="exec-card"
          :class="batchAccountStates[`${task.platform}:${task.account}`] || 'pending'"
        >
          <div class="exec-card-top">
            <span class="plat-tag-badge" :style="{ background: getPlatformStyle(task.platform).brandColor }">
              {{ getPlatformStyle(task.platform).name }}
            </span>
            <span class="exec-acc-name">{{ task.nickname || task.account }}</span>
            <span class="exec-status-badge">
              {{ getStatusText(batchAccountStates[`${task.platform}:${task.account}`]) }}
            </span>
          </div>
          <div class="exec-card-title">
            <span class="title-tag">下发标题:</span> {{ task.title }}
          </div>
        </div>
      </div>

      <!-- 实时终端日志流 -->
      <div class="exec-log-box">
        <div class="log-header">
          <span class="log-title"><el-icon><Monitor /></el-icon> 引擎实时执行标准输出流</span>
          <el-button size="small" type="info" link @click="$emit('clear-logs')">清屏</el-button>
        </div>
        <div class="log-terminal custom-scrollbar" ref="terminalRef">
          <div v-for="(log, idx) in liveLogs" :key="idx" class="log-line" :class="log.type">
            <span class="log-time">{{ log.time }}</span>
            <span class="log-text">{{ log.message }}</span>
          </div>
          <div v-if="liveLogs.length === 0" class="log-empty">等待引擎任务启动...</div>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { getPlatformConfig } from '../../config/platforms'
import { engine } from '../../../wailsjs/go/models'
import type { LiveLogItem } from '../../types/matrix'

defineProps<{
  modelValue: boolean
  preparedTasks: engine.AccountPublishTask[]
  batchAccountStates: Record<string, string>
  liveLogs: LiveLogItem[]
}>()

defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'clear-logs'): void
}>()

const terminalRef = ref<HTMLElement | null>(null)

const getPlatformStyle = (platformId: string) => {
  return getPlatformConfig(platformId)
}

const getStatusText = (st?: string) => {
  switch (st) {
    case 'running': return '正在发布...'
    case 'success': return '发布成功'
    case 'failed': return '发布失败'
    default: return '等待调度'
  }
}

defineExpose({
  terminalRef
})
</script>

<style scoped>
.exec-drawer-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 12px;
}

.exec-account-cards {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 220px;
  overflow-y: auto;
}

.exec-card {
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-detail);
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.exec-card.running {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.08);
}

.exec-card.success {
  border-color: #10b981;
  background: rgba(16, 185, 129, 0.08);
}

.exec-card.failed {
  border-color: #ef4444;
  background: rgba(239, 68, 68, 0.08);
}

.exec-card-top {
  display: flex;
  align-items: center;
  gap: 8px;
}

.plat-tag-badge {
  font-size: 9px;
  font-weight: 600;
  color: #fff;
  padding: 1px 5px;
  border-radius: 3px;
}

.exec-acc-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
  flex: 1;
}

.exec-status-badge {
  font-size: 11px;
  color: var(--text-secondary);
}

.exec-card-title {
  font-size: 11px;
  color: var(--text-secondary);
}

.title-tag {
  color: var(--text-muted);
}

.exec-log-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  background: #090d16;
  overflow: hidden;
}

.log-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 11px;
  color: #94a3b8;
}

.log-title {
  display: flex;
  align-items: center;
  gap: 5px;
}

.log-terminal {
  flex: 1;
  padding: 8px 10px;
  overflow-y: auto;
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 11px;
  line-height: 1.4;
}

.log-line {
  margin-bottom: 2px;
  word-break: break-all;
}

.log-time {
  color: #64748b;
  margin-right: 6px;
}

.log-line.error .log-text {
  color: #f87171;
}

.log-line.success .log-text {
  color: #34d399;
}

.log-line.log .log-text {
  color: #cbd5e1;
}

.log-empty {
  color: #475569;
  text-align: center;
  padding-top: 30px;
}
</style>
