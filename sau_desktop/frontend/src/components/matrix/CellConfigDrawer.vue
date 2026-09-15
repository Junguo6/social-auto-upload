<template>
  <el-dialog
    v-model="visible"
    width="960px"
    top="5vh"
    align-center
    destroy-on-close
    class="cell-config-dialog"
  >
    <!-- 自定义高质感标题栏 -->
    <template #header>
      <div class="dialog-custom-header" v-if="cellData">
        <div class="header-left">
          <span class="plat-pill" :style="{ background: getPlatformColor(cellData.platform) }">
            {{ getPlatformName(cellData.platform) }}
          </span>
          <span class="header-title">渠道发布定制 · @{{ cellData.nickname || cellData.account }}</span>
        </div>
        <div class="header-right">
          <div class="banner-media-info">
            <el-icon class="media-icon"><Film /></el-icon>
            <span class="media-name" :title="cellData.mediaName">{{ cellData.mediaName }}</span>
          </div>
          <el-tag :type="cellData.cell.enabled ? 'success' : 'info'" size="small" class="status-tag">
            {{ cellData.cell.enabled ? '已启用发布' : '暂停不发布' }}
          </el-tag>
        </div>
      </div>
    </template>

    <!-- 双栏开阔内容区 (告别单列抽屉局促感) -->
    <div v-if="cellData" class="dialog-body custom-scrollbar">
      <div class="dialog-two-columns">
        <!-- 左栏：继承基线、状态与发布时机 (占 38%) -->
        <div class="column-left">
          <!-- 1. 全局继承原值实时对照卡片 -->
          <div class="inherited-context-card">
            <div class="context-header">
              <div class="context-title">
                <el-icon><CopyDocument /></el-icon>
                <span>全局继承基准</span>
              </div>
              <el-button size="small" link type="primary" class="copy-btn" @click="copyInheritedToOverride">
                <el-icon><DocumentCopy /></el-icon> 一键带入微调
              </el-button>
            </div>
            <div class="context-body">
              <div class="context-item">
                <span class="c-label">继承标题:</span>
                <span class="c-val" :title="cellData.inheritedTitle">{{ cellData.inheritedTitle || '无标题' }}</span>
              </div>
              <div class="context-item" v-if="cellData.inheritedDesc">
                <span class="c-label">继承正文:</span>
                <span class="c-val text-clamp-3" :title="cellData.inheritedDesc">{{ cellData.inheritedDesc }}</span>
              </div>
              <div class="context-item" v-if="cellData.inheritedTags">
                <span class="c-label">继承标签:</span>
                <span class="c-val">{{ cellData.inheritedTags }}</span>
              </div>
              <div class="context-item">
                <span class="c-label">预计排期:</span>
                <span class="c-val timing-text">{{ cellData.inheritedSchedule || '立即发布' }}</span>
              </div>
            </div>
          </div>

          <!-- 2. 发布通道状态与时机控制 -->
          <div class="config-section">
            <div class="section-title">
              <el-icon><Timer /></el-icon>
              <span>发布状态与排期策略</span>
            </div>
            <div class="field-row">
              <span class="field-label">启用该通道发布:</span>
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
                placeholder="选择该账号专属定时时间"
                value-format="YYYY-MM-DD HH:mm"
                size="small"
                style="width: 100%;"
                @change="handleDirty"
              />
            </div>
          </div>
        </div>

        <!-- 右栏：专属文案微调与平台专属特性 (占 62%) -->
        <div class="column-right">
          <!-- 3. 专属标题与文案微调 -->
          <div class="config-section" v-if="cellData.cell.enabled">
            <div class="section-title-row">
              <div class="section-title">
                <el-icon><EditPen /></el-icon>
                <span>专属标题与文案微调</span>
              </div>
              <el-button v-if="cellData.cell.isCustomized" size="small" link type="warning" @click="resetToInherit">
                恢复继承全局
              </el-button>
            </div>

            <div class="field-col">
              <div class="label-with-hint">
                <span class="field-label">专属稿件标题:</span>
                <span class="field-hint">留空则自动继承全局标题</span>
              </div>
              <el-input
                v-model="cellData.cell.customTitle"
                placeholder="针对该账号微调后的个性化标题..."
                clearable
                size="small"
                @input="handleDirty"
              />
            </div>

            <div class="field-col">
              <div class="label-with-hint">
                <span class="field-label">专属正文简介描述:</span>
                <span class="field-hint">留空则继承全局简介正文</span>
              </div>
              <el-input
                v-model="cellData.cell.override.desc"
                type="textarea"
                :rows="3"
                placeholder="针对该账号个性化微调的文案、话术、引导语或口播词..."
                size="small"
                @input="handleDirty"
              />
            </div>

            <div class="field-col">
              <div class="label-with-hint">
                <span class="field-label">专属话题标签:</span>
                <span class="field-hint">逗号分隔</span>
              </div>
              <el-input
                v-model="cellData.cell.override.tags"
                placeholder="如：专属话题A, 专属话题B"
                clearable
                size="small"
                @input="handleDirty"
              />
            </div>
          </div>

          <!-- 4. 平台专属高级特性 (组件化一体复用) -->
          <div class="config-section" v-if="cellData.cell.enabled">
            <div class="section-title">
              <el-icon><Setting /></el-icon>
              <span>{{ getPlatformName(cellData.platform) }} 平台专属高级特性</span>
              <span class="sub-hint">(必填分区或平台独有合规设置)</span>
            </div>

            <TencentForm v-if="cellData.platform === 'tencent'" :override="cellData.cell.override" />
            <BilibiliForm v-else-if="cellData.platform === 'bilibili'" :override="cellData.cell.override" />
            <DouyinForm v-else-if="cellData.platform === 'douyin'" :override="cellData.cell.override" />
            <XiaohongshuForm v-else-if="cellData.platform === 'xiaohongshu'" :override="cellData.cell.override" />
            <GenericForm v-else :override="cellData.cell.override" />
          </div>
        </div>
      </div>
    </div>

    <!-- 底部操作栏 -->
    <template #footer>
      <div class="dialog-footer">
        <el-button size="small" type="primary" link @click="$emit('open-sync')">
          <el-icon><Connection /></el-icon> 一键克隆同步到同平台其他账号
        </el-button>
        <div class="btn-group">
          <el-button size="small" @click="visible = false">取消</el-button>
          <el-button size="small" type="primary" class="gradient-btn-sm" @click="visible = false">
            完成并保存微调
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getPlatformConfig } from '../../config/platforms'
import type { MatrixCellConfig } from '../../types/matrix'

