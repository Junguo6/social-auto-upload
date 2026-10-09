<template>
  <div class="platform-layout-xhs">
    <!-- 1. 核心创作内容区 -->
    <div class="form-content-section">
      <!-- 小红书标题 (官方严格限制 20 字以内) -->
      <TitleInput
        v-model="override.title"
        label="笔记标题"
        placeholder="填写标题会有更多赞哦 (限20字以内)"
        :maxlength="20"
        :required="true"
        :rule-config="ruleConfig"
        :sample-media="sampleMedia"
        :unit-level="unitLevel"
        :hide-variables="hideVariables"
      />

      <!-- 小红书正文笔记 -->
      <DescInput
        v-model="override.desc"
        label="笔记正文"
        placeholder="填写笔记正文，添加引人入胜的剧情介绍或讨论话题..."
        :rows="4"
        :maxlength="1000"
        :sample-media="sampleMedia"
        :unit-level="unitLevel"
        :hide-variables="hideVariables"
      />

      <!-- 话题与标签 -->
      <TagsInput
        v-model="override.tags"
        label="添加标签 (#)"
        placeholder="参与相关话题，获得更多笔记曝光"
        :presets="['追剧', '短剧推荐', '宝藏短剧', '沉浸式看剧', '都市情感']"
      />
    </div>

    <!-- 2. 笔记偏好与归属设置卡片 -->
    <div class="settings-card-group">
      <div class="group-title">
        <span class="title-bar"></span>
        <span>专栏归属与版权声明</span>
      </div>

      <!-- 专栏/合集输入行：采用 compact 紧凑变量模式 -->
      <div class="collection-field-row">
        <div class="field-label-wrap">
          <span class="field-label">专栏 / 合集</span>
          <span class="field-hint">选填 · 相同专栏的笔记将归集展示</span>
        </div>
        <div class="field-input-box">
          <TokenTemplateInput
            v-model="override.collection"
            type="input"
            placeholder="选填：专栏或合集名称，支持插入动态变量或TXT文案..."
            :sample-media="sampleMedia"
            :unit-level="unitLevel"
            :rule-config="ruleConfig"
            :hide-tools="hideVariables"
          />
        </div>
      </div>

      <!-- 转载声明 -->
      <div class="declaration-row">
        <el-form-item label="非原创转载声明" class="compact-form-item">
          <el-select v-model="override.declaration" placeholder="声明类型" style="width: 100%">
            <el-option label="默认（原创作品）" value="" />
            <el-option label="网络转载整理 (非原创)" value="repost" />
          </el-select>
        </el-form-item>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PlatformOverrideSetting, BatchRuleConfig, MediaItem } from '../../../types/matrix'
import TitleInput from '../controls/TitleInput.vue'
import DescInput from '../controls/DescInput.vue'
import TagsInput from '../controls/TagsInput.vue'
import TokenTemplateInput from '../controls/TokenTemplateInput.vue'

defineProps<{
  override: PlatformOverrideSetting
  ruleConfig?: Partial<BatchRuleConfig>
  sampleMedia?: Partial<MediaItem>
  unitLevel?: number
  hideVariables?: boolean
}>()
</script>

<style scoped>
.platform-layout-xhs {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-content-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* 偏好与归属设置卡片 */
.settings-card-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px 14px;
  background: var(--bg-hover, rgba(248, 250, 252, 0.6));
  border: 1px solid var(--border-color-light, rgba(226, 232, 240, 0.8));
  border-radius: 8px;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary, #475569);
  user-select: none;
}

.title-bar {
  width: 3px;
  height: 12px;
  border-radius: 2px;
  background: #ff2442; /* 小红书品牌红 */
}

/* 专栏归属行 */
.collection-field-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.field-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--el-text-color-primary, #334155);
}

.field-hint {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
}

.field-input-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* 声明选项行 */
.declaration-row {
  margin-top: 2px;
}

.compact-form-item {
  margin-bottom: 0;
}

.compact-form-item :deep(.el-form-item__label) {
  font-size: 12px;
  font-weight: 600;
  color: var(--el-text-color-primary, #334155);
  margin-bottom: 4px;
  line-height: 1.2;
}
</style>
