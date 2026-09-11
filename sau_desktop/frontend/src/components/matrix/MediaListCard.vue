<template>
  <div class="media-list-card glass-card">
    <div class="card-header">
      <div class="card-title-box">
        <span class="step-badge">1</span>
        <div class="title-text-group">
          <div class="main-title">
            <span>要发哪些视频 / 素材</span>
            <span class="req-star">*</span>
            <span class="badge-count" v-if="mediaList.length > 0">已添加 {{ mediaList.length }} 个</span>
          </div>
          <div class="sub-title">支持批量多选导入本地短视频，系统将自动识别视频名、集数并在矩阵中排产</div>
        </div>
      </div>

      <div class="header-actions">
        <el-button type="primary" class="gradient-btn-sm" @click="handleSelectFiles">
          <el-icon><Plus /></el-icon> 批量添加视频 (多选)
        </el-button>
        <el-button v-if="mediaList.length > 0" type="danger" link size="small" @click="handleClearAll">
          <el-icon><Delete /></el-icon> 清空
        </el-button>
      </div>
    </div>

    <!-- 搜索与快捷操作条 -->
    <div class="media-toolbar" v-if="mediaList.length > 0">
      <el-input
        v-model="searchQuery"
        placeholder="搜索视频文件名..."
        size="small"
        clearable
        prefix-icon="Search"
        class="search-input"
      />
      <div class="quick-batch-ops">
        <el-button size="small" link type="primary" @click="selectAll">全选</el-button>
        <el-button size="small" link @click="deselectAll">取消全选</el-button>
        <el-tooltip content="按列表顺序将所有视频重新编号为第 1, 2, 3... 集" placement="top">
          <el-button size="small" link type="warning" @click="reorderEpisodes">
            <el-icon><Sort /></el-icon> 重排集数
          </el-button>
        </el-tooltip>
      </div>
    </div>

    <!-- 视频清单列表 -->
    <div v-if="filteredMediaList.length > 0" class="video-list custom-scrollbar">
      <div
        v-for="(item, index) in filteredMediaList"
        :key="item.id"
        class="video-card-item"
        :class="{ selected: selectedMediaIds.includes(item.id) }"
        @click="toggleSelect(item.id)"
      >
        <!-- 复选框 -->
        <div class="video-checkbox" @click.stop>
          <el-checkbox
            :model-value="selectedMediaIds.includes(item.id)"
            @change="() => toggleSelect(item.id)"
          />
        </div>

        <!-- 缩略图占位 -->
        <div class="video-thumb">
          <el-icon class="thumb-icon"><Film /></el-icon>
          <span class="format-badge">{{ item.format || 'MP4' }}</span>
        </div>

        <!-- 视频基础信息 -->
        <div class="video-info">
          <div class="video-name" :title="item.fileName">
            <span class="video-idx">#{{ index + 1 }}</span>
            <span class="name-text">{{ item.fileName }}</span>
          </div>
          <div class="video-meta">
            <!-- 可直接微调集数的微标 -->
            <el-popover placement="top" :width="180" trigger="click">
              <template #reference>
                <span class="meta-item clickable-ep-badge" @click.stop title="点击微调该视频集数">
                  <el-icon><EditPen /></el-icon>
                  <span>第 {{ item.parsedEpisode ?? (index + 1) }} 集</span>
                </span>
              </template>
              <div class="ep-edit-popover" @click.stop>
                <div class="popover-tip">设定该视频指定集数:</div>
                <el-input-number
                  v-model="item.parsedEpisode"
                  :min="1"
                  :max="9999"
                  size="small"
                  controls-position="right"
                  @change="handleEpisodeUpdated"
                />
              </div>
            </el-popover>

            <span class="meta-item" v-if="item.fileSize">{{ item.fileSize }}</span>
            <span class="meta-path" :title="item.filePath">{{ item.filePath }}</span>
          </div>
        </div>

        <!-- 单项操作 -->
        <div class="row-actions" @click.stop>
          <el-tooltip content="从清单中移除该视频" placement="top">
            <el-button
              type="danger"
              link
              size="small"
              class="del-btn"
              @click="removeMedia(item.id)"
            >
              <el-icon><Close /></el-icon>
            </el-button>
          </el-tooltip>
        </div>
      </div>
    </div>

    <!-- 空状态提示 -->
    <div v-else-if="mediaList.length === 0" class="empty-upload-zone" @click="handleSelectFiles">
      <div class="upload-icon-pulse">
        <el-icon><UploadFilled /></el-icon>
      </div>
      <div class="upload-title">点击批量选择本地短视频文件</div>
      <div class="upload-hint">支持按住 Ctrl / Cmd 批量多选，兼容 MP4, MOV, MKV 等主流格式</div>
      <el-button type="primary" class="gradient-btn-sm" style="margin-top: 14px;">
        <el-icon><FolderOpened /></el-icon> 浏览本地素材库
      </el-button>
    </div>

    <!-- 搜索无结果 -->
    <div v-else class="search-empty">
      <span>未找到匹配的视频文件</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { SelectLocalFiles } from '../../../wailsjs/go/main/App'
