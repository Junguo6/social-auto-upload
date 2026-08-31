<template>
  <div class="exclusive-fields-grid">
    <el-form-item label="B站投稿主分区 (TID) *">
      <el-select v-model="override.tid" placeholder="必须选择一个归属分区" style="width: 100%">
        <el-option 
          v-for="p in BILIBILI_PARTITIONS" 
          :key="p.id" 
          :label="p.name" 
          :value="p.id" 
        />
      </el-select>
    </el-form-item>

    <el-form-item label="自制/转载声明">
      <el-select v-model="override.declaration" placeholder="自制 / 转载" style="width: 100%">
        <el-option label="自制原创 (1)" value="1" />
        <el-option label="转载注明出处 (2)" value="2" />
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
