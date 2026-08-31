<template>
  <div class="exclusive-fields-grid">
    <el-form-item label="非原创转载声明">
      <el-select v-model="override.declaration" placeholder="选填：是否为转载/非原创" style="width: 100%">
        <el-option label="原创笔记" value="" />
        <el-option label="非原创 / 网络转载整理" value="repost" />
      </el-select>
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