import type { MediaItem } from '../../types/matrix'

const props = defineProps<{
  mediaList: MediaItem[]
  selectedMediaIds: string[]
}>()

const emit = defineEmits<{
  (e: 'update:mediaList', list: MediaItem[]): void
  (e: 'update:selectedMediaIds', ids: string[]): void
  (e: 'add-media', items: MediaItem[]): void
}>()

const searchQuery = ref('')

// 过滤后的列表
const filteredMediaList = computed(() => {
  if (!searchQuery.value.trim()) return props.mediaList
  const q = searchQuery.value.toLowerCase()
  return props.mediaList.filter(m => m.fileName.toLowerCase().includes(q))
})

import { parseEpisodeFromFileName } from '../../utils/matrixHelper'

// 按当前顺序批量重排集数 (1, 2, 3...)
const reorderEpisodes = () => {
  const updated = props.mediaList.map((m, idx) => ({
    ...m,
    parsedEpisode: idx + 1
  }))
  emit('update:mediaList', updated)
  ElMessage.success(`已将全部 ${updated.length} 个视频重新按序编号为第 1~${updated.length} 集`)
}

// 单项集数手动调整
const handleEpisodeUpdated = () => {
  emit('update:mediaList', [...props.mediaList])
}

// 批量选择本地视频
const handleSelectFiles = async () => {
  try {
    const res = await SelectLocalFiles('选择待发布的本地短视频 (支持批量多选)', ['*.mp4;*.mov;*.mkv;*.flv;*.avi'])
    if (res && res.length > 0) {
      const newItems: MediaItem[] = res.map((fp, idx) => {
        const parts = fp.split(/[\/\\]/)
        const fileName = parts[parts.length - 1]
        const ext = fileName.includes('.') ? fileName.split('.').pop()?.toUpperCase() : 'MP4'
        const ep = parseEpisodeFromFileName(fileName) || (props.mediaList.length + idx + 1)
        return {
          id: `media_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
          filePath: fp,
          fileName: fileName,
          format: ext,
          parsedEpisode: ep
        }
      })

      const merged = [...props.mediaList, ...newItems]
      emit('update:mediaList', merged)

      // 默认将新添加的视频勾选
      const newIds = newItems.map(i => i.id)
      emit('update:selectedMediaIds', Array.from(new Set([...props.selectedMediaIds, ...newIds])))
      ElMessage.success(`成功导入 ${newItems.length} 个视频文件`)
    }
  } catch (err: any) {
    ElMessage.error(`选择文件失败: ${err?.message || err}`)
  }
}

// 切换单项选中
const toggleSelect = (id: string) => {
  const current = [...props.selectedMediaIds]
  const idx = current.indexOf(id)
  if (idx !== -1) {
    current.splice(idx, 1)
  } else {
    current.push(id)
  }
  emit('update:selectedMediaIds', current)
}

// 全选
const selectAll = () => {
  emit('update:selectedMediaIds', props.mediaList.map(m => m.id))
}

// 取消全选
const deselectAll = () => {
  emit('update:selectedMediaIds', [])
}

// 移除单个
const removeMedia = (id: string) => {
  const updated = props.mediaList.filter(m => m.id !== id)
  emit('update:mediaList', updated)
  emit('update:selectedMediaIds', props.selectedMediaIds.filter(i => i !== id))
}

// 清空全部
const handleClearAll = () => {
  emit('update:mediaList', [])
  emit('update:selectedMediaIds', [])
}
</script>

<style scoped>
.media-list-card {
  padding: 18px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  transition: all 0.25s ease;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 14px;
}

.card-title-box {
  display: flex;
  align-items: center;
  gap: 12px;
}

.step-badge {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--primary-gradient);
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
  flex-shrink: 0;
}

.title-text-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.main-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 8px;
}

.req-star {
  color: var(--status-danger);
}

.badge-count {
  font-size: 12px;
  color: var(--primary-color);
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.25);
  border-radius: 20px;
  padding: 1px 9px;
  font-weight: 600;
}

.sub-title {
  font-size: 12px;
  color: var(--text-muted);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.media-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.search-input {
  max-width: 260px;
}

.quick-batch-ops {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 视频清单流 */
.video-list {
  max-height: 260px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-right: 4px;
}

.video-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.video-row:hover {
  border-color: var(--primary-color);
  background: var(--bg-detail);
}

.video-row.selected {
  border-color: var(--primary-color);
  background: rgba(99, 102, 241, 0.08);
}

.check-box {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  border: 1.5px solid var(--border-highlight);
  background: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #fff;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.check-box.checked {
  background: var(--primary-color);
  border-color: var(--primary-color);
}

.video-thumb {
  width: 50px;
  height: 34px;
  border-radius: 6px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(168, 85, 247, 0.15));
  border: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  flex-shrink: 0;
}

.play-icon {
  font-size: 16px;
  color: var(--primary-color);
  opacity: 0.8;
}

.format-badge {
  position: absolute;
  right: 2px;
  bottom: 2px;
  font-size: 9px;
  font-weight: 700;
  color: var(--text-muted);
  background: rgba(0, 0, 0, 0.3);
  padding: 0 3px;
  border-radius: 3px;
}

.video-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.video-name {
  display: flex;
  align-items: center;
  gap: 6px;
}

.video-idx {
  font-size: 11px;
  font-weight: 700;
  color: var(--primary-color);
  background: rgba(99, 102, 241, 0.12);
  padding: 0 5px;
  border-radius: 4px;
}

.name-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.video-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--text-muted);
}

.meta-item {
  color: var(--text-secondary);
}

.meta-path {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 320px;
  opacity: 0.6;
}

.row-actions {
  flex-shrink: 0;
}

.del-btn {
  font-size: 15px;
  color: var(--text-muted);
}

.del-btn:hover {
  color: var(--status-danger);
}

/* 空状态拖入区 */
.empty-upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  border: 1.5px dashed var(--border-highlight);
  border-radius: 12px;
  cursor: pointer;
  background: var(--bg-detail);
  transition: all 0.25s ease;
}

.empty-upload-zone:hover {
  border-color: var(--primary-color);
  background: rgba(99, 102, 241, 0.05);
}

.upload-icon-pulse {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: rgba(99, 102, 241, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  color: var(--primary-color);
  margin-bottom: 12px;
}

.upload-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 4px;
}

.upload-hint {
  font-size: 12px;
  color: var(--text-muted);
}

.search-empty {
  text-align: center;
  padding: 24px;
  color: var(--text-muted);
  font-size: 13px;
}

.clickable-ep-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: rgba(99, 102, 241, 0.12);
  color: var(--primary-color);
  padding: 1px 6px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 600;
}

.clickable-ep-badge:hover {
  background: var(--primary-color);
  color: #fff;
}

.ep-edit-popover {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 4px 0;
}

.popover-tip {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
