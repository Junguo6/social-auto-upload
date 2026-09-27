<template>
  <div class="variable-chips-helper" :class="{ 'is-compact': compact }">
    <!-- 1. 紧凑下拉模式 (适合嵌入合集等狭窄网格组件) -->
    <div v-if="compact" class="compact-trigger-bar">
      <el-dropdown trigger="click" @command="handleInsert">
        <span class="compact-add-btn">
          <span class="plus-icon">+</span>
          <span>插入动态变量</span>
          <el-icon class="arrow-down"><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu class="var-dropdown-menu">
            <el-dropdown-item
              v-for="v in computedVars"
              :key="v.key"
              :command="v.key"
              class="var-dropdown-item"
            >
              <span class="var-drop-tag" :class="{ 'is-level': v.isLevel }">{{ v.label }}</span>
              <span class="var-drop-key">{{ v.key }}</span>
              <span v-if="v.sampleVal" class="var-drop-sample">{{ v.sampleVal }}</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <!-- 紧凑微型解析结果 -->
      <span v-if="previewText" class="compact-preview" :title="previewText">
        <span class="preview-dot"></span>
        <span class="preview-text">{{ previewText }}</span>
      </span>
    </div>

    <!-- 2. 标准精巧胶囊栏模式 (标题、正文等宽阔区域) -->
    <template v-else>
      <div class="chips-container">
        <span class="chips-label">变量:</span>
        <div class="chips-list">
          <el-tooltip
            v-for="v in visibleVars"
            :key="v.key"
            :content="`${v.desc || v.label} · 插入 ${v.key}${v.sampleVal ? '（示例：' + v.sampleVal + '）' : ''}`"
            placement="top"
            :show-after="200"
          >
            <button
              type="button"
              class="var-pill-btn"
              :class="{ 'is-level': v.isLevel }"
              @click.prevent="handleInsert(v.key)"
            >
              <span class="pill-plus">+</span>
              <span class="pill-label">{{ v.label }}</span>
            </button>
          </el-tooltip>

          <!-- 展开/折叠更多变量 -->
          <button
            v-if="hasMoreVars"
            type="button"
            class="var-pill-btn expand-btn"
            @click.prevent="isExpanded = !isExpanded"
          >
            <span>{{ isExpanded ? '收起' : `更多 (${computedVars.length - COLLAPSE_LIMIT})` }}</span>
            <el-icon class="expand-icon" :class="{ 'is-open': isExpanded }"><ArrowDown /></el-icon>
          </button>
        </div>
      </div>

      <!-- 实时解析示例预览 (精巧单行 Badge) -->
      <transition name="fade">
        <div v-if="previewText" class="preview-pill-bar">
          <span class="preview-badge">示例</span>
          <span class="preview-val-text" :title="previewText">{{ previewText }}</span>
        </div>
      </transition>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ArrowDown } from '@element-plus/icons-vue'
import {
  buildDynamicVariables,
  resolveTemplateString,
  type AvailableVariable
} from '../../utils/matrixHelper'
import type { MediaItem, BatchRuleConfig } from '../../types/matrix'

const COLLAPSE_LIMIT = 5

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
  /** 是否紧凑模式（如下拉菜单模式，用于多列网格内防撑破） */
  compact?: boolean
}>(), {
  currentValue: '',
  unitLevel: 0,
  compact: false
})

const emit = defineEmits<{
  (e: 'insert', variableKey: string): void
}>()

const isExpanded = ref(false)

// 优先动态根据真实素材构建变量
const computedVars = computed<AvailableVariable[]>(() => {
  if (props.vars && props.vars.length > 0) {
    return props.vars
  }
  return buildDynamicVariables(props.sampleMedia, props.unitLevel, props.ruleConfig)
})

const hasMoreVars = computed(() => computedVars.value.length > COLLAPSE_LIMIT)

