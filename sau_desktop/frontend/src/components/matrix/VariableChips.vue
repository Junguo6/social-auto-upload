<template>
  <div class="variable-chips-helper">
    <!-- 变量快速选择标签栏 -->
    <div class="chips-row">
      <span class="chips-label">插入变量:</span>
      <div class="chips-list">
        <el-tooltip
          v-for="v in availableVars"
          :key="v.key"
          :content="v.desc"
          placement="top"
          :show-after="300"
        >
          <span class="var-chip-btn" @click.prevent="handleInsert(v.key)">
            + {{ v.label }}
          </span>
        </el-tooltip>
      </div>
    </div>

    <!-- 实时解析示例预览 -->
    <div v-if="previewText" class="preview-box">
      <span class="preview-icon">💡</span>
      <span class="preview-title">实时示例:</span>
      <span class="preview-value" :title="previewText">{{ previewText }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { AVAILABLE_VARIABLES, resolveTemplateString } from '../../utils/matrixHelper'
import type { MediaItem, BatchRuleConfig } from '../../types/matrix'

const props = withDefaults(defineProps<{
  /** 当前输入框的值，用于生成实时预览 */
  currentValue?: string
  /** 变量列表，默认全量 */
  vars?: Array<{ key: string; label: string; desc: string }>
  /** 用于计算示例的媒体参考对象 */
  sampleMedia?: Partial<MediaItem>
  /** 分集或排期规则 */
  ruleConfig?: Partial<BatchRuleConfig>
}>(), {
  currentValue: '',
  vars: () => AVAILABLE_VARIABLES,
  sampleMedia: () => ({
    fileName: '迟遇山野知秋_第01集.mp4',
    filePath: '/素材库/迟遇山野知秋/迟遇山野知秋_第01集.mp4',
    folderCrumbs: ['素材库', '迟遇山野知秋'],
    parsedEpisode: 1
  })
})

const emit = defineEmits<{
  (e: 'insert', variableKey: string): void
}>()

const availableVars = computed(() => props.vars || AVAILABLE_VARIABLES)

const handleInsert = (key: string) => {
  emit('insert', key)
}

// 实时计算输入文本在参考视频下的解析示例
const previewText = computed(() => {
  const val = props.currentValue?.trim()
  if (!val) return ''
  // 检查是否包含任何变量大括号
  if (!/\{.*?\}/.test(val)) return ''

  const dummyMedia = props.sampleMedia || {
    fileName: '迟遇山野知秋_第01集.mp4',
    filePath: '/素材库/迟遇山野知秋/迟遇山野知秋_第01集.mp4',
    folderCrumbs: ['素材库', '迟遇山野知秋'],
    parsedEpisode: 1
  }

  return resolveTemplateString(val, dummyMedia, 0, props.ruleConfig)
})
</script>

<style scoped>
.variable-chips-helper {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 6px;
  font-size: 12px;
}

.chips-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.chips-label {
  color: var(--text-tertiary, #909399);
  font-size: 11px;
  user-select: none;
}

.chips-list {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.var-chip-btn {
  display: inline-flex;
  align-items: center;
  padding: 2px 7px;
  font-size: 11px;
  line-height: 1.3;
  color: var(--el-color-primary, #409eff);
  background: rgba(64, 158, 255, 0.08);
  border: 1px solid rgba(64, 158, 255, 0.2);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.var-chip-btn:hover {
  background: rgba(64, 158, 255, 0.18);
  border-color: var(--el-color-primary, #409eff);
  transform: translateY(-1px);
}

.preview-box {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background: rgba(255, 255, 255, 0.04);
  border-left: 2px solid var(--el-color-primary, #409eff);
  border-radius: 0 4px 4px 0;
  color: var(--text-secondary, #606266);
  font-size: 11px;
  overflow: hidden;
}

.preview-icon {
  font-size: 12px;
}

.preview-title {
  color: var(--text-tertiary, #909399);
  font-weight: 500;
  flex-shrink: 0;
}

.preview-value {
  color: var(--text-primary, #303133);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
