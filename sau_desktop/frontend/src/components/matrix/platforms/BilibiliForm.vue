<template>
  <div class="platform-layout-bilibili">
    <!-- 1. B站排版首项：投递主分区 + 创作版权声明 (双列网格) -->
    <div class="form-grid-2col">
      <el-form-item label="B站投稿分区 (TID) *" class="compact-item">
        <el-select
          v-model="override.tid"
          placeholder="请选择归属分区"
          filterable
          style="width: 100%"
        >
          <el-option
            v-for="p in BILIBILI_PARTITIONS"
            :key="p.id"
            :label="p.name"
            :value="p.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="创作声明与类型 *" class="compact-item">
        <el-select
          v-model="override.declaration"
          placeholder="请选择创作声明"
          style="width: 100%"
        >
          <el-option label="自制原创 (未经许可禁止转载)" value="1" />
          <el-option label="转载视频 (自动注明出处)" value="2" />
          <el-option label="内容由 AI 生成" value="ai" />
          <el-option label="内容含商业推广广告" value="ad" />
        </el-select>
      </el-form-item>
    </div>

    <!-- 2. B站稿件标题 (含占位变量与集数生成抽屉) -->
    <TitleInput
      v-model="override.title"
      label="稿件标题"
      placeholder="请输入B站视频标题，支持变量如：{视频名} - 第{集数}集"
      :maxlength="80"
      :required="true"
      :rule-config="ruleConfig"
      :sample-media="sampleMedia"
      :unit-level="unitLevel"
      :hide-variables="hideVariables"
    />

    <!-- 3. B站标签 (官方紧随标题之后) -->
    <TagsInput
      v-model="override.tags"
      label="视频标签 (Tag)"
      placeholder="按回车或空格分隔，最多支持 10 个标签"
      :presets="['短剧', '剧情', '逆袭', '精选短片', '都市日常']"
    />

    <!-- 4. 视频简介 -->
    <DescInput
      v-model="override.desc"
      label="视频简介"
      placeholder="填写更全面的视频介绍、演职员表或互动引导，让更多观众发现你的作品..."
      :rows="3"
      :maxlength="1000"
      :sample-media="sampleMedia"
      :unit-level="unitLevel"
      :hide-variables="hideVariables"
    />
  </div>
</template>

<script setup lang="ts">
import { BILIBILI_PARTITIONS } from '../../../config/platforms'
import type { PlatformOverrideSetting, BatchRuleConfig, MediaItem } from '../../../types/matrix'
import TitleInput from '../controls/TitleInput.vue'
import DescInput from '../controls/DescInput.vue'
import TagsInput from '../controls/TagsInput.vue'

defineProps<{
  override: PlatformOverrideSetting
  ruleConfig?: Partial<BatchRuleConfig>
  sampleMedia?: Partial<MediaItem>
  unitLevel?: number
  hideVariables?: boolean
}>()
</script>

<style scoped>
.platform-layout-bilibili {
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