const visibleVars = computed(() => {
  if (isExpanded.value || !hasMoreVars.value) {
    return computedVars.value
  }
  return computedVars.value.slice(0, COLLAPSE_LIMIT)
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
  gap: 5px;
  margin-top: 5px;
  font-size: 12px;
}

/* 1. 紧凑模式样式 (适用于合集等狭窄列) */
.compact-trigger-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.compact-add-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 500;
  color: var(--el-color-primary, #6366f1);
  background: var(--el-color-primary-light-9, rgba(99, 102, 241, 0.08));
  border: 1px dashed var(--el-color-primary-light-5, rgba(99, 102, 241, 0.35));
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}
.compact-add-btn:hover {
  background: var(--el-color-primary-light-8, rgba(99, 102, 241, 0.16));
  border-color: var(--el-color-primary, #6366f1);
}
.compact-add-btn .plus-icon {
  font-weight: 700;
  font-size: 12px;
}
.compact-add-btn .arrow-down {
  font-size: 10px;
  opacity: 0.7;
}

.compact-preview {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--text-secondary, #64748b);
  max-width: 180px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.compact-preview .preview-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #10b981;
  flex-shrink: 0;
}

/* 2. 正常胶囊条样式 */
.chips-container {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.chips-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted, #94a3b8);
  user-select: none;
  flex-shrink: 0;
}

.chips-list {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 5px;
}

.var-pill-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 7px;
  font-size: 11px;
  line-height: 1.3;
  color: var(--text-regular, #475569);
  background: rgba(148, 163, 184, 0.08);
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.18s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
  outline: none;
}

.var-pill-btn:hover {
  color: var(--el-color-primary, #6366f1);
  background: var(--el-color-primary-light-9, rgba(99, 102, 241, 0.1));
  border-color: var(--el-color-primary-light-5, rgba(99, 102, 241, 0.35));
  transform: translateY(-1px);
}

.var-pill-btn .pill-plus {
  font-size: 11px;
  opacity: 0.6;
  font-weight: bold;
}

.var-pill-btn.is-level {
  color: #7c3aed;
  background: rgba(124, 58, 237, 0.08);
  border-color: rgba(124, 58, 237, 0.25);
}
.var-pill-btn.is-level:hover {
  color: #6d28d9;
  background: rgba(124, 58, 237, 0.16);
  border-color: #7c3aed;
}

.var-pill-btn.expand-btn {
  color: var(--text-tertiary, #94a3b8);
  background: transparent;
  border-style: dashed;
}
.var-pill-btn.expand-btn:hover {
  color: var(--el-color-primary, #6366f1);
  border-color: var(--el-color-primary-light-5, rgba(99, 102, 241, 0.35));
}
.expand-icon {
  font-size: 10px;
  transition: transform 0.2s ease;
}
.expand-icon.is-open {
  transform: rotate(180deg);
}

/* 3. 示例预览条 (微缩单行 Badge) */
.preview-pill-bar {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  background: rgba(16, 185, 129, 0.06);
  border: 1px solid rgba(16, 185, 129, 0.2);
  border-radius: 4px;
  font-size: 11px;
  max-width: 100%;
  overflow: hidden;
  align-self: flex-start;
}

.preview-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 0 4px;
  background: rgba(16, 185, 129, 0.15);
  color: #059669;
  border-radius: 2px;
  line-height: 1.4;
  flex-shrink: 0;
}

.preview-val-text {
  color: var(--text-regular, #334155);
  font-family: var(--font-mono, monospace);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 下拉菜单项样式 */
:deep(.var-dropdown-item) {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  padding: 6px 12px;
}
.var-drop-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px;
  background: rgba(99, 102, 241, 0.1);
  color: #6366f1;
  font-weight: 600;
}
.var-drop-tag.is-level {
  background: rgba(124, 58, 237, 0.1);
  color: #7c3aed;
}
.var-drop-key {
  color: var(--text-secondary, #64748b);
  font-family: monospace;
}
.var-drop-sample {
  color: var(--text-tertiary, #94a3b8);
  font-size: 11px;
  margin-left: auto;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
