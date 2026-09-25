<template>
  <el-drawer
    :model-value="modelValue"
    title="📦 任务批次中心与历史记录库"
    size="680px"
    append-to-body
    class="batch-manager-drawer"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div class="batch-drawer-body">
      <!-- 1. 顶部统计与搜索栏 -->
      <div class="batch-stats-overview glass-card">
        <div class="overview-stat">
          <span class="ov-num">{{ taskStore.batches.length }}</span>
          <span class="ov-label">累计批次</span>
        </div>
        <div class="overview-stat">
          <span class="ov-num text-success">{{ totalSuccessInBatches }}</span>
          <span class="ov-label">已成功卡片</span>
        </div>
        <div class="overview-stat">
          <span class="ov-num text-danger">{{ totalFailedInBatches }}</span>
          <span class="ov-label">失败/异常卡片</span>
        </div>
      </div>

      <!-- 搜索与筛选工具栏 -->
      <div class="batch-toolbar">
        <el-input 
          v-model="searchKeyword" 
          placeholder="按批次名 / 视频文件名搜索..." 
          size="default" 
          clearable 
          prefix-icon="Search"
          style="flex: 1;"
        />
        <el-select v-model="statusFilter" size="default" style="width: 140px;">
          <el-option label="全部状态" value="all" />
          <el-option label="全部成功" value="completed" />
          <el-option label="包含失败" value="partial" />
          <el-option label="排队/执行中" value="active" />
        </el-select>
      </div>

      <!-- 2. 批次列表流 -->
      <div class="batches-list-container custom-scrollbar">
        <div v-if="filteredBatches.length === 0" class="empty-batches">
          <el-icon class="empty-icon"><FolderOpened /></el-icon>
          <span class="empty-title">暂无匹配的任务批次</span>
          <span class="empty-desc">提交的矩阵发布任务将自动在此处沉淀归档，即使清理画板也能随时回溯并一键重新发布</span>
        </div>

        <div 
          v-for="batch in filteredBatches" 
          :key="batch.id"
          class="batch-record-card glass-card"
          :class="getBatchCardClass(batch)"
        >
          <!-- 批次头部 -->
          <div class="batch-card-header">
            <div class="header-main-info">
              <div class="batch-title-row">
                <span class="batch-title-text" :title="batch.name">{{ batch.name }}</span>
                <el-tag :type="getBatchTagType(batch)" size="small" effect="dark" round>
                  {{ getBatchStatusText(batch) }}
                </el-tag>
              </div>
              <div class="batch-meta-row">
                <span class="meta-time">
                  <el-icon><Calendar /></el-icon> {{ batch.createdAt }}
                </span>
                <span class="meta-video" v-if="batch.videoFileName" :title="batch.videoFileName">
                  <el-icon><Film /></el-icon> {{ batch.videoFileName }}
                </span>
                <span class="meta-concurrency">
                  <el-icon><Promotion /></el-icon> {{ batch.concurrency || 3 }} 线程并发
                </span>
              </div>
            </div>

            <!-- 批次操作工具 -->
            <div class="header-actions">
              <el-tooltip content="将该批次的所有任务克隆并重新载入工作流泳道排队执行" placement="top">
                <el-button 
                  size="small" 
                  type="primary" 
                  class="gradient-btn-matrix"
                  @click="handleRepublish(batch.id)"
                >
                  <el-icon><RefreshRight /></el-icon> 一键重发整批
                </el-button>
              </el-tooltip>

              <el-tooltip 
                v-if="getBatchFailedCount(batch) > 0" 
                content="仅将该批次中发布失败的任务重新加入通道排队" 
                placement="top"
              >
                <el-button 
                  size="small" 
                  type="warning" 
                  plain 
                  @click="handleRepublishFailed(batch.id)"
                >
                  <el-icon><Warning /></el-icon> 重发失败 ({{ getBatchFailedCount(batch) }})
                </el-button>
              </el-tooltip>

              <el-popconfirm 
                title="确定要从历史记录中删除该批次吗？"
                confirm-button-text="删除"
                cancel-button-text="取消"
                confirm-button-type="danger"
                @confirm="taskStore.deleteBatch(batch.id)"
              >
                <template #reference>
                  <el-button size="small" type="danger" link>
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>

          <!-- 进度与指标统计条 -->
          <div class="batch-progress-section">
            <div class="progress-info-row">
              <span class="task-counter">
                共 <strong>{{ batch.totalTasks }}</strong> 个任务卡片
                <span class="sep">·</span>
                <span class="text-success">成功 {{ getBatchSuccessCount(batch) }}</span>
                <span class="sep" v-if="getBatchFailedCount(batch) > 0">·</span>
                <span class="text-danger" v-if="getBatchFailedCount(batch) > 0">失败 {{ getBatchFailedCount(batch) }}</span>
              </span>
              <span class="percent-label">{{ getBatchPercent(batch) }}%</span>
            </div>
            <el-progress 
              :percentage="getBatchPercent(batch)" 
              :status="getBatchProgressStatus(batch)"
              :stroke-width="6" 
              :show-text="false"
            />
          </div>

          <!-- 卡片明细折叠控制 -->
          <div class="batch-expand-bar" @click="toggleExpand(batch.id)">
            <span class="expand-label">
              {{ expandedBatchIds.has(batch.id) ? '收起任务卡片明细' : `查看批次内 ${batch.totalTasks} 个任务明细快照` }}
            </span>
            <el-icon class="expand-icon" :class="{ 'is-expanded': expandedBatchIds.has(batch.id) }">
              <ArrowDown />
            </el-icon>
          </div>

          <!-- 展开的具体任务卡片列表 -->
          <div v-if="expandedBatchIds.has(batch.id)" class="batch-tasks-tray custom-scrollbar">
            <div 
              v-for="task in getBatchTaskList(batch)" 
              :key="task.id"
              class="batch-task-item"
              :class="task.status"
            >
              <div class="task-item-left">
                <span class="task-plat-badge" :style="{ background: getPlatformStyle(task.platform).brandColor }">
                  {{ getPlatformStyle(task.platform).name }}
                </span>
                <span class="task-acc-name">{{ task.nickname || task.account }}</span>
                <span class="task-title-text" :title="task.title">{{ task.title }}</span>
              </div>

              <div class="task-item-right">
                <span v-if="task.errorMsg" class="task-error-text" :title="task.errorMsg">
                  {{ task.errorMsg }}
                </span>
                <span class="task-status-pill" :class="task.status">
                  <el-icon v-if="task.status === 'success'"><Check /></el-icon>
                  <el-icon v-else-if="task.status === 'failed'"><Close /></el-icon>
                  <el-icon v-else-if="task.status === 'running'"><Loading /></el-icon>
                  <el-icon v-else><Clock /></el-icon>
                  <span>{{ getTaskStatusText(task.status) }}</span>
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { getPlatformConfig } from '../../config/platforms'
import { useTaskStore } from '../../stores/taskStore'
import type { TaskBatch, PublishTask } from '../../types/task'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'republished', batchId: string): void
}>()

