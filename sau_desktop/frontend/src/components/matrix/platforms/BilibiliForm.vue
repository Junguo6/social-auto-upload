<template>
  <div class="exclusive-fields-grid">
    <el-form-item label="B站投稿主分区 (TID) *">
      <el-select v-model="override.tid" placeholder="请选择归属分区" style="width: 100%" filterable>
        <el-option 
          v-for="p in BILIBILI_PARTITIONS" 
          :key="p.id" 
          :label="p.name" 
          :value="p.id" 
        />
      </el-select>
    </el-form-item>

    <el-form-item label="创作声明与版权 *">
      <el-select v-model="override.declaration" placeholder="请选择创作声明" style="width: 100%">
        <el-option label="自制原创 (未经许可禁止转载)" value="1" />
        <el-option label="转载视频 (自动注明出处)" value="2" />
        <el-option label="内容由 AI 生成" value="ai" />
        <el-option label="内容含商业营销推广" value="ad" />
      </el-select>
    </el-form-item>
  </div>
</template>

<script setup lang="ts">
import { BILIBILI_PARTITIONS } from '../../../config/platforms'
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