// 平台专属表单子组件 (与矩阵定制卡片完全复用同一套组件与校验规范)
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

// 标记为已定制
const handleDirty = () => {
  if (props.cellData?.cell) {
    props.cellData.cell.isCustomized = true
  }
}

// 深度监听单元格专属配置，自动标记为已定制
watch(
  () => props.cellData?.cell?.override,
  () => {
    handleDirty()
  },
  { deep: true }
)

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
:deep(.el-dialog.cell-config-dialog) {
  border-radius: 16px;
  overflow: hidden;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  box-shadow: 0 20px 48px rgba(0, 0, 0, 0.28);
}

:deep(.el-dialog__header) {
  margin: 0;
  padding: 16px 22px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-detail);
}

:deep(.el-dialog__body) {
  padding: 20px 22px;
  max-height: 78vh;
  overflow-y: auto;
}

:deep(.el-dialog__footer) {
  padding: 14px 22px;
  border-top: 1px solid var(--border-subtle);
  background: var(--bg-detail);
}

/* 顶部标题栏 */
.dialog-custom-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding-right: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.plat-pill {
  padding: 3px 10px;
  border-radius: 20px;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.header-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.banner-media-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-card);
  padding: 4px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
}

.media-icon {
  color: var(--primary-color);
  font-size: 14px;
}

.media-name {
  max-width: 220px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 600;
}

/* 双栏网格开阔排版 */
.dialog-two-columns {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 18px;
  align-items: start;
}

.column-left,
.column-right {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 继承原值对照卡片 */
.inherited-context-card {
  background: rgba(99, 102, 241, 0.05);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 12px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.context-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.context-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--primary-color);
  display: flex;
  align-items: center;
  gap: 6px;
}

.copy-btn {
  font-size: 11px;
  font-weight: 600;
}

.context-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12px;
  background: var(--bg-card);
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
}

.context-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.c-label {
  color: var(--text-muted);
  font-weight: 600;
  width: 58px;
  flex-shrink: 0;
}

.c-val {
  color: var(--text-main);
  flex: 1;
  word-break: break-all;
}

.text-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
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
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  font-size: 13px;
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
  gap: 12px;
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
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 600;
}

.field-hint {
  font-size: 11px;
  color: var(--text-muted);
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
  gap: 10px;
}

.gradient-btn-sm {
  background: linear-gradient(135deg, var(--primary-color) 0%, #4f46e5 100%);
  border: none;
  font-weight: 600;
}
</style>
