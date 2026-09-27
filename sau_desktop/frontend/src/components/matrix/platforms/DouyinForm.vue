<template>
  <div class="platform-layout-douyin">
    <!-- 1. 核心创作内容区 -->
    <div class="form-content-section">
      <!-- 抖音标题 -->
      <TitleInput
        v-model="override.title"
        label="作品标题"
        placeholder="请输入抖音作品标题，支持变量如：{视频名} - 第{集数}集"
        :maxlength="80"
        :required="true"
        :rule-config="ruleConfig"
        :sample-media="sampleMedia"
        :unit-level="unitLevel"
        :hide-variables="hideVariables"
      />

      <!-- 作品描述 -->
      <DescInput
        v-model="override.desc"
        label="作品描述 / 剧情简介"
        placeholder="添加作品描述，支持详细剧情或引导文案..."
        :rows="3"
        :maxlength="1000"
        :sample-media="sampleMedia"
        :unit-level="unitLevel"
        :hide-variables="hideVariables"
      />

      <!-- 话题标签 -->
      <TagsInput
        v-model="override.tags"
        label="添加话题 (#)"
        placeholder="按回车或空格分隔，将自动参与对应话题热点"
        :presets="['抖音精选', '短剧', '剧情', '追剧', '逆袭']"
      />
    </div>

    <!-- 2. 发布设置与权益声明卡片 (规整防错乱布局) -->
    <div class="settings-card-group">
      <div class="group-title">
        <span class="title-bar"></span>
        <span>发布设置与偏好</span>
      </div>

      <!-- 归属合集行：单行独立排布，采用 compact 紧凑变量模式，永不撑爆网格 -->
      <div class="collection-field-row">
        <div class="field-label-wrap">
          <span class="field-label">归属合集</span>
          <span class="field-hint">选填 · 相同合集视频将自动聚合</span>
        </div>
        <div class="field-input-box">
          <TokenTemplateInput
            v-model="override.collection"
            type="input"
            placeholder="请输入合集名称，支持插入动态变量或TXT文案..."
            :sample-media="sampleMedia"
            :unit-level="unitLevel"
            :rule-config="ruleConfig"
            :hide-tools="hideVariables"
          />
        </div>
      </div>

      <!-- 下拉选择区：严谨 1:1 双列网格，高度绝对对齐 -->
      <div class="settings-dropdown-grid">
        <el-form-item label="原创与AI声明" class="compact-form-item">
          <el-select v-model="override.declaration" placeholder="声明选项" style="width: 100%">
            <el-option label="默认不声明" value="" />
            <el-option label="个人原创作品" value="original" />
            <el-option label="内容由 AI 辅助生成" value="ai_generated" />
          </el-select>
        </el-form-item>

        <el-form-item label="谁可以看" class="compact-form-item">
          <el-select v-model="override.visibility" placeholder="可见范围" style="width: 100%">
            <el-option label="公开 (全网可见)" value="0" />
            <el-option label="好友可见" value="1" />
            <el-option label="仅自己可见 (私密)" value="2" />
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
  ruleConfig?: BatchRuleConfig
  sampleMedia?: Partial<MediaItem>
  unitLevel?: number
  hideVariables?: boolean
}>()
</script>

<style scoped>
.platform-layout-douyin {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-content-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* 发布设置与偏好卡片 */
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
  background: var(--primary-color, #6366f1);
}

/* 归属合集单行区域 */
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

/* 双列网格 */
.settings-dropdown-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
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
