<template>
  <div class="desc-input-control">
    <div class="control-header">
      <div class="label-box">
        <span class="label-text">{{ label }}</span>
        <span v-if="required" class="required-star">*</span>
      </div>
      <span v-if="hint" class="header-hint">{{ hint }}</span>
    </div>

    <el-input
      v-model="modelValue"
      type="textarea"
      :rows="rows"
      :placeholder="placeholder"
      :maxlength="maxlength"
      show-word-limit
      class="stylish-desc-input"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: string
  label?: string
  placeholder?: string
  rows?: number
  maxlength?: number
  required?: boolean
  hint?: string
}>(), {
  label: '作品简介 / 描述文案',
  placeholder: '请输入正文、剧情简介或引流文案...',
  rows: 3,
  maxlength: 1000,
  required: false
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: string): void
}>()

const modelValue = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})
</script>

<style scoped>
.desc-input-control {
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

.stylish-desc-input :deep(.el-textarea__inner) {
  font-family: inherit;
  font-size: 13px;
  line-height: 1.5;
}
</style>