const taskStore = useTaskStore()
const searchKeyword = ref('')
const statusFilter = ref('all')
const expandedBatchIds = ref<Set<string>>(new Set())

const toggleExpand = (batchId: string) => {
  if (expandedBatchIds.value.has(batchId)) {
    expandedBatchIds.value.delete(batchId)
  } else {
    expandedBatchIds.value.add(batchId)
  }
}

const getPlatformStyle = (plat: string) => getPlatformConfig(plat)

const getTaskStatusText = (status: string) => {
  switch (status) {
    case 'success': return '发布成功'
    case 'failed': return '失败'
    case 'running': return '执行中'
    case 'queued': return '排队中'
    case 'cancelled': return '已取消'
    default: return '待调度'
  }
}

const getBatchTaskList = (batch: TaskBatch): PublishTask[] => {
  // 优先从当前全局 tasks 取，取不到则从 tasksSnapshot 归档快照取
  const liveTasks = taskStore.tasks.filter(t => t.batchId === batch.id)
  if (liveTasks.length > 0) return liveTasks
  return batch.tasksSnapshot || []
}

const getBatchSuccessCount = (batch: TaskBatch): number => {
  const list = getBatchTaskList(batch)
  if (list.length > 0) {
    return list.filter(t => t.status === 'success').length
  }
  return batch.completedTasks || 0
}

const getBatchFailedCount = (batch: TaskBatch): number => {
  const list = getBatchTaskList(batch)
  if (list.length > 0) {
    return list.filter(t => t.status === 'failed' || t.status === 'cancelled').length
  }
  return batch.failedTasks || 0
}

const getBatchPercent = (batch: TaskBatch): number => {
  if (!batch.totalTasks || batch.totalTasks <= 0) return 0
  const succ = getBatchSuccessCount(batch)
  return Math.min(100, Math.round((succ / batch.totalTasks) * 100))
}

const getBatchProgressStatus = (batch: TaskBatch) => {
  const failed = getBatchFailedCount(batch)
  const succ = getBatchSuccessCount(batch)
  if (failed > 0) return 'exception'
  if (succ === batch.totalTasks && batch.totalTasks > 0) return 'success'
  return ''
}

const getBatchTagType = (batch: TaskBatch) => {
  const failed = getBatchFailedCount(batch)
  const succ = getBatchSuccessCount(batch)
  if (succ === batch.totalTasks && batch.totalTasks > 0) return 'success'
  if (failed > 0) return 'danger'
  return 'primary'
}

const getBatchStatusText = (batch: TaskBatch) => {
  const failed = getBatchFailedCount(batch)
  const succ = getBatchSuccessCount(batch)
  if (succ === batch.totalTasks && batch.totalTasks > 0) return '全部完成'
  if (failed > 0 && succ + failed === batch.totalTasks) return `存在 ${failed} 个失败`
  if (failed > 0) return `执行中 (${failed}个失败)`
  return '调度中'
}

