<template>
  <div class="exclusive-fields-grid">
    <el-form-item label="抖音合集名称">
      <el-input 
        v-model="override.collection" 
        placeholder="选填：加入的抖音合集名称" 
        clearable 
        class="stylish-input" 
      />
    </el-form-item>

    <el-form-item label="AI生成/原创声明">
      <el-select v-model="override.declaration" placeholder="选填：自创/AI生成声明" style="width: 100%">
        <el-option label="不特别声明" value="" />
        <el-option label="内容由 AI 辅助生成" value="ai_generated" />
        <el-option label="个人原创作品" value="original" />
      </el-select>
    </el-form-item>

    <el-form-item label="谁可以看">
      <el-select v-model="override.visibility" placeholder="可见性" style="width: 100%">
        <el-option label="公开 (全网可见)" value="0" />
        <el-option label="好友可见" value="1" />
        <el-option label="仅自己可见 (私密)" value="2" />
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
