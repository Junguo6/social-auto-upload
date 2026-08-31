<template>
  <div class="exclusive-fields-grid">
    <el-form-item label="竖版专属封面 (Portrait)">
      <el-input 
        v-model="override.thumbnailPortrait" 
        placeholder="选填：专供视频号信息流展示的竖版封面" 
        class="stylish-input"
      >
        <template #append>
          <el-button @click="choosePortraitCover"><el-icon><Picture /></el-icon></el-button>
        </template>
      </el-input>
    </el-form-item>

    <el-form-item label="视频号专栏合集">
      <el-input 
        v-model="override.collection" 
        placeholder="选填：归属的视频号合集名称" 
        clearable 
        class="stylish-input" 
      />
    </el-form-item>

    <el-form-item label="精炼短标题 (展示在左下角)">
      <el-input 
        v-model="override.shortTitle" 
        placeholder="选填：6~16字短标题" 
        clearable 
        class="stylish-input" 
      />
    </el-form-item>

    <div class="exclusive-checkboxes">
      <el-checkbox v-model="override.draft">存为草稿 (不直接公开发布)</el-checkbox>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { SelectLocalFile } from '../../../../wailsjs/go/main/App'
import type { PlatformOverrideSetting } from '../../../types/matrix'

const props = defineProps<{
  override: PlatformOverrideSetting
}>()

const choosePortraitCover = async () => {
  try {
    const file = await SelectLocalFile('选择微信视频号竖版封面', ['*.png', '*.jpg', '*.jpeg', '*.webp'])
    if (file) {
      props.override.thumbnailPortrait = file
      ElMessage.success('已设置微信视频号竖版封面')
    }
  } catch (err: any) {
    ElMessage.error(`选择封面失败: ${err.message || err}`)
  }
}
</script>

<style scoped>
.exclusive-fields-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.exclusive-checkboxes {
  grid-column: span 2;
  margin-top: -4px;
}
</style>
