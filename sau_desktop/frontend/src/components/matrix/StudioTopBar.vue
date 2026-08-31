<template>
  <div class="studio-topbar glass-card">
    <div class="topbar-left">
      <div class="studio-logo-badge">
        <el-icon><Grid /></el-icon>
      </div>
      <div class="studio-title-box">
        <div class="studio-title">
          <span>全景矩阵差异化发布工作台</span>
          <span class="badge-pro">MATRIX STUDIO</span>
        </div>
        <div class="studio-sub">左侧全局主模板智能分发，右侧各平台与账号独立精准调优</div>
      </div>
    </div>

    <div class="topbar-actions">
      <el-dropdown trigger="click" @command="$emit('template-command', $event)">
        <el-button class="glass-btn">
          <el-icon><FolderOpened /></el-icon>
          <span>预设模板 ({{ savedTemplates.length }})</span>
          <el-icon class="el-icon--right"><ArrowDown /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu class="custom-dropdown-menu">
            <el-dropdown-item v-if="savedTemplates.length === 0" disabled>暂无保存的预设模板</el-dropdown-item>
            <el-dropdown-item 
              v-for="tpl in savedTemplates" 
              :key="tpl.id" 
              :command="'load:' + tpl.id"
            >
              <el-icon><Document /></el-icon> {{ tpl.name }} <span class="tpl-time">({{ tpl.createdAt }})</span>
            </el-dropdown-item>
            <el-dropdown-item divided command="save">
              <el-icon><FolderAdd /></el-icon> 将当前全套配置存为新模板
            </el-dropdown-item>
            <el-dropdown-item v-if="savedTemplates.length > 0" command="clear">
              <el-icon><Delete /></el-icon> 清空所有预设模板
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <el-button class="glass-btn" @click="$emit('fill-demo')">
        <el-icon><MagicStick /></el-icon> 填入演示作品
      </el-button>

      <el-button class="glass-btn danger-hover" @click="$emit('reset-all')">
        <el-icon><RefreshLeft /></el-icon> 重置配置
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { MatrixPreset } from '../../types/matrix'

defineProps<{
  savedTemplates: MatrixPreset[]
}>()

defineEmits<{
  (e: 'template-command', cmd: string): void
  (e: 'fill-demo'): void
  (e: 'reset-all'): void
}>()
</script>

<style scoped>
.studio-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 22px;
  border-radius: 12px;
  flex-shrink: 0;
  border: 1px solid var(--border-subtle);
  background: var(--bg-card);
  backdrop-filter: blur(16px);
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.studio-logo-badge {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
}

.studio-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 8px;
}

.badge-pro {
  font-size: 10px;
  padding: 2px 6px;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.35);
  color: #818cf8;
  border-radius: 4px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.studio-sub {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 3px;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.glass-btn {
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  color: var(--text-main);
  border-radius: 7px;
  font-size: 13px;
  height: 34px;
  padding: 0 14px;
  transition: all 0.2s ease;
}

.glass-btn:hover {
  border-color: var(--primary-light);
  color: var(--primary-light);
  background: rgba(99, 102, 241, 0.08);
}

.danger-hover:hover {
  border-color: #ef4444 !important;
  color: #ef4444 !important;
  background: rgba(239, 68, 68, 0.08) !important;
}

.tpl-time {
  font-size: 11px;
  color: var(--text-muted);
  margin-left: 4px;
}
</style>
