<template>
  <el-dialog
    v-model="visible"
    :width="isFullscreen ? '100vw' : '1180px'"
    :fullscreen="isFullscreen"
    top="4vh"
    align-center
    append-to-body
    :before-close="handleBeforeClose"
    destroy-on-close
    class="cell-config-global-dialog"
  >
    <!-- 全局自适应高质感标题栏 -->
    <template #header>
      <div class="dialog-custom-header" v-if="cellData">
        <div class="header-left">
          <span class="plat-pill" :style="{ background: getPlatformColor(cellData.platform) }">
            {{ getPlatformName(cellData.platform) }}
          </span>
          <span class="header-title">全局发布微调 · @{{ cellData.nickname || cellData.account }}</span>
          <el-tag :type="cellData.cell.enabled ? 'success' : 'info'" size="small" class="status-tag">
            {{ cellData.cell.enabled ? '已激活本通道' : '跳过不发布' }}
          </el-tag>
        </div>
        <div class="header-right">
          <div class="banner-media-info">
            <el-icon class="media-icon"><Film /></el-icon>
            <span class="media-name" :title="cellData.mediaName">{{ cellData.mediaName }}</span>
          </div>
          <el-tooltip :content="isFullscreen ? '退出全屏' : '全屏展开'" placement="bottom">
            <el-button
              circle
              size="small"
              class="fullscreen-toggle-btn"
              @click="isFullscreen = !isFullscreen"
            >
              <el-icon><FullScreen /></el-icon>
            </el-button>
          </el-tooltip>
        </div>
      </div>
    </template>

    <!-- 双栏开阔全局工作台 (彻底告别单列抽屉狭小局促感) -->
    <div v-if="cellData" class="dialog-body custom-scrollbar">
      <div class="dialog-two-columns">
        <!-- 左栏：继承对照基准与排期策略 (占 36%) -->
        <div class="column-left">
          <!-- 1. 全局继承基准卡片 -->
          <div class="inherited-context-card">
            <div class="context-header">
              <div class="context-title">
                <el-icon><CopyDocument /></el-icon>
                <span>全局继承基准预演</span>
              </div>
              <el-button size="small" link type="primary" class="copy-btn" @click="copyInheritedToOverride">
                <el-icon><DocumentCopy /></el-icon> 一键带入原值微调
              </el-button>
            </div>
            <div class="context-body">
              <div class="context-item">
                <span class="c-label">继承标题:</span>
                <span class="c-val text-bold" :title="cellData.inheritedTitle">{{ cellData.inheritedTitle || '无标题' }}</span>
              </div>
              <div class="context-item" v-if="cellData.inheritedDesc">
                <span class="c-label">继承正文:</span>
                <span class="c-val text-clamp-3" :title="cellData.inheritedDesc">{{ cellData.inheritedDesc }}</span>
              </div>
              <div class="context-item" v-if="cellData.inheritedTags">
                <span class="c-label">继承标签:</span>
                <span class="c-val tag-cloud">{{ cellData.inheritedTags }}</span>
              </div>
              <div class="context-item">
                <span class="c-label">预计排期:</span>
                <span class="c-val timing-text">{{ cellData.inheritedSchedule || '立即发布' }}</span>
              </div>
            </div>
          </div>

          <!-- 2. 发布通道激活状态与排期策略 -->
          <div class="config-section">
            <div class="section-title">
              <el-icon><Timer /></el-icon>
              <span>发布通道与排期策略</span>
            </div>
            <div class="field-row">
              <span class="field-label">启用该账号发布:</span>
              <el-switch
                v-model="cellData.cell.enabled"
                active-text="启用"
                inactive-text="跳过"
                @change="handleDirty"
              />
            </div>
            <div class="field-col" v-if="cellData.cell.enabled">
              <span class="field-label">发布时机模式:</span>
              <el-radio-group v-model="cellData.cell.scheduleMode" size="small" @change="handleDirty">
                <el-radio-button value="inherit">继承全局排期</el-radio-button>
                <el-radio-button value="immediate">立即发布</el-radio-button>
                <el-radio-button value="scheduled">专属定时</el-radio-button>
              </el-radio-group>
            </div>
            <div class="field-col" v-if="cellData.cell.enabled && cellData.cell.scheduleMode === 'scheduled'">
              <span class="field-label">专属定时发布时间:</span>
              <el-date-picker
                v-model="cellData.cell.customSchedule"
                type="datetime"
                placeholder="选择该账号专属定时发布时间"
                value-format="YYYY-MM-DD HH:mm"
                size="small"
                style="width: 100%;"
                @change="handleDirty"
              />
            </div>
          </div>
        </div>

        <!-- 右栏：专属文案与平台高级专属特性 (占 64%) -->
        <div class="column-right">
          <!-- 3. 专属标题与正文文案微调 -->
          <div class="config-section" v-if="cellData.cell.enabled">
            <div class="section-title-row">
              <div class="section-title">
                <el-icon><EditPen /></el-icon>
                <span>专属标题与正文文案微调</span>
              </div>
              <el-button v-if="cellData.cell.isCustomized" size="small" link type="warning" @click="resetToInherit">
                恢复继承全局
              </el-button>
            </div>

            <div class="field-col">
              <div class="label-with-hint">
                <span class="field-label">专属稿件标题:</span>
                <span class="field-hint">留空则自动继承全局统一标题</span>
              </div>
              <el-input
                v-model="cellData.cell.customTitle"
                placeholder="输入该账号独立微调标题..."
                clearable
                size="default"
                @input="handleDirty"
              />
            </div>

            <div class="field-col">
              <div class="label-with-hint">
                <span class="field-label">专属正文简介描述:</span>
                <span class="field-hint">留空则继承全局统一文案</span>
              </div>
              <el-input
                v-model="cellData.cell.override.desc"
                type="textarea"
                :rows="4"
                placeholder="针对该账号个性化微调的文案、话术、引导语或专属口播词..."
                size="default"
                @input="handleDirty"
              />
            </div>

            <div class="field-col">
              <div class="label-with-hint">
                <span class="field-label">专属话题标签:</span>
                <span class="field-hint">多个标签用逗号分隔</span>
              </div>
              <el-input
                v-model="cellData.cell.override.tags"
                placeholder="如：专属话题A, 专属话题B"
                clearable
                size="default"
                @input="handleDirty"
              />
            </div>
          </div>

          <!-- 4. 平台专属高级特性 (组件化全局复用) -->
          <div class="config-section" v-if="cellData.cell.enabled">
            <div class="section-title">
              <el-icon><Setting /></el-icon>
              <span>{{ getPlatformName(cellData.platform) }} 平台专属高级特性</span>
              <span class="sub-hint">(必填主分区、版权合规声明与平台专属控制)</span>
            </div>

            <div class="platform-form-wrapper">
              <TencentForm v-if="cellData.platform === 'tencent'" :override="cellData.cell.override" />
              <BilibiliForm v-else-if="cellData.platform === 'bilibili'" :override="cellData.cell.override" />
              <DouyinForm v-else-if="cellData.platform === 'douyin'" :override="cellData.cell.override" />
              <XiaohongshuForm v-else-if="cellData.platform === 'xiaohongshu'" :override="cellData.cell.override" />
              <GenericForm v-else :override="cellData.cell.override" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部全局操作栏 -->
    <template #footer>
      <div class="dialog-footer">
        <el-button size="small" type="primary" link @click="$emit('open-sync')">
          <el-icon><Connection /></el-icon> 一键克隆同步到同平台其他账号
        </el-button>
        <div class="btn-group">
          <el-button size="default" @click="handleCancel">取消</el-button>
          <el-button size="default" type="primary" class="gradient-btn" @click="handleSave">
            完成并保存微调
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getPlatformConfig } from '../../config/platforms'
import type { MatrixCellConfig } from '../../types/matrix'

