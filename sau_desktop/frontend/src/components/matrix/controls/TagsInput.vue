<template>
  <div class="tags-input-control">
    <div class="control-header">
      <div class="label-box">
        <span class="label-text">{{ label }}</span>
        <span v-if="required" class="required-star">*</span>
      </div>
      <span class="header-hint">{{ hint }}</span>
    </div>

    <el-input
      v-model="modelValue"
      :placeholder="placeholder"
      clearable
      class="stylish-tags-input"
    />

    <!-- 常用热门标签快捷胶囊 -->
    <div v-if="presets && presets.length > 0" class="presets-row">
      <span class="presets-caption">推荐话题:</span>
      <div class="chips-group">
        <span
          v-for="tag in presets"
          :key="tag"
          class="tag-chip"
          @click="appendTag(tag)"
        >
          #{{ tag }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: string
  label?: string
  placeholder?: string
  required?: boolean
  hint?: string
  presets?: string[]
}>(), {
  label: '话题标签 (Tags)',
  placeholder: '多个话题标签请用空格或逗号分隔...',
  required: false,
  hint: '多个标签用空格或逗号分开',
  presets: () => ['热门短剧', '剧情', '逆袭', '都市', '精彩片段']
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: string): void
}>()

const modelValue = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

function appendTag(tag: string) {
  const current = (props.modelValue || '').trim()
  if (!current) {
    emit('update:modelValue', tag)
    return
  }
  const list = current.split(/[\s,，#]+/).filter(Boolean)
  if (!list.includes(tag)) {
    emit('update:modelValue', `${current} ${tag}`)
  }
}
</script>

<style scoped>
.tags-input-control {
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

.header-hint {
  font-size: 11px;
  color: var(--el-text-color-secondary, #909399);
}

.presets-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}

.presets-caption {
  font-size: 11px;
  color: var(--el-text-color-secondary, #909399);
}

.chips-group {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.tag-chip {
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 12px;
  background: var(--el-fill-color, #f0f2f5);
  color: var(--el-text-color-regular, #606266);
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s ease;
}

.tag-chip:hover {
  background: var(--el-color-primary-light-9, #ecf5ff);
  color: var(--el-color-primary, #409eff);
  border-color: var(--el-color-primary-light-8, #d9ecff);
}
</style>
