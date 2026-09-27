<template>
  <div class="variable-chips-helper">
    <!-- 变量快速选择标签栏 -->
    <div class="chips-row">
      <span class="chips-label">插入变量:</span>
      <div class="chips-list">
        <el-tooltip
          v-for="v in computedVars"
          :key="v.key"
          :content="`${v.desc} · 插入 ${v.key}${v.sampleVal ? '（当前值：' + v.sampleVal + '）' : ''}`"
          placement="top"
          :show-after="300"
        >
          <span
            class="var-chip-btn"
            :class="{ 'is-level': v.isLevel }"
            @click.prevent="handleInsert(v.key)"
          >
            + {{ v.label }}
            <span v-if="v.sampleVal" class="chip-sample-text">({{ v.sampleVal }})</span>
          </span>
        </el-tooltip>
      </div>
    </div>

    <!-- 实时解析示例预览 -->
    <div v-if="previewText" class="preview-box">
      <span class="preview-icon">💡</span>
      <span class="preview-title">实时解析示例:</span>
      <span class="preview-value" :title="previewText">{{ previewText }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  AVAILABLE_VARIABLES,
  buildDynamicVariables,
  resolveTemplateString,
  type AvailableVariable
} from '../../utils/matrixHelper'
import type { MediaItem, BatchRuleConfig } from '../../types/matrix'

const props = withDefaults(defineProps<{
  /** 当前输入框的值，用于生成实时预览 */
  currentValue?: string
  /** 变量列表，若未传入则根据 sampleMedia 和 unitLevel 动态探测生成 */
  vars?: AvailableVariable[]
  /** 用于计算示例的媒体参考对象（第一步上传的真实视频） */
  sampleMedia?: Partial<MediaItem>
  /** 分集或排期规则 */
  ruleConfig?: Partial<BatchRuleConfig>
  /** 第一步选择的分配单位层级 (0: 每条视频, 1: 第1层, 2: 第2层...) */
  unitLevel?: number
}>(), {
  currentValue: '',
  unitLevel: 0
})

const emit = defineEmits<{
  (e: 'insert', variableKey: string): void
}>()

// 优先动态根据真实素材构建变量
const computedVars = computed<AvailableVariable[]>(() => {
  if (props.vars && props.vars.length > 0) {
    return props.vars
  }
  return buildDynamicVariables(props.sampleMedia, props.unitLevel, props.ruleConfig)
})

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

  return resolveTemplateString(val, dummyMedia, 0, props.ruleConfig, props.unitLevel)
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
  font-weight: 500;
}

.chips-list {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 5px;
}

.var-chip-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 7px;
  font-size: 11px;
  line-height: 1.3;
  color: var(--el-color-primary, #409eff);
  background: rgba(64, 158, 255, 0.08);
  border: 1px solid rgba(64, 158, 255, 0.22);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
}

.var-chip-btn:hover {
  background: rgba(64, 158, 255, 0.2);
  border-color: var(--el-color-primary, #409eff);
  transform: translateY(-1px);
}

/* 目录层级专属标识高亮，视觉一目了然 */
.var-chip-btn.is-level {
  color: #8b5cf6;
  background: rgba(139, 92, 246, 0.09);
  border-color: rgba(139, 92, 246, 0.28);
}

.var-chip-btn.is-level:hover {
  background: rgba(139, 92, 246, 0.22);
  border-color: #8b5cf6;
}

.chip-sample-text {
  font-size: 10px;
  color: var(--text-muted, #94a3b8);
  max-width: 90px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  opacity: 0.85;
}

.preview-box {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(99, 102, 241, 0.06);
  border-left: 2px solid var(--primary-color, #6366f1);
  border-radius: 0 4px 4px 0;
  color: var(--text-secondary, #606266);
  font-size: 11px;
  overflow: hidden;
}

.preview-icon {
  font-size: 13px;
  line-height: 1;
}

.preview-title {
  color: var(--text-tertiary, #909399);
  font-weight: 600;
  flex-shrink: 0;
}

.preview-value {
  color: var(--text-main, #303133);
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