// 平台专属表单子组件
import TencentForm from './platforms/TencentForm.vue'
import DouyinForm from './platforms/DouyinForm.vue'
import BilibiliForm from './platforms/BilibiliForm.vue'
import XiaohongshuForm from './platforms/XiaohongshuForm.vue'
import GenericForm from './platforms/GenericForm.vue'

export interface CellDataWrap {
  mediaId: string
  mediaName: string
  platform: string
  account: string
  nickname?: string
  cell: MatrixCellConfig
  inheritedTitle?: string
  inheritedDesc?: string
  inheritedTags?: string
  inheritedSchedule?: string
}

const props = defineProps<{
  modelValue: boolean
  cellData: CellDataWrap | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'open-sync'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 是否全屏展示状态
const isFullscreen = ref(false)

// 记录打开弹窗时的原始快照深拷贝，用于取消时原样回退
let originalSnapshot: string | null = null
let isSaved = false

// 打开弹窗时记录初始状态快照
watch(
  () => props.modelValue,
  (isOpen) => {
    if (isOpen && props.cellData?.cell) {
      isSaved = false
      originalSnapshot = JSON.stringify({
        customTitle: props.cellData.cell.customTitle || '',
        customSchedule: props.cellData.cell.customSchedule || '',
        scheduleMode: props.cellData.cell.scheduleMode || 'inherit',
        enabled: props.cellData.cell.enabled !== false,
        isCustomized: !!props.cellData.cell.isCustomized,
        override: JSON.parse(JSON.stringify(props.cellData.cell.override || {}))
      })
    }
  },
  { immediate: true }
)

// 判断是否有实质性的专属定制内容
const hasActiveCustomization = (cell: MatrixCellConfig): boolean => {
  if (cell.customTitle && cell.customTitle.trim()) return true
  if (cell.override?.desc && cell.override.desc.trim()) return true
  if (cell.override?.tags && cell.override.tags.trim()) return true
  if (cell.scheduleMode && cell.scheduleMode !== 'inherit') return true
  
  // 平台专属字段是否被定制
  const ov = cell.override
  if (ov) {
    if (ov.collection || ov.productTitle || ov.productLink || ov.shortTitle || ov.category || ov.draft) return true
    if (ov.declaration && ov.declaration !== '1' && ov.declaration !== '') return true
  }
  return false
}

// 标记为已修改 (用户显式输入时)
const handleDirty = () => {
  // 仅作为标记，实际状态在 handleSave 时精确判定
}

// 确认并保存微调
const handleSave = () => {
  if (props.cellData?.cell) {
    isSaved = true
    const hasCustom = hasActiveCustomization(props.cellData.cell)
    props.cellData.cell.isCustomized = hasCustom
    if (hasCustom) {
      ElMessage.success('已保存个性化微调配置')
    } else {
      ElMessage.info('未检测到实质专属改动，已保持实时继承全局')
    }
  }
  visible.value = false
}

// 取消编辑并完全还原初始快照
const handleCancel = () => {
  if (!isSaved && originalSnapshot && props.cellData?.cell) {
    try {
      const restored = JSON.parse(originalSnapshot)
      props.cellData.cell.customTitle = restored.customTitle
      props.cellData.cell.customSchedule = restored.customSchedule
      props.cellData.cell.scheduleMode = restored.scheduleMode
      props.cellData.cell.enabled = restored.enabled
      props.cellData.cell.isCustomized = restored.isCustomized
      if (restored.override && props.cellData.cell.override) {
        Object.assign(props.cellData.cell.override, restored.override)
      }
    } catch (e) {}
  }
  visible.value = false
}

// 弹窗关闭前拦截
const handleBeforeClose = (done: () => void) => {
  handleCancel()
  done()
}

// 一键复制继承原值到覆盖输入框
const copyInheritedToOverride = () => {
  if (!props.cellData) return
  if (props.cellData.inheritedTitle) {
    props.cellData.cell.customTitle = props.cellData.inheritedTitle
  }
  if (props.cellData.inheritedDesc) {
    props.cellData.cell.override.desc = props.cellData.inheritedDesc
  }
  if (props.cellData.inheritedTags) {
    props.cellData.cell.override.tags = props.cellData.inheritedTags
  }
  handleDirty()
  ElMessage.success('已将全局继承原值复制到个性化微调输入框')
}

// 恢复继承全局
const resetToInherit = () => {
  if (!props.cellData) return
  props.cellData.cell.customTitle = ''
  props.cellData.cell.override.desc = ''
  props.cellData.cell.override.tags = ''
  props.cellData.cell.isCustomized = false
  ElMessage.info('已清除专属文案，恢复为实时继承全局')
}

const getPlatformName = (platId?: string): string => {
  if (!platId) return ''
  return getPlatformConfig(platId).name
}

const getPlatformColor = (platId?: string): string => {
  if (!platId) return '#3b82f6'
  return getPlatformConfig(platId).brandColor || '#3b82f6'
}
</script>

<style scoped>
/* 全局挂载 Dialog 顶层样式 */
:deep(.el-dialog.cell-config-global-dialog) {
  border-radius: 16px;
  overflow: hidden;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.36);
  transition: all 0.25s ease-in-out;
}

