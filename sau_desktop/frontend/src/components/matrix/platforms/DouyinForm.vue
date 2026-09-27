<template>
  <div class="platform-layout-douyin">
    <!-- 1. 抖音标题 -->
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

    <!-- 2. 作品描述 -->
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

    <!-- 3. 添加话题标签 -->
    <TagsInput
      v-model="override.tags"
      label="添加话题 (#)"
      placeholder="按回车或空格分隔，将自动参与对应话题热点"
      :presets="['抖音精选', '短剧', '剧情', '追剧', '逆袭']"
    />

    <!-- 4. 抖音发布与合集高级选项 (多列整齐网格) -->
    <div class="form-grid-3col">
      <el-form-item label="归属合集" class="compact-item">
        <el-input
          v-model="override.collection"
          placeholder="选填：合集名称"
          clearable
        />
        <VariableChips
          v-if="!hideVariables"
          :current-value="override.collection"
          :rule-config="ruleConfig"
          :sample-media="sampleMedia"
          :unit-level="unitLevel"
          @insert="(v) => override.collection = (override.collection || '') + v"
        />
      </el-form-item>

      <el-form-item label="原创与AI声明" class="compact-item">
        <el-select v-model="override.declaration" placeholder="声明选项" style="width: 100%">
          <el-option label="默认不声明" value="" />
          <el-option label="个人原创作品" value="original" />
          <el-option label="内容由 AI 辅助生成" value="ai_generated" />
        </el-select>
      </el-form-item>

      <el-form-item label="谁可以看" class="compact-item">
        <el-select v-model="override.visibility" placeholder="可见范围" style="width: 100%">
          <el-option label="公开 (全网可见)" value="0" />
          <el-option label="好友可见" value="1" />
          <el-option label="仅自己可见 (私密)" value="2" />
        </el-select>
      </el-form-item>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PlatformOverrideSetting, BatchRuleConfig, MediaItem } from '../../../types/matrix'
import TitleInput from '../controls/TitleInput.vue'
import DescInput from '../controls/DescInput.vue'
import TagsInput from '../controls/TagsInput.vue'
import VariableChips from '../VariableChips.vue'

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
  gap: 14px;
}

.form-grid-3col {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 14px;
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
