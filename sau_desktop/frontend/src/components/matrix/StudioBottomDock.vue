<template>
  <div class="studio-bottom-dock glass-card">
    <div class="dock-left-settings">
      <div class="dock-setting-item">
        <span class="label">并发调度池:</span>
        <el-input-number 
          :model-value="concurrency" 
          :min="1" 
          :max="5" 
          size="small" 
          style="width: 100px" 
          @update:model-value="$emit('update:concurrency', $event || 3)"
        />
      </div>

      <div class="dock-setting-item">
        <span class="label">后台静默执行:</span>
        <el-switch 
          :model-value="isHeadless" 
          size="small" 
          @update:model-value="$emit('update:isHeadless', $event)"
        />
      </div>

      <div class="dock-summary">
        <span>分发目标: <strong>{{ activePlatformCount }}</strong> 个平台，<strong>{{ selectedCount }}</strong> 个矩阵账号</span>
      </div>
    </div>

    <div class="dock-right-actions">
      <router-link to="/tasks" class="view-tasks-link" v-if="taskStore.activeTasksCount > 0">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>查看后台任务 ({{ taskStore.activeTasksCount }})</span>
      </router-link>

      <el-button 
        type="primary" 
        size="large" 
        class="launch-btn gradient-btn-matrix"
        :disabled="selectedCount === 0"
        @click="$emit('start')"
      >
        <el-icon><Promotion /></el-icon>
        <span>创建并加入发布任务 ({{ selectedCount }})</span>
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useTaskStore } from '../../stores/taskStore'

const taskStore = useTaskStore()

defineProps<{
  concurrency: number
  isHeadless: boolean
  activePlatformCount: number
  selectedCount: number
}>()

defineEmits<{
  (e: 'update:concurrency', val: number): void
  (e: 'update:isHeadless', val: boolean): void
  (e: 'start'): void
}>()
</script>

<style scoped>
.studio-bottom-dock {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 18px;
  border-radius: 10px;
  flex-shrink: 0;
  border: 1px solid var(--border-subtle);
  background: var(--bg-card);
  backdrop-filter: blur(16px);
}

.dock-left-settings {
  display: flex;
  align-items: center;
  gap: 20px;
}

.dock-setting-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-main);
  font-weight: 500;
}

.dock-summary {
  font-size: 12px;
  color: var(--text-secondary);
}

.dock-summary strong {
  color: #818cf8;
  font-weight: 700;
}

.dock-right-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.view-tasks-link {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #60a5fa;
  text-decoration: none;
  padding: 4px 10px;
  border-radius: 6px;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.25);
  transition: all 0.15s;
}

.view-tasks-link:hover {
  background: rgba(59, 130, 246, 0.2);
}

.launch-btn {
  padding: 10px 24px;
  font-size: 13px;
  font-weight: 700;
  border-radius: 7px;
  height: 38px;
}

.gradient-btn-matrix {
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
  border: none !important;
  box-shadow: 0 4px 14px rgba(79, 70, 229, 0.3);
  transition: all 0.2s ease;
}

.gradient-btn-matrix:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(79, 70, 229, 0.45);
}
</style>