:deep(.el-dialog__header) {
  margin: 0;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-detail);
}

:deep(.el-dialog__body) {
  padding: 22px 26px;
  max-height: 80vh;
  overflow-y: auto;
}

:deep(.el-dialog__footer) {
  padding: 14px 26px;
  border-top: 1px solid var(--border-subtle);
  background: var(--bg-detail);
}

/* 顶部标题栏 */
.dialog-custom-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding-right: 28px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.plat-pill {
  padding: 4px 12px;
  border-radius: 20px;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.5px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

.header-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.banner-media-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
  background: var(--bg-card);
  padding: 5px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
}

.media-icon {
  color: var(--primary-color);
  font-size: 15px;
}

.media-name {
  max-width: 280px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 600;
}

.fullscreen-toggle-btn {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.fullscreen-toggle-btn:hover {
  color: var(--primary-color);
  border-color: var(--primary-color);
}

/* 双栏开阔网格排版 */
.dialog-two-columns {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 22px;
  align-items: start;
}

.column-left,
.column-right {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* 继承原值对照卡片 */
.inherited-context-card {
  background: rgba(99, 102, 241, 0.05);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 12px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.context-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.context-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--primary-color);
  display: flex;
  align-items: center;
  gap: 6px;
}

.copy-btn {
  font-size: 12px;
  font-weight: 600;
}

.context-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  font-size: 13px;
  background: var(--bg-card);
  padding: 12px 14px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
}

.context-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.c-label {
  color: var(--text-muted);
  font-weight: 600;
  width: 65px;
  flex-shrink: 0;
}

.c-val {
  color: var(--text-main);
  flex: 1;
  word-break: break-all;
  line-height: 1.5;
}

.text-bold {
  font-weight: 600;
}

.text-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tag-cloud {
  color: var(--primary-color);
  font-family: monospace;
}

.timing-text {
  color: var(--status-warning);
  font-weight: 600;
}

/* 调优卡片区块 */
.config-section {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.section-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 8px;
}

.sub-hint {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: normal;
}

.field-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
}

.field-col {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.label-with-hint {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.field-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 600;
}

.field-hint {
  font-size: 11px;
  color: var(--text-muted);
}

.platform-form-wrapper {
  background: var(--bg-detail);
  padding: 14px 16px;
  border-radius: 10px;
  border: 1px solid var(--border-subtle);
}

.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.btn-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.gradient-btn {
  background: linear-gradient(135deg, var(--primary-color) 0%, #4f46e5 100%);
  border: none;
  font-weight: 600;
  padding: 8px 20px;
}
</style>
