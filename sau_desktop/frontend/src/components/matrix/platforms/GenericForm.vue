<template>
  <div class="exclusive-fields-grid">
    <el-form-item label="专栏 / 合集名称">
      <el-input 
        v-model="override.collection" 
        placeholder="选填：专栏/合集名称" 
        clearable 
        class="stylish-input" 
      />
    </el-form-item>
  </div>
</template>

<script setup lang="ts">
import type { PlatformOverrideSetting } from '../../../types/matrix'

defineProps<{
  override: PlatformOverrideSetting
}>()
</script>

<style scoped>
.exclusive-fields-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
</style>
