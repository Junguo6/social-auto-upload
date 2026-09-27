<template>
  <Teleport to="body">
    <transition name="slide-panel">
      <div v-if="visible && cellData" class="cell-config-drawer-overlay" @click.self="handleCancel">
        <div class="cell-config-slide-panel" :class="{ fullscreen: isFullscreen }">
          <!-- 顶部自适应高质感标题栏 -->
          <div class="panel-custom-header">
            <div class="header-left">
              <span class="plat-pill" :style="{ background: getPlatformColor(cellData.platform) }">
                {{ getPlatformName(cellData.platform) }}
              </span>
              <span class="header-title">发布微调 · @{{ cellData.nickname || cellData.account }}</span>
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
              <button class="panel-close-btn" @click="handleCancel" title="关闭">
                <el-icon><Close /></el-icon>
              </button>
            </div>
          </div>

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

        <!-- 右栏：平台微调表单 (与发布信息内的表单结构 100% 一致) -->
        <div class="column-right">
          <div class="config-section platform-main-config" v-if="cellData.cell.enabled">
            <div class="section-title-row">
              <div class="section-title">
                <span class="plat-badge" :style="{ background: getPlatformColor(cellData.platform) }">
                  {{ getPlatformName(cellData.platform) }}
                </span>
                <span>平台发布微调表单</span>
            
              </div>
              <el-button v-if="cellData.cell.isCustomized" size="small" link type="warning" @click="resetToInherit">
                恢复继承基准
              </el-button>
            </div>

            <!-- 直接呈现对应的完整平台表单，不再有多余的中间层级与重复标题框 -->
            <div class="platform-form-wrapper">
              <TencentForm
                v-if="cellData.platform === 'tencent' || cellData.platform === 'wechat'"
                :override="cellData.cell.override"
                :rule-config="ruleConfig"
                :sample-media="currentSampleMedia"
                :unit-level="unitLevel"
                :hide-variables="true"
              />
              <BilibiliForm
                v-else-if="cellData.platform === 'bilibili'"
                :override="cellData.cell.override"
                :rule-config="ruleConfig"
                :sample-media="currentSampleMedia"
                :unit-level="unitLevel"
                :hide-variables="true"
              />
              <DouyinForm
                v-else-if="cellData.platform === 'douyin'"
                :override="cellData.cell.override"
                :rule-config="ruleConfig"
                :sample-media="currentSampleMedia"
                :unit-level="unitLevel"
                :hide-variables="true"
              />
              <XiaohongshuForm
                v-else-if="cellData.platform === 'xiaohongshu'"
                :override="cellData.cell.override"
                :rule-config="ruleConfig"
                :sample-media="currentSampleMedia"
                :unit-level="unitLevel"
                :hide-variables="true"
              />
              <GenericForm
                v-else
                :override="cellData.cell.override"
                :rule-config="ruleConfig"
                :sample-media="currentSampleMedia"
                :unit-level="unitLevel"
                :hide-variables="true"
              />
            </div>
          </div>
          <div v-else class="channel-disabled-empty">
            <el-empty description="当前发布通道已跳过，开启左侧开关即可微调发布内容" :image-size="80" />
          </div>
        </div>
      </div>
    </div>

          <!-- 底部操作栏 -->
          <div class="panel-footer">
            <el-button size="small" type="primary" link @click="handleCloneToSamePlatform">
              <el-icon><Connection /></el-icon> 一键克隆同步到同平台其他账号
            </el-button>
            <div class="btn-group">
              <el-button size="default" @click="handleCancel">取消</el-button>
              <el-button size="default" type="primary" class="gradient-btn" @click="handleSave">
                完成并保存微调
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Close, Film, FullScreen, Connection, CopyDocument, DocumentCopy, Timer } from '@element-plus/icons-vue'
import { getPlatformConfig } from '../../config/platforms'
import type { MatrixCellConfig, BatchRuleConfig } from '../../types/matrix'

// 平台专属表单子组件
import TencentForm from './platforms/TencentForm.vue'
import DouyinForm from './platforms/DouyinForm.vue'
import BilibiliForm from './platforms/BilibiliForm.vue'
import XiaohongshuForm from './platforms/XiaohongshuForm.vue'
import GenericForm from './platforms/GenericForm.vue'

