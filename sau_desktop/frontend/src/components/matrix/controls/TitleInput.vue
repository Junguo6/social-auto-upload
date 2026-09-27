<template>
  <div class="title-input-control">
    <div class="control-header">
      <div class="label-box">
        <span class="label-text">{{ label }}</span>
        <span v-if="required" class="required-star">*</span>
      </div>
      <!-- 暂时取消分集规则设置按钮，按默认智能规则处理即可
      <div v-if="ruleConfig && !hideVariables" class="header-tools">
        <button
          type="button"
          class="rule-toggle-btn"
          :class="{ active: isEpisodePanelOpen }"
          @click="isEpisodePanelOpen = !isEpisodePanelOpen"
        >
          <el-icon><Setting /></el-icon>
          <span>{{ isEpisodePanelOpen ? '收起分集规则' : '集数生成规则' }}</span>
        </button>
      </div>
      -->
    </div>

    <!-- 标题富标签输入框 (内嵌变量标签/TXT标签 + 底部极简双入口) -->
    <TokenTemplateInput
      v-model="modelValue"
      type="input"
      :placeholder="placeholder"
      :maxlength="maxlength"
      :sample-media="sampleMedia"
      :unit-level="unitLevel"
      :rule-config="ruleConfig"
      :hide-tools="hideVariables"
    />

    <!-- 折叠展开的集数规则面板 (暂时隐藏)
    <el-collapse-transition>
      <div v-if="isEpisodePanelOpen && !hideVariables" class="episode-drawer-card">
        <div class="drawer-header">
          <span class="drawer-title">分集变量 `{集数}` 自动解析规则</span>
          <span class="drawer-desc">多集连发时自动识别或递增编号</span>
        </div>
        <div class="drawer-body">
          <div class="param-row">
            <span class="param-name">提取方式</span>
            <el-select v-model="safeRuleConfig.episodeMode" size="small" style="width: 140px">
              <el-option label="智能提取文件名" value="auto" />
              <el-option label="强制顺序递增" value="sequence" />
            </el-select>
          </div>

          <div class="param-row">
            <span class="param-name">起始集</span>
            <el-input-number
              v-model="safeRuleConfig.startEpisode"
              :min="1"
              :max="9999"
              size="small"
              style="width: 96px"
            />
          </div>

          <div class="param-row">
            <span class="param-name">步长</span>
            <el-input-number
              v-model="safeRuleConfig.episodeStep"
              :min="1"
              :max="10"
              size="small"
              style="width: 86px"
            />
          </div>

          <div class="param-row">
            <el-checkbox v-model="ruleConfig!.padZero" size="small">
              自动补零 (如 01, 02)
            </el-checkbox>
          </div>
        </div>
      </div>
    </el-collapse-transition>
    -->
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { BatchRuleConfig, MediaItem } from '../../../types/matrix'
import TokenTemplateInput from './TokenTemplateInput.vue'

const props = withDefaults(defineProps<{
  modelValue: string
  label?: string
  placeholder?: string
  maxlength?: number
  required?: boolean
  ruleConfig?: BatchRuleConfig
  sampleMedia?: Partial<MediaItem>
  unitLevel?: number
  hideVariables?: boolean
}>(), {
  label: '作品标题',
  placeholder: '请输入视频标题，支持变量如：{视频名} - 第{集数}集',
  maxlength: 80,
  required: true,
  hideVariables: false
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: string): void
}>()

const defaultRuleConfig: BatchRuleConfig = {
  titleTemplate: '{视频名}',
  episodeMode: 'sequence',
  startEpisode: 1,
  episodeStep: 1,
  padZero: false,
  scheduleType: 'immediate',
  startScheduleTime: '',
  intervalMinutes: 30
}
const safeRuleConfig = computed(() => props.ruleConfig || defaultRuleConfig)

const isEpisodePanelOpen = ref(false)

const modelValue = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

function insertVar(varStr: string) {
  const current = props.modelValue || ''
  if (!current) {
    emit('update:modelValue', varStr)
  } else if (!current.includes(varStr)) {
    emit('update:modelValue', `${current} ${varStr}`)
  } else {
    emit('update:modelValue', `${current}${varStr}`)
  }
}
</script>

<style scoped>
.title-input-control {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.control-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.label-box {
  display: flex;
  align-items: center;
  gap: 4px;
}

.label-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary, #303133);
}

.required-star {
  color: var(--el-color-danger, #f56c6c);
}

.rule-toggle-btn {
  background: none;
  border: none;
  color: var(--el-color-primary, #409eff);
  font-size: 12px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.rule-toggle-btn:hover {
  background: var(--el-color-primary-light-9, #ecf5ff);
}

.variable-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}

.bar-caption {
  font-size: 11px;
  color: var(--el-text-color-secondary, #909399);
}

.chips-group {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.chip-item {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--el-fill-color-light, #f5f7fa);
  color: var(--el-color-primary, #409eff);
  cursor: pointer;
  border: 1px solid var(--el-color-primary-light-8, #d9ecff);
  transition: all 0.15s ease;
}

.chip-item:hover {
  background: var(--el-color-primary-light-9, #ecf5ff);
  border-color: var(--el-color-primary, #409eff);
}

.episode-drawer-card {
  margin-top: 6px;
  background: var(--el-fill-color-light, #f8f9fa);
  border: 1px solid var(--el-border-color-light, #ebeef5);
  border-radius: 8px;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.drawer-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.drawer-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--el-text-color-primary, #303133);
}

.drawer-desc {
  font-size: 11px;
  color: var(--el-text-color-secondary, #909399);
}

.drawer-body {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.param-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.param-name {
  font-size: 12px;
  color: var(--el-text-color-regular, #606266);
}
</style>
