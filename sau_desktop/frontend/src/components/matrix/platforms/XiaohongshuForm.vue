<template>
  <div class="platform-layout-xhs">
    <!-- 1. 小红书标题 (官方严格限制 20 字以内) -->
    <TitleInput
      v-model="override.title"
      label="笔记标题"
      placeholder="填写标题会有更多赞哦 (限20字以内)"
      :maxlength="20"
      :required="true"
      :rule-config="ruleConfig"
    />

    <!-- 2. 小红书正文笔记 -->
    <DescInput
      v-model="override.desc"
      label="笔记正文"
      placeholder="填写笔记正文，添加引人入胜的剧情介绍或讨论话题..."
      :rows="4"
      :maxlength="1000"
    />

    <!-- 3. 话题与标签 -->
    <TagsInput
      v-model="override.tags"
      label="添加标签 (#)"
      placeholder="参与相关话题，获得更多笔记曝光"
      :presets="['追剧', '短剧推荐', '宝藏短剧', '沉浸式看剧', '都市情感']"
    />

    <!-- 4. 转载与合集声明 -->
    <div class="form-grid-2col">
      <el-form-item label="专栏 / 合集" class="compact-item">
        <el-input
          v-model="override.collection"
          placeholder="选填：归属的合集名称"
          clearable
        />
      </el-form-item>

      <el-form-item label="非原创转载声明" class="compact-item">
        <el-select v-model="override.declaration" placeholder="声明类型" style="width: 100%">
          <el-option label="原创作品" value="" />
          <el-option label="网络转载整理 (非原创)" value="repost" />
        </el-select>
      </el-form-item>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PlatformOverrideSetting, BatchRuleConfig } from '../../../types/matrix'
import TitleInput from '../controls/TitleInput.vue'
import DescInput from '../controls/DescInput.vue'
import TagsInput from '../controls/TagsInput.vue'

defineProps<{
  override: PlatformOverrideSetting
  ruleConfig?: BatchRuleConfig
}>()
</script>

<style scoped>
.platform-layout-xhs {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-grid-2col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.compact-item {
  margin-bottom: 0;
}

.compact-item :deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary, #303133);
  margin-bottom: 6px;
}
</style>
