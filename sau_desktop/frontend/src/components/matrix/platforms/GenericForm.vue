<template>
  <div class="platform-layout-generic">
    <!-- 1. 作品标题 -->
    <TitleInput
      v-model="override.title"
      label="作品标题"
      placeholder="请输入作品标题，支持变量如：{视频名} - 第{集数}集"
      :maxlength="80"
      :required="true"
      :rule-config="ruleConfig"
      :sample-media="sampleMedia"
      :unit-level="unitLevel"
      :hide-variables="hideVariables"
    />

    <!-- 2. 作品简介 -->
    <DescInput
      v-model="override.desc"
      label="正文与简介描述"
      placeholder="填写正文、剧情简介或引流文案..."
      :rows="3"
      :maxlength="1000"
      :sample-media="sampleMedia"
      :unit-level="unitLevel"
      :hide-variables="hideVariables"
    />

    <!-- 3. 话题标签 -->
    <TagsInput
      v-model="override.tags"
      label="话题标签 (Tags)"
      placeholder="多个话题标签请用空格或逗号分隔..."
    />

    <!-- 4. 合集/专栏 -->
    <div class="form-grid-single">
      <el-form-item label="专栏 / 合集名称" class="compact-item">
        <TokenTemplateInput
          v-model="override.collection"
          type="input"
          placeholder="选填：专栏/合集名称，支持插入动态变量或TXT文案..."
          :sample-media="sampleMedia"
          :unit-level="unitLevel"
          :rule-config="ruleConfig"
          :hide-tools="hideVariables"
        />
      </el-form-item>
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
.platform-layout-generic {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-grid-single {
  display: grid;
  grid-template-columns: 1fr;
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