export interface CellDataWrap {
  mediaId: string
  mediaName: string
  folderCrumbs?: string[]
  filePath?: string
  platform: string
  account: string
  nickname?: string
  cell: MatrixCellConfig
  inheritedTitle?: string
  inheritedDesc?: string
  inheritedTags?: string
  inheritedSchedule?: string
  inheritedOverride?: Record<string, any>
}

const props = defineProps<{
  modelValue: boolean
  cellData: CellDataWrap | null
  ruleConfig?: Partial<BatchRuleConfig>
  unitLevel?: number
  selectedAccounts?: Array<{ platform: string; account: string; nickname?: string }>
}>()

const currentSampleMedia = computed(() => {
  if (!props.cellData) return undefined
  return {
    id: props.cellData.mediaId,
    fileName: props.cellData.mediaName,
    folderCrumbs: props.cellData.folderCrumbs || [],
    filePath: props.cellData.filePath || ''
  }
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'clone-to-accounts', payload: { mediaId: string; sourceCell: MatrixCellConfig; targetAccounts: any[] }): void
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
      if (!props.cellData.cell.override) {
        props.cellData.cell.override = {
          isCustomized: false,
          title: '',
          desc: '',
          tags: '',
          thumbnail: '',
          thumbnailLandscape: '',
          thumbnailPortrait: '',
          tid: props.cellData.platform === 'bilibili' ? 230 : 0,
          shortTitle: '',
          category: '',
          draft: false,
          schedule: '',
          declaration: '',
          collection: '',
          productLink: '',
          productTitle: '',
          visibility: 'public',
          playlist: '',
          bgm: '',
          note: '',
          notef: ''
        }
      }
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
  if (cell.override?.title && cell.override.title.trim()) return true
  if (cell.override?.desc && cell.override.desc.trim()) return true
  if (cell.override?.tags && cell.override.tags.trim()) return true
  if (cell.scheduleMode && cell.scheduleMode !== 'inherit') return true
  
  // 平台专属字段是否被定制
  const ov = cell.override
  if (ov) {
    if (ov.collection || ov.productTitle || ov.productLink || ov.shortTitle || ov.category || ov.draft || ov.activityName || ov.linkTitle) return true
    if (ov.declaration && ov.declaration !== '1' && ov.declaration !== '') return true
    if (ov.location && ov.location !== 'auto') return true
    if (ov.tid && ov.tid !== 0 && ov.tid !== 230) return true
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
    // 如果平台表单设置了 override.title，同步到 customTitle 保证兼容
    if (props.cellData.cell.override?.title?.trim()) {
      props.cellData.cell.customTitle = props.cellData.cell.override.title.trim()
    }
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

// 一键复制继承原值到覆盖输入框（深度将第二步基准配置完整注入）
const copyInheritedToOverride = () => {
  if (!props.cellData?.cell) return
  const inh = props.cellData.inheritedOverride || {}

  // 深度复制平台基准配置
  const copiedOverride = JSON.parse(JSON.stringify(inh))

  // 针对标题对齐：
  if (props.cellData.inheritedTitle) {
    copiedOverride.title = props.cellData.inheritedTitle
    props.cellData.cell.customTitle = props.cellData.inheritedTitle
  }
  if (props.cellData.inheritedDesc) {
    copiedOverride.desc = props.cellData.inheritedDesc
  }
  if (props.cellData.inheritedTags) {
    copiedOverride.tags = props.cellData.inheritedTags
  }

  props.cellData.cell.override = copiedOverride
  props.cellData.cell.isCustomized = true
  ElMessage.success('已将该平台的基准配置完整带入微调表单，您可直接微调')
}

// 恢复继承全局基准
const resetToInherit = () => {
  if (!props.cellData?.cell) return
  props.cellData.cell.customTitle = ''
  props.cellData.cell.override = {
    isCustomized: false,
    title: '',
    desc: '',
    tags: '',
    thumbnail: '',
    thumbnailLandscape: '',
    thumbnailPortrait: '',
    tid: props.cellData.platform === 'bilibili' ? 230 : 0,
    shortTitle: '',
    category: '',
    draft: false,
    schedule: '',
    declaration: '',
    collection: '',
    productLink: '',
    productTitle: '',
    visibility: props.cellData.platform === 'douyin' ? '0' : 'public',
    playlist: '',
    bgm: '',
    note: '',
    notef: '',
    location: 'auto',
    linkType: 'none',
    linkUrl: '',
    linkTitle: '',
    activityName: ''
  }
  props.cellData.cell.isCustomized = false
  ElMessage.info('已恢复为实时继承全局基准')
}

// 查找同平台其他账号
const samePlatformAccounts = computed(() => {
  if (!props.cellData || !props.selectedAccounts) return []
  return props.selectedAccounts.filter(
    acc => acc.platform === props.cellData!.platform && acc.account !== props.cellData!.account
  )
})

// 一键克隆同步到同平台其他账号
const handleCloneToSamePlatform = async () => {
  if (!props.cellData?.cell) return
  const targets = samePlatformAccounts.value
  const platName = getPlatformName(props.cellData.platform)

  if (targets.length === 0) {
    ElMessage.info(`步骤②中未选择其他【${platName}】账号，无需克隆`)
    return
  }

  const targetNames = targets.map(t => `@${t.nickname || t.account}`).join('、')

  try {
    await ElMessageBox.confirm(
      `确定将当前账号（@${props.cellData.nickname || props.cellData.account}）的微调内容一键克隆给同平台其他 ${targets.length} 个账号吗？\n\n目标账号：${targetNames}\n\n（将同步标题、描述、话题标签及所有平台配置）`,
      `克隆微调配置 · ${platName}`,
      {
        confirmButtonText: '确定克隆覆盖',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    // 确保当前内容同步为定制状态
    if (props.cellData.cell.override?.title?.trim()) {
      props.cellData.cell.customTitle = props.cellData.cell.override.title.trim()
    }
    props.cellData.cell.isCustomized = true

    emit('clone-to-accounts', {
      mediaId: props.cellData.mediaId,
      sourceCell: JSON.parse(JSON.stringify(props.cellData.cell)),
      targetAccounts: targets
    })
  } catch (e) {
    // 取消
  }
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
/* 原生独立抽屉遮罩与面板 */
.cell-config-drawer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(6px);
  z-index: 3500;
  display: flex;
  justify-content: flex-end;
}

.cell-config-slide-panel {
  width: 880px;
  max-width: 90vw;
  height: 100vh;
  background: var(--bg-card, #1e293b);
  border-left: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.12));
  box-shadow: -16px 0 60px rgba(0, 0, 0, 0.55);
  display: flex;
  flex-direction: column;
  transition: width 0.25s ease;
}

.cell-config-slide-panel.fullscreen {
  width: 100vw;
  max-width: 100vw;
}

/* 顶部标题栏 */
.panel-custom-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 22px;
  background: var(--bg-detail, rgba(0, 0, 0, 0.25));
  border-bottom: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
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
  color: var(--text-main, #f8fafc);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.panel-close-btn {
  background: none;
  border: none;
  color: var(--text-secondary, #94a3b8);
  font-size: 18px;
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.panel-close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

/* 主体内容滚动区 */
.panel-body,
.dialog-body {
  flex: 1;
  padding: 22px;
  overflow-y: auto;
}

/* 底部操作栏 */
.panel-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 22px;
  background: var(--bg-detail, rgba(0, 0, 0, 0.25));
  border-top: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
}

/* 滑动动画 */
.slide-panel-enter-active,
.slide-panel-leave-active {
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.slide-panel-enter-from,
.slide-panel-leave-to {
  opacity: 0;
}

.slide-panel-enter-from .cell-config-slide-panel,
.slide-panel-leave-to .cell-config-slide-panel {
  transform: translateX(100%);
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

.plat-badge {
  padding: 2px 8px;
  border-radius: 4px;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: inline-block;
}

.channel-disabled-empty {
  padding: 40px 20px;
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