const getBatchCardClass = (batch: TaskBatch) => {
  const failed = getBatchFailedCount(batch)
  const succ = getBatchSuccessCount(batch)
  if (succ === batch.totalTasks && batch.totalTasks > 0) return 'is-completed'
  if (failed > 0) return 'has-failed'
  return 'is-active'
}

const totalSuccessInBatches = computed(() => {
  return taskStore.batches.reduce((sum, b) => sum + getBatchSuccessCount(b), 0)
})

const totalFailedInBatches = computed(() => {
  return taskStore.batches.reduce((sum, b) => sum + getBatchFailedCount(b), 0)
})

const filteredBatches = computed(() => {
  return taskStore.batches.filter(b => {
    if (searchKeyword.value.trim()) {
      const q = searchKeyword.value.trim().toLowerCase()
      const matchName = b.name.toLowerCase().includes(q)
      const matchVideo = (b.videoFileName || '').toLowerCase().includes(q)
      if (!matchName && !matchVideo) return false
    }

    if (statusFilter.value === 'completed') {
      return getBatchSuccessCount(b) === b.totalTasks && b.totalTasks > 0
    } else if (statusFilter.value === 'partial') {
      return getBatchFailedCount(b) > 0
    } else if (statusFilter.value === 'active') {
      const done = getBatchSuccessCount(b) + getBatchFailedCount(b)
      return done < b.totalTasks
    }
    return true
  })
})

const handleRepublish = (batchId: string) => {
  const newBatchId = taskStore.republishBatch(batchId)
  if (newBatchId) {
    emit('update:modelValue', false)
    emit('republished', newBatchId)
  }
}

const handleRepublishFailed = (batchId: string) => {
  const newBatchId = taskStore.republishFailedInBatch(batchId)
  if (newBatchId) {
    emit('update:modelValue', false)
    emit('republished', newBatchId)
  }
}
</script>

<style scoped>
.batch-drawer-body {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 12px;
}

.batch-stats-overview {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 12px 16px;
  border-radius: 10px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.overview-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.ov-num {
  font-size: 20px;
  font-weight: 800;
  color: var(--text-main);
  line-height: 1.2;
}

.ov-label {
  font-size: 11px;
  color: var(--text-secondary);
}

.batch-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.batches-list-container {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-right: 4px;
}

.empty-batches {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 48px;
  color: #64748b;
  margin-bottom: 12px;
}

.empty-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.empty-desc {
  font-size: 12px;
  max-width: 360px;
  line-height: 1.6;
}

.batch-record-card {
  padding: 14px 16px;
  border-radius: 12px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.2s ease;
}

.batch-record-card:hover {
  border-color: rgba(99, 102, 241, 0.4);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

.batch-record-card.is-completed {
  border-left: 3px solid #10b981;
}

.batch-record-card.has-failed {
  border-left: 3px solid #ef4444;
}

.batch-record-card.is-active {
  border-left: 3px solid #3b82f6;
}

.batch-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.header-main-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.batch-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.batch-title-text {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 320px;
}

.batch-meta-row {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
  color: var(--text-muted);
  flex-wrap: wrap;
}

.meta-time, .meta-video, .meta-concurrency {
  display: flex;
  align-items: center;
  gap: 4px;
}

.meta-video {
  max-width: 180px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #818cf8;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.batch-progress-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.progress-info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
}

.task-counter {
  color: var(--text-secondary);
}

.sep {
  margin: 0 4px;
  color: var(--text-muted);
}

.percent-label {
  font-weight: 700;
  color: var(--text-main);
}

.batch-expand-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: rgba(0, 0, 0, 0.15);
  border-radius: 6px;
  cursor: pointer;
  font-size: 11px;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.batch-expand-bar:hover {
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-main);
}

.expand-icon {
  transition: transform 0.2s;
}

.expand-icon.is-expanded {
  transform: rotate(180deg);
}

.batch-tasks-tray {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 220px;
  overflow-y: auto;
  padding: 8px 10px;
  background: rgba(0, 0, 0, 0.25);
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
}

.batch-task-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.04);
  font-size: 11px;
  gap: 10px;
}

.task-item-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.task-plat-badge {
  font-size: 9px;
  font-weight: 600;
  color: #fff;
  padding: 1px 5px;
  border-radius: 3px;
  flex-shrink: 0;
}

.task-acc-name {
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
  flex-shrink: 0;
}

.task-title-text {
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-item-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.task-error-text {
  color: #f87171;
  max-width: 140px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 10px;
}

.task-status-pill {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 10px;
  font-weight: 600;
}

.task-status-pill.success { color: #10b981; }
.task-status-pill.failed { color: #ef4444; }
.task-status-pill.running { color: #3b82f6; }
.task-status-pill.queued { color: #eab308; }
.task-status-pill.cancelled { color: #94a3b8; }
</style>
